import os
import numpy as np
from scipy.signal import butter, filtfilt

# Constants
ACCEL_SCALE = 16  # +/- 16 g
GYRO_SCALE = 2000  # +/- 2000 deg/second
READINGS_PER_FILE = 100
SENSOR_COUNT = 5
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, 'data')
PROCESSED_DIR = os.path.join(BASE_DIR, 'processed_data')
CUTOFF_FREQUENCY = 10  # New cutoff frequency for the low-pass filter in Hz
FS = 50  # Sampling frequency in Hz
FILTER_ORDER = 6  # Order of the Butterworth filter

# Ensure the processed_data directory exists
if not os.path.exists(PROCESSED_DIR):
    os.makedirs(PROCESSED_DIR)

def butter_lowpass(cutoff, fs, order=6):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return b, a

def low_pass_filter(data, cutoff, fs, order=6):
    b, a = butter_lowpass(cutoff, fs, order)
    y = filtfilt(b, a, data, axis=0)
    return y

def read_and_process_file(file_path):
    data = np.fromfile(file_path, dtype=np.int16)
    if data.size == 0:
        print(f"Warning: {file_path} is empty.")
        return None
    data = data.reshape((-1, SENSOR_COUNT * 6))
    scale_vector = np.tile(np.hstack([ACCEL_SCALE]*3 + [GYRO_SCALE]*3), SENSOR_COUNT)
    scaled_data = (data / 32768.0) * scale_vector
    filtered_data = low_pass_filter(scaled_data, CUTOFF_FREQUENCY, FS, FILTER_ORDER)
    # Scale back to int16
    int_data = (filtered_data * (32768.0 / scale_vector)).astype(np.int16)
    return int_data

def save_filtered_data(filtered_data, output_path):
    filtered_data.tofile(output_path)

def process_single_file(file_number):
    file_path = os.path.join(DATA_DIR, f"{file_number}.bin")
    if os.path.exists(file_path):
        filtered_data = read_and_process_file(file_path)
        if filtered_data is not None:
            output_path = os.path.join(PROCESSED_DIR, f"{file_number}.bin")
            save_filtered_data(filtered_data, output_path)
            print(f"Processed and saved: {output_path}")
    else:
        print(f"File {file_path} does not exist.")

