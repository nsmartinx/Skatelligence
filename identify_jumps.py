import os
import glob
import numpy as np

# Constants
ACCEL_SCALE = 16  # +/- 16 g
READINGS_PER_FILE = 100
SENSOR_COUNT = 5
BASE_DIR = os.path.dirname(__file__)
PROCESSED_DIR = os.path.join(BASE_DIR, 'processed_data')  # Directory containing processed data
JUMPS_DIR = os.path.join(BASE_DIR, 'jumps')
BUFFER_READINGS = 10
SAMPLING_RATE = 100.0  # 100 Hz
MIN_JUMP_DURATION = 0.2  # Minimum duration of a jump in seconds
MAX_JUMP_DURATION = 0.8  # Maximum duration of a jump in seconds
ZERO_G_THRESHOLD = 0.5  # Threshold for near 0g during the jump
SPIKE_THRESHOLD = 1.5  # Threshold for detecting spikes

# States for jump detection
STATE_GROUNDED = 0
STATE_TAKEOFF = 1
STATE_IN_AIR = 2

# Function to read data from a binary file
def read_accelerometer_data(file_path):
    try:
        data = np.fromfile(file_path, dtype=np.int16)
        if data.size == 0:
            return None
        return data
    except Exception as e:
        return None

# Function to extract x-axis acceleration values from the data
def extract_x_accel(data):
    x_accel = data[0::30]  # Extract every 30th value starting from the 0th
    x_accel_scaled = (x_accel / 32768.0) * ACCEL_SCALE  # Scale to +/- 16g
    return x_accel_scaled

# Function to detect potential jumps
def detect_jumps(x_accel_data, start_time_offset):
    jumps = []
    state = STATE_GROUNDED 
    jump_start = 0.0
    jump_start_time = 0.0

    for i in range(len(x_accel_data)):
        if i >= READINGS_PER_FILE and state == STATE_GROUNDED:
            return jumps

        x_accel = x_accel_data[i]
        current_time = start_time_offset + i / SAMPLING_RATE  # Calculate the current time in seconds

        if state == STATE_GROUNDED:
            if x_accel > SPIKE_THRESHOLD:  # Detect takeoff spike
                state = STATE_TAKEOFF
                jump_start = i
                jump_start_time = current_time
        
        elif state == STATE_TAKEOFF:
            if x_accel > SPIKE_THRESHOLD:
                jump_start_time = current_time

            if x_accel < ZERO_G_THRESHOLD:  # Transition to in-air when acceleration drops below 0.5g
                state = STATE_IN_AIR

            # Reset if the jump exceeds the maximum duration
            current_duration = current_time - jump_start_time  # Calculate the current duration of the jump
            if current_duration > MAX_JUMP_DURATION:
                state = STATE_GROUNDED
        
        elif state == STATE_IN_AIR:
            current_duration = current_time - jump_start_time  # Calculate the current duration of the jump

            if x_accel > SPIKE_THRESHOLD:  # Detect landing spike
                jump_end = i
                jump_end_time = current_time
                if MIN_JUMP_DURATION <= current_duration <= MAX_JUMP_DURATION:
                    jumps.append((jump_start_time, jump_end_time))
                state = STATE_GROUNDED

            # Reset if the jump exceeds the maximum duration
            if current_duration > MAX_JUMP_DURATION:
                state = STATE_GROUNDED

    return jumps

def process_files_and_detect_jumps(index):
    files = glob.glob(os.path.join(PROCESSED_DIR, '*.bin'))
    files.sort(key=lambda x: int(os.path.splitext(os.path.basename(x))[0]))
    all_jumps = []

    if 0 < index < len(files):
        data_prev = read_accelerometer_data(files[index - 1])
        data_curr = read_accelerometer_data(files[index])
        if data_prev is not None and data_curr is not None:
            x_accel_prev = extract_x_accel(data_prev)
            x_accel_curr = extract_x_accel(data_curr)
            start_time_offset = (index - 1) * READINGS_PER_FILE / SAMPLING_RATE
            
            jumps = detect_jumps(
                np.concatenate([x_accel_prev, x_accel_curr]),
                start_time_offset,
            )
            all_jumps.extend(jumps)

        # Process each new jump for saving
        for jump in all_jumps:
            jump_start_time, jump_end_time = jump
            print(f"Detected jump from {jump_start_time:.2f}s to {jump_end_time:.2f}s")
                
            start_index = (int((jump_start_time - index + 1) * SAMPLING_RATE) - BUFFER_READINGS) * 30
            end_index = (int((jump_end_time - index + 1) * SAMPLING_RATE) + BUFFER_READINGS) * 30 + 30 
            
            jump_files = glob.glob(os.path.join(JUMPS_DIR, 'jump_*.bin'))
            if jump_files:
                # Extract numbers from file names and find the maximum
                jump_counter = max(int(os.path.splitext(os.path.basename(f))[0].split('_')[1]) for f in jump_files) + 1
            else:
                jump_counter = 0  # Start from 0 if no files are found
            
            # Extract and save jump data
            jump_data = np.concatenate([data_prev, data_curr])[start_index:end_index]
            jump_data = jump_data.astype(np.int16)  # Ensure data is converted to 16-bit integers
            jump_file_path = os.path.join(JUMPS_DIR, f'jump_{jump_counter}.bin')
            
            jump_data.tofile(jump_file_path)  # Save as binary file in 16-bit format
            
            file_size = os.path.getsize(jump_file_path)
            print(f"Jump data saved to {jump_file_path}")

