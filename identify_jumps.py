import os
import glob
import numpy as np

# Constants
ACCEL_SCALE = 16  # +/- ACCEL_SCLAE are the min/max readings of the accelerometer (
GYRO_SCALE = 2000 # +/- GYRO_SCALE are the min/max readings of the gyroscope (deg/sec)
READINGS_PER_FILE = 100
SENSOR_COUNT = 5
BASE_DIR = os.path.dirname(__file__)
PROCESSED_DIR = os.path.join(BASE_DIR, 'data/live/processed_data')  # Directory containing processed data
JUMPS_DIR = os.path.join(BASE_DIR, 'data/live/jumps')
JUMP_LENGTH = 150
END_BUFFER = 30
SAMPLING_RATE = 100.0  # Hz of IMU sampling
MIN_JUMP_DURATION = 0.2  # Minimum duration of a jump in seconds
MAX_JUMP_DURATION = 0.8  # Maximum duration of a jump in seconds
LOW_THRESHOLD = 0.5  # Acceleration must drop below this value while skater is airborn (in Gs)
HIGH_THRESHOLD = 1.5  # Acceleration must be above this value on takeoff and landing (in Gs)
MINIMUM_ROTATION = 180 # Minimum number of degress that must be rotated for it to be considered a jump

# States for jump detection
STATE_GROUNDED = 0
STATE_TAKEOFF = 1
STATE_IN_AIR = 2

# Temporary Bugfix:
previous_end = -1

def read_accelerometer_data(file_path):
    """
    Reads a binary file containing accelerometer data and returns it as a numpy array of signed 16-bit integers.

    Args:
        file_path (str): The path to the binary file.

    Returns:
        numpy.array or None: Array of accelerometer data or None if the file is empty or unreadable.
    """

    try:
        data = np.fromfile(file_path, dtype=np.int16)
        if data.size == 0:
            return None
        return data
    except Exception as e:
        return None

def extract_data(data, start_index, SCALE):
    """
    Extracts and scales one specific stream of data from the raw array. If the sensor index is n, the start index is:
    6n: x_accel
    6n+1: y_accel
    6n+2: z_accel
    6n+3: x_gyro
    6n+4: y_gyro
    6n+5: z_gyro

    Args:
        data (numpy.array): The raw data array.
        start_index (int): The index to start extracting from
        SCALE (int): The amount that the values are scalled by, either ACCEL_SCALE or GYRO_SCALE

    Returns:
        numpy.array: The extracted scaled values.
    """

    extracted_data = data[start_index::30]  # Extract every 30th value starting from the start_index
    extracted_data_scaled = (extracted_data / 32768.0) * SCALE  # Scale the readings to the accelerometer range
    return extracted_data_scaled

def compute_total_rotation(x_gyro_data):
    """
    Computes the total rotation of a jump by numerically integrating the x-axis gyroscope data.

    Args:
        x_gro_data (numpy.array): The scaled x-axis gyroscope data array

    Returns:
        float: Total rotation on x axis 

    """
    time_interval = 1 / SAMPLING_RATE
    total_rotation = np.sum(x_gyro_data) * time_interval
    return total_rotation

def is_valid_jump(data):
    """
    Runs checks to ensure the potential identified jumps meet the criteria for a jump. This includes:
    1. Total rotation > 180 degrees
    2. Skate sees acceleration of at least 5 Gs at some point (this occurs at takeoff)

    Args: 
        data (numpy.array): The raw data array

    Returns:
        Bool: If jump is valid
    """
    total_rotation = abs(compute_total_rotation(extract_data(data, 3, GYRO_SCALE)))
    print(f"rotation: {total_rotation}")
    accel_data = extract_data(data, 19, ACCEL_SCALE)
    maximum = np.max(accel_data[:len(accel_data) // 2])
    print(f"max: {maximum}")
    return total_rotation  > MINIMUM_ROTATION and maximum > 5

def detect_jumps(x_accel_data, start_time_offset):
    """
    Detects jumps based on x-axis acceleration data, using state machine logic to define jump phases.

    Args:
        x_accel_data (numpy.array): Array of scaled x-axis acceleration data.
        start_time_offset (float): Time offset to calculate actual time of readings.

    Returns:
        list of tuple: List of tuples, each representing a detected jump as (jump_start_time, jump_end_time).
    """

    jumps = [] # Will be a list of tuples of floats containing the start and end time for a jump
    state = STATE_GROUNDED
    jump_start = 0.0
    jump_start_time = 0.0

    for i in range(len(x_accel_data)):
        # If the first file has been analyzed and it is not currently in the middle of a jump, stop.
        # This is because the second file will be analyzed in the next call to the function anyways
        if i >= READINGS_PER_FILE and state == STATE_GROUNDED:
            return jumps

        x_accel = x_accel_data[i]
        current_time = start_time_offset + i / SAMPLING_RATE  # Calculate the current time in seconds
        if state == STATE_GROUNDED:
            # If accel goes above threshold, register a takeoff
            if x_accel > HIGH_THRESHOLD:
                state = STATE_TAKEOFF
                jump_start = i
                jump_start_time = current_time
        
        elif state == STATE_TAKEOFF:
            # If still in the takeoff phase, we will reset the start time
            if x_accel > HIGH_THRESHOLD:
                jump_start_time = current_time

            # If accel drops below low threshold, set to air state
            if x_accel < LOW_THRESHOLD:
                state = STATE_IN_AIR

            # Reset if the jump exceeds the maximum duration
            current_duration = current_time - jump_start_time  # Calculate the current duration of the jump
            if current_duration > MAX_JUMP_DURATION:
                state = STATE_GROUNDED
        
        elif state == STATE_IN_AIR:
            current_duration = current_time - jump_start_time  # Calculate the current duration of the jump

            # If high acceleration spike after being in the air, they have landed
            if x_accel > HIGH_THRESHOLD:
                jump_end = i
                jump_end_time = current_time
                if MIN_JUMP_DURATION <= current_duration <= MAX_JUMP_DURATION: # Ensure it within acceptable time range
                    jumps.append((jump_start_time, jump_end_time))
                state = STATE_GROUNDED

            # Reset if the jump exceeds the maximum duration
            if current_duration > MAX_JUMP_DURATION:
                state = STATE_GROUNDED

    return jumps

def process_files_and_detect_jumps(index, processed_dir):
    """
    Processes two consecutive accelerometer data files to detect jumps and save detected jump data.

    Args:
        index (int): Index of the most recent file. Files index-1 and index-2 will be analyzed for jumps. 
        Files index-3 and index will be used when saving a jump. This index is based on the naming convention of the files.

    Returns:
        None: Detected jumps are processed and saved to disk. Messages are printed to indicate detected jumps and save status.
    """
    
    global previous_end
    if index == 3:
        previous_end = -1
    
    PROCESSED_DIR = processed_dir
    JUMPS_DIR = os.path.join(os.path.dirname(PROCESSED_DIR), 'jumps')	

    print(f'Processing file {index-1} and {index-2} for jumps')
    # Get all of the files in the filtered_data directory
    files = glob.glob(os.path.join(PROCESSED_DIR, '*.bin'))
    files.sort(key=lambda x: int(os.path.splitext(os.path.basename(x))[0]))
    all_jumps = [] # List of tuples, format is (jump_start_time, jump_end_time)

    if 2 < index < len(files):
        # Get numpy array of data for index - 1 and index - 2 files
        data_prev = read_accelerometer_data(files[index - 2])
        data_curr = read_accelerometer_data(files[index - 1])

        data_pre = read_accelerometer_data(files[index - 3])
        data_post = read_accelerometer_data(files[index])

        if data_prev is not None and data_curr is not None:
            # Get the acceleration data
            x_accel_prev = extract_data(data_prev, 0, ACCEL_SCALE)
            x_accel_curr = extract_data(data_curr, 0, ACCEL_SCALE)
            start_time_offset = (index - 2) * READINGS_PER_FILE / SAMPLING_RATE
            
            # Combine the two data arrays into one and find the jumps in it
            jumps = detect_jumps(
                np.concatenate([x_accel_prev, x_accel_curr]),
                start_time_offset,
            )
            all_jumps.extend(jumps)

        # Process each new jump for saving
        for jump in all_jumps:

            jump_start_time, jump_end_time = jump
            print(f"Detected jump from {jump_start_time:.2f}s to {jump_end_time:.2f}s")
                
            # Calculate the start and end index in the files, this is the index relative to the concatenation of
            # data_prev and data_curr.
            end_index = (int((jump_end_time - index + 2) * READINGS_PER_FILE) + END_BUFFER) * 30 + 30 + (READINGS_PER_FILE * 30)
            start_index = end_index - (JUMP_LENGTH * 30)
            print(f'start_index: {start_index}. end_index: {end_index}')
            
            if abs(end_index + 3000 - previous_end) <= 20:
                print("Duplicate Jump Detected")
                continue
            previous_end = end_index
            
            # Determine what number jump this is
            jump_files = glob.glob(os.path.join(JUMPS_DIR, 'jump_*.bin'))
            if jump_files:
                # Extract numbers from file names and find the maximum
                jump_counter = max(int(os.path.splitext(os.path.basename(f))[0].split('_')[1]) for f in jump_files) + 1
            else:
                jump_counter = 0  # Start from 0 if no files are found
            
            # Extract and save jump data
            jump_data = np.concatenate([data_pre, data_prev, data_curr, data_post])[start_index:end_index]
            jump_data = jump_data.astype(np.int16)
            
            # Check if the jump has the minimum rotation to be considered a jump
            if is_valid_jump(jump_data):
                jump_file_path = os.path.join(JUMPS_DIR, f'jump_{jump_counter}.bin')
                jump_data.tofile(jump_file_path)
            
                file_size = os.path.getsize(jump_file_path)
                print(f"Jump data saved to {jump_file_path}")
            else:
                print("Jump not valid")

