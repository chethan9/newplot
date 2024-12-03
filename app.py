from flask import Flask, request, jsonify
import os
import requests
import shutil
import urllib.parse

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
CONVERSION_API_TOKEN = '8747d93b31419ff444c769a7c1d8ab3b'

# Supported formats (top 15)
SUPPORTED_FORMATS = [
    'jpeg', 'png', 'pdf', 'doc', 'docx', 'xls',
    'xlsx', 'pptx', 'odt', 'rtf', 'txt', 'csv',
    'ppt', 'dot', 'xml'
]

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

# Helper function to sanitize the file name
def sanitize_filename(filename):
    return urllib.parse.quote(filename.replace(' ', '_'))

# Endpoint for processing files
@app.route('/process_file', methods=['POST'])
def process_file():
    uploaded_file = request.files.get('file')
    process_type = request.form.get('process')
    target_format = request.form.get('format')

    if not uploaded_file or not process_type:
        return jsonify({"error": "File and process type are required"}), 400

    # For Process Types 1 and 3, 'format' is required
    if process_type in ['1', '3'] and not target_format:
        return jsonify({"error": "Format is required for process types 1 and 3"}), 400

    if target_format:
        target_format = target_format.lower()
        if target_format not in SUPPORTED_FORMATS:
            return jsonify({"error": f"Unsupported format. Supported formats are: {', '.join(SUPPORTED_FORMATS)}"}), 400

    # Save file to local directory
    if not os.path.exists(LOCAL_STORAGE):
        os.makedirs(LOCAL_STORAGE)
    file_path = os.path.join(LOCAL_STORAGE, uploaded_file.filename)
    uploaded_file.save(file_path)

    try:
        # Process Type 1: Convert document to specified format only
        if process_type == '1':
            converted_url = convert_to_format(file_path, target_format)
            return jsonify({"converted_url": converted_url})

        # Process Type 2: Upload existing file to Backblaze
        elif process_type == '2':
            auth_data = authorize_backblaze()

            # Sanitize the file name before uploading
            sanitized_filename = sanitize_filename(uploaded_file.filename)

            upload_response = upload_file_to_backblaze(file_path, sanitized_filename, auth_data)
            public_link = generate_backblaze_public_link(auth_data, sanitized_filename)

            return jsonify({
                "backblaze_response": upload_response,
                "public_link": public_link
            })

        # Process Type 3: Convert and then upload to Backblaze
        elif process_type == '3':
            # Convert file to specified format
            converted_url = convert_to_format(file_path, target_format)

            # Download the converted file to local folder
            converted_filename = f"{os.path.splitext(uploaded_file.filename)[0]}.{target_format}"
            converted_file_path = download_file(converted_url, converted_filename)

            # Authorize and upload the converted file to Backblaze
            auth_data = authorize_backblaze()
            sanitized_filename = sanitize_filename(converted_filename)

            upload_response = upload_file_to_backblaze(converted_file_path, sanitized_filename, auth_data)
            public_link = generate_backblaze_public_link(auth_data, sanitized_filename)

            return jsonify({
                "converted_url": converted_url,
                "backblaze_response": upload_response,
                "public_link": public_link
            })

        else:
            return jsonify({"error": "Invalid process type. Choose 1, 2, or 3."}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Helper function to convert document to specified format
def convert_to_format(file_path, target_format):
    files = {'file': open(file_path, 'rb')}
    data = {
        'to': target_format,
        'compress': '',
        'token': CONVERSION_API_TOKEN  # Include the token in the request
    }

    try:
        response = requests.post(CONVERSION_API_URL, files=files, data=data)

        # Debugging: Print response status and content
        print(f"Conversion API Response Status: {response.status_code}")
        print(f"Conversion API Response Content: {response.content.decode()}")

        if response.status_code in [200, 201]:  # Success for 200 or 201
            response_data = response.json()
            converted_file_url = response_data.get('CONVERTED_FILE')

            if not converted_file_url:
                raise Exception("Failed to get the converted file URL from the response")

            return converted_file_url
        else:
            raise Exception(f"Conversion failed with status code {response.status_code}: {response.content.decode()}")

    except Exception as e:
        print(f"Error in convert_to_format: {str(e)}")
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


from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

app = Flask(__name__)

# Function to generate Google Maps URL
def generate_maps_url(source_lat, source_lng, dest_lat, dest_lng):
    # Calculate the center point (midpoint)
    center_lat = (source_lat + dest_lat) / 2
    center_lng = (source_lng + dest_lng) / 2

    url = f"https://www.google.com/maps/dir/{source_lat},{source_lng}/{dest_lat},{dest_lng}/@{center_lat},{center_lng},14z/data=!3m1!4b1!4m10!4m9!1m3!2m2!1d{source_lng}!2d{source_lat}!1m3!2m2!1d{dest_lng}!2d{dest_lat}!3e0?entry=ttu"
    return url

# Web scraping function using Selenium to get time and distance
def scrape_distance_time(url):
    # Set up Chrome driver (assuming you have ChromeDriver installed)
    options = Options()
    options.headless = True  # Run headless so no window pops up
    service = Service("/path/to/chromedriver")  # Specify your ChromeDriver path
    driver = webdriver.Chrome(service=service, options=options)

    driver.get(url)
    time.sleep(5)  # Wait for the page to load completely

    try:
        # Scrape the time and distance using the 'fontHeadlineSmall' class
        time_elements = driver.find_elements(By.CLASS_NAME, "fontHeadlineSmall")
        
        # Assuming the time and distance are the first two elements in the list
        time_str = time_elements[0].text if time_elements else "Not Found"
        distance_str = time_elements[1].text if len(time_elements) > 1 else "Not Found"

        driver.quit()
        return {"time": time_str, "distance": distance_str}
    except Exception as e:
        driver.quit()
        return {"error": str(e)}

# Endpoint to receive coordinates and return distance and time
@app.route('/get_distance_time', methods=['POST'])
def get_distance_time():
    data = request.get_json()

    source_lat = data.get("source_lat")
    source_lng = data.get("source_lng")
    dest_lat = data.get("dest_lat")
    dest_lng = data.get("dest_lng")

    if not all([source_lat, source_lng, dest_lat, dest_lng]):
        return jsonify({"error": "Missing required coordinates"}), 400

    # Generate Google Maps URL
    url = generate_maps_url(source_lat, source_lng, dest_lat, dest_lng)

    # Scrape the data from the Google Maps URL
    result = scrape_distance_time(url)

    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
