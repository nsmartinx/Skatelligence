import os
import glob
import numpy as np

# Constants
ACCEL_SCALE = 16  # +/- 16 g
READINGS_PER_FILE = 100
SENSOR_COUNT = 5
BASE_DIR = os.path.dirname(__file__)
PROCESSED_DIR = os.path.join(BASE_DIR, 'processed_data')  # Directory containing processed data
X_AXIS_INDEXES = [i * 30 for i in range(READINGS_PER_FILE)]
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
def detect_jumps(x_accel_data, start_time_offset, initial_state, initial_jump_start, initial_jump_start_time):
    jumps = []
    state = initial_state
    jump_start = initial_jump_start
    jump_start_time = initial_jump_start_time

    for i in range(1, len(x_accel_data)):
        x_accel = x_accel_data[i]
        current_time = start_time_offset + i / SAMPLING_RATE  # Calculate the current time in seconds

        if state == STATE_GROUNDED:
            if x_accel > SPIKE_THRESHOLD:  # Detect takeoff spike
                state = STATE_TAKEOFF
                jump_start = i
                jump_start_time = current_time
        
        elif state == STATE_TAKEOFF:
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

    return jumps, state, jump_start, jump_start_time

# Function to process all files and detect jumps
def process_files_and_detect_jumps():
    files = glob.glob(os.path.join(PROCESSED_DIR, '*.bin'))
    files.sort(key=lambda x: int(os.path.splitext(os.path.basename(x))[0]))
    all_jumps = []
    total_readings = 0
    state = STATE_GROUNDED
    jump_start = None
    jump_start_time = None

    for file in files:
        data = read_accelerometer_data(file)
        if data is not None:
            x_accel_data = extract_x_accel(data)
            jumps, state, jump_start, jump_start_time = detect_jumps(
                x_accel_data, total_readings / SAMPLING_RATE, state, jump_start, jump_start_time
            )
            all_jumps.extend(jumps)
            total_readings += len(x_accel_data)

    for jump_start_time, jump_end_time in all_jumps:
        print(f"Detected jump from {jump_start_time:.2f}s to {jump_end_time:.2f}s")

if __name__ == '__main__':
    process_files_and_detect_jumps()

