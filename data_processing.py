import os
import glob
import numpy as np
from filter_data import process_single_file
from identify_jumps import process_files_and_detect_jumps  # Import the function

# Constants
ACCEL_SCALE = 16  # +/- 16 g
GYRO_SCALE = 2000  # +/- 2000 deg/second
READINGS_PER_FILE = 100
SENSOR_COUNT = 5
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, 'data')
PROCESSED_DIR = os.path.join(BASE_DIR, 'processed_data')
PLOT_WINDOW = 10  # Number of files to display in the plot

'''
Returns the largest index of processed files
'''
def get_last_processed_file():
    processed_files = glob.glob(os.path.join(PROCESSED_DIR, '*.bin'))
    if not processed_files:
        return -1
    file_numbers = [int(os.path.splitext(os.path.basename(f))[0]) for f in processed_files]
    return max(file_numbers)

last_processed_file = get_last_processed_file()  # Initialize last processed file number

"""
Returns an array of the scaled accel/gyro readings. This function will also call the appropriate functions
to filter the data and find the jumps in the data. You can pass "None" into this function in order to just
filter the data and find jumps without returning anything.
"""
def read_and_process_file(file_path):
    global last_processed_file

    # Find all files in the directory matching the pattern XX.bin
    files = glob.glob(os.path.join(DATA_DIR, '*.bin'))
    if not files:
        print("No files found.")
        return

    # Find the highest file number that has been recorded
    file_numbers = [int(os.path.splitext(os.path.basename(f))[0]) for f in files]
    max_file_number = max(file_numbers)

    # Process files from the last processed file to the highest file number
    for file_number in range(last_processed_file + 1, max_file_number + 1):
        process_single_file(file_number)
        last_processed_file = file_number

        # Call identify_jumps on processed files. Do not call on file 0 as identify jumps requires one file before it
        if file_number != 0:
            process_files_and_detect_jumps(file_number)

    # Scale the data and return that array
    if file_path:
        data = np.fromfile(file_path, dtype=np.int16)
        if data.size == 0:
            print(f"Warning: {file_path} is empty.")
            return None
        data = data.reshape((-1, SENSOR_COUNT * 6))
        scale_vector = np.tile(np.hstack([ACCEL_SCALE]*3 + [GYRO_SCALE]*3), SENSOR_COUNT)
        scaled_data = (data / 32768.0) * scale_vector
        return scaled_data

'''
Returns all files in the direcotory sorted by file name
'''
def get_data_files(data_dir):
    return sorted(glob.glob(os.path.join(data_dir, '*.bin')), key=os.path.getmtime)

