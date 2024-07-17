from flask import Flask, request
import os

app = Flask(__name__)

UPLOAD_FOLDER = "</Path/to/folder>"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
    return f"File {filename} uploaded successfully", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)

