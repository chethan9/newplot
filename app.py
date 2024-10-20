import os
from flask import Flask, request, jsonify, send_file
from pdf2image import convert_from_path
from docx import Document
from PIL import Image, ImageDraw
import fitz  # PyMuPDF
import b2sdk.v2

app = Flask(__name__)

# Backblaze B2 credentials
APPLICATION_KEY_ID = '004d9965f7b24df0000000004'
APPLICATION_KEY = 'K004PuDNv5705ek5KUnNpCP7aIQlkFo'
BUCKET_NAME = 'storagevizsoft'

# Initialize B2 API client
def initialize_b2_client():
    info = b2sdk.v2.InMemoryAccountInfo()
    b2_api = b2sdk.v2.B2Api(info)
    b2_api.authorize_account("production", APPLICATION_KEY_ID, APPLICATION_KEY)
    return b2_api

# Utility function to save images as JPEG
def save_image_as_jpeg(image, output_path):
    image.save(output_path, "JPEG")

# Convert PDF to JPEG
def convert_pdf_to_jpeg(file_path):
    images = convert_from_path(file_path, dpi=300)
    output_files = []
    for i, image in enumerate(images):
        output_path = f'/tmp/output_{i}.jpeg'
        save_image_as_jpeg(image, output_path)
        output_files.append(output_path)
    return output_files

# Convert DOCX to JPEG
def convert_docx_to_jpeg(file_path):
    doc = Document(file_path)
    output_files = []
    for i, paragraph in enumerate(doc.paragraphs):
        image = Image.new('RGB', (500, 200), color='white')
        draw = ImageDraw.Draw(image)
        draw.text((10, 10), paragraph.text, fill='black')
        output_path = f'/tmp/output_{i}.jpeg'
        save_image_as_jpeg(image, output_path)
        output_files.append(output_path)
    return output_files

# Convert generic documents (PDF, EPUB) to JPEG
def convert_generic_to_jpeg(file_path):
    doc = fitz.open(file_path)
    output_files = []
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap()
        output_path = f'/tmp/output_{page_num}.jpeg'
        pix.save(output_path)
        output_files.append(output_path)
    return output_files

# Convert images to JPEG
def convert_image_to_jpeg(file_path):
    image = Image.open(file_path)
    output_path = '/tmp/output.jpeg'
    save_image_as_jpeg(image, output_path)
    return [output_path]

# Upload file to Backblaze B2
def upload_to_b2(file_path, b2_api):
    bucket = b2_api.get_bucket_by_name(BUCKET_NAME)
    file_name = os.path.basename(file_path)
    bucket.upload_local_file(local_file=file_path, file_name=file_name)
    print(f'File "{file_name}" uploaded successfully to bucket "{BUCKET_NAME}".')

# Endpoint to handle file conversion and upload to B2
@app.route('/convert-and-upload', methods=['POST'])
def convert_and_upload():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    file_path = os.path.join('/tmp', file.filename)
    file.save(file_path)

    try:
        output_files = []

        # Determine file type and convert accordingly
        if file.filename.lower().endswith('.pdf'):
            output_files = convert_pdf_to_jpeg(file_path)
        elif file.filename.lower().endswith('.docx'):
            output_files = convert_docx_to_jpeg(file_path)
        elif file.filename.lower().endswith(('.epub', '.ppt', '.pptx')):
            output_files = convert_generic_to_jpeg(file_path)
        elif file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            output_files = convert_image_to_jpeg(file_path)
        else:
            return jsonify({"error": "Unsupported file type"}), 400

        # Initialize B2 API client
        b2_api = initialize_b2_client()

        # Upload the first converted JPEG to B2
        if output_files:
            upload_to_b2(output_files[0], b2_api)
            return send_file(output_files[0], mimetype='image/jpeg')

        return jsonify({"error": "No output files generated"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        # Clean up temporary files
        if os.path.exists(file_path):
            os.remove(file_path)
        for output_file in output_files:
            if os.path.exists(output_file):
                os.remove(output_file)

# New endpoint to upload any file directly to B2
@app.route('/upload-to-b2', methods=['POST'])
def upload_to_b2_endpoint():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    file_path = os.path.join('/tmp', file.filename)
    file.save(file_path)

    try:
        # Initialize B2 API client
        b2_api = initialize_b2_client()

        # Upload the file directly to B2
        upload_to_b2(file_path, b2_api)
        return jsonify({"message": f'File "{file.filename}" uploaded successfully to B2'}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        # Clean up the temporary file
        if os.path.exists(file_path):
            os.remove(file_path)

# Main entry point
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
