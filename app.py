import streamlit as st
import boto3
import datetime
import time
import ntplib
from PIL import Image
import os
import io
import requests
from streamlit_extras.buy_me_a_coffee import button

class TimeAwareTextractProcessor:
    def __init__(self, access_key, secret_key, region):
        self.sync_time()
        self.textract = boto3.client(
            'textract',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )

    def sync_time(self):
        try:
            ntp_client = ntplib.NTPClient()
            response = ntp_client.request('pool.ntp.org')
            offset = response.offset
            if abs(offset) > 1:
                st.warning("⚠️ System time significantly different from NTP time")
        except:
            st.warning("⚠️ Could not sync with NTP server. Proceeding with system time.")

    def process_uploaded_image(self, uploaded_file):
        try:
            image_bytes = uploaded_file.getvalue()
            max_retries = 3
            retry_delay = 2

            for attempt in range(max_retries):
                try:
                    response = self.textract.detect_document_text(
                        Document={'Bytes': image_bytes}
                    )
                    extracted_text = []
                    for item in response['Blocks']:
                        if item['BlockType'] == 'LINE':
                            extracted_text.append(item['Text'])

                    return {
                        'status': 'success',
                        'text': '\n'.join(extracted_text),
                        'confidence': sum(item.get('Confidence', 0) for item in response['Blocks']) / len(response['Blocks']) if response['Blocks'] else 0
                    }

                except Exception as e:
                    if attempt < max_retries - 1:
                        st.error(f"⚠️ Error occurred: {str(e)}, retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                    else:
                        raise

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

def generate_text(prompt, bard_api_key):
    request_body = {
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ]
    }
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={bard_api_key}"
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json=request_body)

    print(f"API Response: {response.json()}")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print(f"Error: API call failed with status code {response.status_code}")
        return None

def main():
    st.title("Test Solver 📝")
    st.write("Upload an image with a multiple-choice question:")

    with st.sidebar:
        st.header("⚙️ Configuration")
        access_key = st.text_input("AWS Access Key", type="password")
        secret_key = st.text_input("AWS Secret Key", type="password")
        region = st.text_input("AWS Region", value="us-east-1")
        bard_api_key = st.text_input("Bard API Key", type="password")

    uploaded_file = st.file_uploader("📂 Choose an image file", type=['png', 'jpg', 'jpeg'])

    if uploaded_file is not None:
        st.image(uploaded_file, caption="Uploaded Image", use_column_width=True)

        if not access_key or not secret_key or not bard_api_key:
            st.error("Please enter all required credentials in the sidebar")
            return
        try:
            with st.spinner("Initializing processor and syncing time..."):
                processor = TimeAwareTextractProcessor(access_key, secret_key, region)
            with st.spinner("Processing image..."):
                result = processor.process_uploaded_image(uploaded_file)
            if result['status'] == 'success':
                st.success("Answer extracted successfully!")
                
                full_text = result['text']
                bard_response = generate_text(f"{full_text}\nAnswer the following question by picking the appropriate response from the option:", bard_api_key)
                
                st.subheader("🎯 Correct Answer: ")
                st.markdown("- " + bard_response["candidates"][0]["content"]["parts"][0]["text"])
                
            else:
                st.error(f"❌ Error: {result['message']}")
        except Exception as e:
            st.error(f"❗ An error occurred: {str(e)}")

        button(username="daniel99estrada", floating=False, width=221)

if __name__ == "__main__":
    main()