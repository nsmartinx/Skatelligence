import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
from PyQt5.QtCore import QTimer
import os
import glob
import shutil

# Constants
ACCEL_SCALE = 16  # +/- 16 g
GYRO_SCALE = 2000  # +/- 2000 deg/second
READINGS_PER_FILE = 100
SENSOR_COUNT = 5
DATA_DIR = "</Path/to/folder>"
PLOT_WINDOW = 10  # Number of files to display in the plot

# Function to clear the directory
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

# Clear the data directory at startup
clear_directory(DATA_DIR)

# Setup application and main widget
app = QApplication([])
main_widget = QWidget()
layout = QVBoxLayout(main_widget)

# Setup pyqtgraph plot widget
plot_widget = pg.GraphicsLayoutWidget()
plots = []
curves = []
for i in range(SENSOR_COUNT):
    accel_plot = plot_widget.addPlot(row=i, col=0, title=f"Sensor {i} Acceleration")
    gyro_plot = plot_widget.addPlot(row=i, col=1, title=f"Sensor {i} Gyroscope")
    plots.extend([accel_plot, gyro_plot])
    curves.extend([accel_plot.plot(pen='r'), accel_plot.plot(pen='g'), accel_plot.plot(pen='b'),
                   gyro_plot.plot(pen='r'), gyro_plot.plot(pen='g'), gyro_plot.plot(pen='b')])
    accel_plot.setXRange(0, READINGS_PER_FILE * PLOT_WINDOW)
    gyro_plot.setXRange(0, READINGS_PER_FILE * PLOT_WINDOW)
file_range_label = QLabel("Displaying files: None")
layout.addWidget(plot_widget)
layout.addWidget(file_range_label)

main_widget.setLayout(layout)
main_widget.resize(2600, 1400)
main_widget.show()

# Function to read and process files
def read_and_process_file(file_path):
    data = np.fromfile(file_path, dtype=np.int16)
    if data.size == 0:
        print(f"Warning: {file_path} is empty.")
        return None
    data = data.reshape((-1, SENSOR_COUNT * 6))
    scale_vector = np.tile(np.hstack([ACCEL_SCALE]*3 + [GYRO_SCALE]*3), SENSOR_COUNT)
    scaled_data = (data / 32768.0) * scale_vector
    return scaled_data

# Update function to refresh plots
last_processed_files = []  # Keep track of the last processed files
def update():
    global last_processed_files
    files = sorted(glob.glob(os.path.join(DATA_DIR, '*.bin')), key=os.path.getmtime)[-PLOT_WINDOW:]
    if not files:
        file_range_label.setText("Displaying files: None")
        return
    
    if files == last_processed_files:
        return  # Skip processing if the files have not changed
    last_processed_files = files
    
    all_data = [read_and_process_file(f) for f in files if os.path.getsize(f) > 0]
    all_data = [data for data in all_data if data is not None]
    
    for i, curve_group in enumerate(curves):
        sensor_index = i // 6
        measure_index = i % 6
        sensor_data = np.vstack([file_data[:, sensor_index * 6 + measure_index] for file_data in all_data if file_data is not None])
        if sensor_data.size > 0:
            flattened_data = sensor_data[-READINGS_PER_FILE:].ravel()  # Flatten the data
            curve_group.setData(flattened_data)
        else:
            print(f"No data for sensor {sensor_index}, measurement {measure_index}")

    file_numbers = [os.path.splitext(os.path.basename(f))[0] for f in files]
    if file_numbers:
        file_range_label.setText(f"Displaying files: {file_numbers[0]} to {file_numbers[-1]}")
    else:
        file_range_label.setText("Displaying files: None")

timer = QTimer()
timer.timeout.connect(update)
timer.start(100)  # Time before next poll

if __name__ == '__main__':
    app.exec_()  # Start the application loop

