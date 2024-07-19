import os
import glob
import numpy as np
from filter_data import process_single_file

# Constants
ACCEL_SCALE = 16  # +/- 16 g
GYRO_SCALE = 2000  # +/- 2000 deg/second
READINGS_PER_FILE = 100
SENSOR_COUNT = 5
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, 'data')
PROCESSED_DIR = os.path.join(BASE_DIR, 'processed_data')  # Added processed data directory
PLOT_WINDOW = 10  # Number of files to display in the plot

# Function to get the last processed file number
def get_last_processed_file():
    processed_files = glob.glob(os.path.join(PROCESSED_DIR, '*.bin'))
    if not processed_files:
        return -1
    file_numbers = [int(os.path.splitext(os.path.basename(f))[0]) for f in processed_files]
    return max(file_numbers)

last_processed_file = get_last_processed_file()  # Initialize last processed file number

def read_and_process_file(file_path):
    global last_processed_file

    # Find all files in the directory matching the pattern XX.bin
    files = glob.glob(os.path.join(DATA_DIR, '*.bin'))
    if not files:
        print("No files found.")
        return

    # Extract file numbers and find the highest one
    file_numbers = [int(os.path.splitext(os.path.basename(f))[0]) for f in files]
    max_file_number = max(file_numbers)

    # Process files from the last processed file to the highest file number
    for file_number in range(last_processed_file + 1, max_file_number + 1):
        process_single_file(file_number)
        last_processed_file = file_number

    if file_path:
        data = np.fromfile(file_path, dtype=np.int16)
        if data.size == 0:
            print(f"Warning: {file_path} is empty.")
            return None
        data = data.reshape((-1, SENSOR_COUNT * 6))
        scale_vector = np.tile(np.hstack([ACCEL_SCALE]*3 + [GYRO_SCALE]*3), SENSOR_COUNT)
        scaled_data = (data / 32768.0) * scale_vector
        return scaled_data

def get_data_files(data_dir):
    return sorted(glob.glob(os.path.join(data_dir, '*.bin')), key=os.path.getmtime)

# The entry point for processing files
if __name__ == '__main__':
    # Directory containing the files
    data_directory = DATA_DIR  # Use the constant defined above

    # Process new files in the directory
    read_and_process_file(None)

