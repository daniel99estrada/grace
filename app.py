import streamlit as st
import boto3
import datetime
import time
import ntplib
from PIL import Image
import os
import io
import requests

class TimeAwareTextractProcessor:
    def __init__(self, access_key, secret_key, region):
        """Initialize AWS Textract client with time synchronization."""
        # Sync time first
        self.sync_time()

        self.textract = boto3.client(
            'textract',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )

    def sync_time(self):
        """Sync local time with NTP server."""
        try:
            ntp_client = ntplib.NTPClient()
            response = ntp_client.request('pool.ntp.org')
            # Get the offset from local time
            offset = response.offset
            # st.info(f"Time offset: {offset:.2f} seconds")
            if abs(offset) > 1:
                st.warning("System time significantly different from NTP time")
        except:
            st.warning("Could not sync with NTP server. Proceeding with system time.")

    def process_uploaded_image(self, uploaded_file):
        """Process an uploaded image file with error handling and retries."""
        try:
            # Read image file
            image_bytes = uploaded_file.getvalue()

            # Add retry logic
            max_retries = 3
            retry_delay = 2

            for attempt in range(max_retries):
                try:
                    # Call Textract
                    response = self.textract.detect_document_text(
                        Document={'Bytes': image_bytes}
                    )

                    # Extract text from response
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
                        st.error(f"Error occurred: {str(e)}, retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                    else:
                        raise

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

# Replace with your actual API key
API_KEY = "AIzaSyBfk-JaTBKYVmKzj-MSuXhAhQaY4QPZoHI"

def generate_text(prompt):

  # Construct the request body
  request_body = {
      "contents": [
          {"role": "user", "parts": [{"text": prompt}]}
      ]
  }

  # Build the URL with the API key
  url = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={API_KEY}"

  # Set headers for content type
  headers = {"Content-Type": "application/json"}

  # Send the POST request
  response = requests.post(url, headers=headers, json=request_body)

  # Print the entire response for debugging
  print(f"API Response: {response.json()}")
  print(f"Status Code: {response.status_code}")

  # Check for successful response
  if response.status_code == 200:
    # Parse the JSON response
    data = response.json()
    # Access the generated text from the response (modify this if the key has changed)
    return data
  else:
    print(f"Error: API call failed with status code {response.status_code}")
    return None
  
def main():
    st.title("Test Solver")
    st.write("Upload an image with a multiple choice question:")

    # AWS Credentials input (you might want to use environment variables in production)
    with st.sidebar:
        st.header("Configuration")
        access_key = st.text_input("AWS Access Key", type="password")
        secret_key = st.text_input("AWS Secret Key", type="password")
        region = st.text_input("AWS Region", value="us-east-1")

    # File uploader
    uploaded_file = st.file_uploader("Choose an image file", type=['png', 'jpg', 'jpeg'])

    if uploaded_file is not None:
        # Display uploaded image
        st.image(uploaded_file, caption="Uploaded Image", use_column_width=True)

        # Process button
        # if st.button("Extract Text"):
        if not access_key or not secret_key:
            st.error("Please enter AWS credentials in the sidebar")
            return
        try:
            # Initialize processor
            with st.spinner("Initializing processor and syncing time..."):
                processor = TimeAwareTextractProcessor(access_key, secret_key, region)
            # Process image
            with st.spinner("Processing image..."):
                result = processor.process_uploaded_image(uploaded_file)
            if result['status'] == 'success':
                st.success("Answer extracted successfully!")
                
                # Display confidence score
                # st.metric("Confidence Score", f"{result['confidence']:.2f}%")
                
                full_text = result['text']
                bard_response = generate_text(f"{full_text}\Answer the following question by picking the appropriate response from the option:")
                # Display extracted text in a text area
                st.subheader("Correct Answer: ")
                st.markdown(bard_response["candidates"][0]["content"]["parts"][0]["text"])
                
                # Add download button for extracted text
                # st.download_button(
                #     label="Download extracted text",
                #     data=result['text'],
                #     file_name="extracted_text.txt",
                #     mime="text/plain"
                # )
            else:
                st.error(f"Error: {result['message']}")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()