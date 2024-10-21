from flask import Flask, request, jsonify
import os
import requests
import shutil

app = Flask(__name__)

# Configuration
BACKBLAZE_BUCKET_ID = '3da90956953fa79b92240d1f'
BACKBLAZE_BUCKET_NAME = 'storagevizsoft'
BACKBLAZE_AUTH_URL = 'https://api.backblazeb2.com/b2api/v2/b2_authorize_account'
CONVERSION_API_URL = 'https://api-tasker.onlineconvertfree.com/api/upload'
LOCAL_STORAGE = './local_files'

# Backblaze B2 credentials
KEY_ID = '004d9965f7b24df0000000005'
APP_KEY = 'K004Tw4DUcnSIq4jiQ/ZXjZisfAv684'
CONVERSION_API_TOKEN = '8747d93b31419ff444c769a7c1d8ab3b'  # Conversion API token

# Helper function to authorize Backblaze
def authorize_backblaze():
    response = requests.get(BACKBLAZE_AUTH_URL, auth=(KEY_ID, APP_KEY))
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception("Failed to authorize Backblaze")

# Helper function to upload a file to Backblaze
def upload_to_backblaze(api_url, auth_token, upload_url, file_path, file_name):
    headers = {
        'Authorization': auth_token,
        'X-Bz-File-Name': file_name,
        'Content-Type': 'b2/x-auto',
        'X-Bz-Content-Sha1': 'do_not_verify'
    }
    with open(file_path, 'rb') as file_data:
        response = requests.post(upload_url, headers=headers, data=file_data)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to upload file to Backblaze: {response.content.decode()}")

# Endpoint for processing files
@app.route('/process_file', methods=['POST'])
def process_file():
    # Retrieve file and process type from request
    uploaded_file = request.files.get('file')
    process_type = request.form.get('process')

    if not uploaded_file or not process_type:
        return jsonify({"error": "File and process type are required"}), 400

    # Save file to local directory
    if not os.path.exists(LOCAL_STORAGE):
        os.makedirs(LOCAL_STORAGE)
    file_path = os.path.join(LOCAL_STORAGE, uploaded_file.filename)
    uploaded_file.save(file_path)

    try:
        # Process Type 1: Convert document to JPEG only
        if process_type == '1':
            converted_url = convert_to_jpeg(file_path)
            return jsonify({"converted_url": converted_url})

        # Process Type 2: Upload existing file to Backblaze
        elif process_type == '2':
            auth_data = authorize_backblaze()
            upload_response = upload_file_to_backblaze(file_path, uploaded_file.filename, auth_data)
            return jsonify({"backblaze_response": upload_response})

        # Process Type 3: Convert and then upload to Backblaze
        elif process_type == '3':
            # Convert file to JPEG
            converted_url = convert_to_jpeg(file_path)

            # Download the converted file to local folder
            converted_file_path = download_file(converted_url, uploaded_file.filename)

            # Authorize and upload to Backblaze
            auth_data = authorize_backblaze()
            upload_response = upload_file_to_backblaze(converted_file_path, uploaded_file.filename, auth_data)

            return jsonify({
                "converted_url": converted_url,
                "backblaze_response": upload_response,
                "public_link": generate_backblaze_public_link(auth_data, uploaded_file.filename)
            })

        else:
            return jsonify({"error": "Invalid process type. Choose 1, 2, or 3."}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Helper function to convert document to JPEG
def convert_to_jpeg(file_path):
    files = {'file': open(file_path, 'rb')}
    data = {
        'to': 'jpeg',
        'compress': '',
        'token':'8747d93b31419ff444c769a7c1d8ab3b'  # Include the token here
    }

    try:
        response = requests.post(CONVERSION_API_URL, files=files, data=data)

        # Debugging: Print response status and content
        print(f"Conversion API Response Status: {response.status_code}")
        print(f"Conversion API Response Content: {response.content.decode()}")

        if response.status_code == 200:
            converted_file_url = response.json().get('CONVERTED_FILE')

            if not converted_file_url:
                raise Exception("Failed to get the converted file URL from the response")

            return converted_file_url
        else:
            raise Exception(f"Conversion failed with status code {response.status_code}: {response.content.decode()}")

    except Exception as e:
        print(f"Error in convert_to_jpeg: {str(e)}")
        raise

# Helper function to download the file
def download_file(url, filename):
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        local_file_path = os.path.join(LOCAL_STORAGE, filename)
        with open(local_file_path, 'wb') as file:
            shutil.copyfileobj(response.raw, file)
        return local_file_path
    else:
        raise Exception("Failed to download the file")

# Helper function to upload file to Backblaze
def upload_file_to_backblaze(file_path, file_name, auth_data):
    api_url = auth_data['apiUrl']
    auth_token = auth_data['authorizationToken']

    # Get upload URL
    upload_url_resp = requests.post(
        f"{api_url}/b2api/v2/b2_get_upload_url",
        headers={'Authorization': auth_token},
        json={'bucketId': BACKBLAZE_BUCKET_ID}
    )

    if upload_url_resp.status_code != 200:
        raise Exception(f"Failed to get upload URL: {upload_url_resp.content.decode()}")

    upload_url_data = upload_url_resp.json()
    upload_url = upload_url_data['uploadUrl']
    upload_auth_token = upload_url_data['authorizationToken']

    # Upload file
    return upload_to_backblaze(api_url, upload_auth_token, upload_url, file_path, file_name)

# Helper function to generate public download link
def generate_backblaze_public_link(auth_data, file_name):
    download_url = auth_data['downloadUrl']
    return f"{download_url}/file/{BACKBLAZE_BUCKET_NAME}/{file_name}"


if __name__ == '__main__':
    app.run()
