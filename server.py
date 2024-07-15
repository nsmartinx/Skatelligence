from flask import Flask, request
import os
import shutil

app = Flask(__name__)

UPLOAD_FOLDER = "</Path/to/folder>"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def clear_directory(path):
    for filename in os.listdir(path):
        file_path = os.path.join(path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')

# Clear the upload folder at startup
clear_directory(UPLOAD_FOLDER)

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

