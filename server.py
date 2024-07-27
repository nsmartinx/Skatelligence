from flask import Flask, request
import os
from data_processing import process_files

app = Flask(__name__)

BASE_DIR = os.path.dirname(__file__)
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'data/live/raw_data')

@app.route('/postdata', methods=['POST'])
def upload_file():
    file = request.files.get('file')
    if not file:
        return "No file part in the request", 400
    filename = file.filename or "default_name.bin"
    if filename.startswith("/"):
        filename = filename[1:]  # Remove leading slash to ensure filenames are relative to UPLOAD_FOLDER
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    print(f"Received and saved file: {filename}")  # Print the name of the file
    process_files()
    return f"File {filename} uploaded successfully", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)

