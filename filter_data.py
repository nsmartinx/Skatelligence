import os
import numpy as np
from scipy.signal import butter, filtfilt

# Constants
ACCEL_SCALE = 16  # +/- 16 g
GYRO_SCALE = 2000  # +/- 2000 deg/second
READINGS_PER_FILE = 100
SENSOR_COUNT = 5
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, 'data/live/raw_data')
PROCESSED_DIR = os.path.join(BASE_DIR, 'data/live/processed_data')
CUTOFF_FREQUENCY = 10  # Cutoff frequency for the low-pass filter in Hz
FS = 50  # Sampling frequency in Hz
FILTER_ORDER = 6  # Order of the Butterworth filter

def apply_low_pass_filter(data, cutoff, fs, order):
    """
    Create and apply a low-pass Butterworth filter to the provided data.

    Parameters:
        data (np.array): The input data to filter.
        cutoff (float): The cutoff frequency of the filter in Hz.
        fs (int): The sampling frequency in Hz.
        order (int): The order of the filter (default is 6).

    Returns:
        np.array: The filtered data.
    """

    nyq = 0.5 * fs  # Nyquist Frequency
    normal_cutoff = cutoff / nyq  # Normalize the frequency
    b, a = butter(order, normal_cutoff, btype='low', analog=False)  # Get filter coefficients
    filtered_data = filtfilt(b, a, data, axis=0)  # Apply filter
    return filtered_data

def read_and_process_file(file_path):
    """
    Read data from a file, scale it, and apply a low-pass filter.

    Parameters:
        file_path (str): Path to the file containing raw binary data.

    Returns:
        np.array or None: The processed data as an array, or None if the file is empty.
    """

    data = np.fromfile(file_path, dtype=np.int16)
    if data.size == 0:
        print(f"Warning: {file_path} is empty.")
        return None
    data = data.reshape((-1, SENSOR_COUNT * 6))
    scale_vector = np.tile(np.hstack([ACCEL_SCALE]*3 + [GYRO_SCALE]*3), SENSOR_COUNT)
    scaled_data = (data / 32768.0) * scale_vector
    filtered_data = apply_low_pass_filter(scaled_data, CUTOFF_FREQUENCY, FS, FILTER_ORDER)
    # Scale back to int16
    int_data = (filtered_data * (32768.0 / scale_vector)).astype(np.int16)
    return int_data

def filter_file(file_number, data_dir, processed_dir):
    """
    Process a single data file from its number, apply filters, and save the processed data.

    Parameters:
        file_number (int): The number of the file to process.

    Returns:
        None: Outputs are saved to disk and messages are printed about the status.
    """

    DATA_DIR = data_dir
    PROCESSED_DIR = processed_dir

    file_path = os.path.join(DATA_DIR, f"{file_number}.bin")
    if os.path.exists(file_path):
        filtered_data = read_and_process_file(file_path)
        if filtered_data is not None:
            output_path = os.path.join(PROCESSED_DIR, f"{file_number}.bin")
            filtered_data.tofile(output_path)
            print(f"Processed and saved: {output_path}")
    else:
        print(f"File {file_path} does not exist.")

