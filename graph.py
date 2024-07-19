import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget, QSlider
from PyQt5.QtCore import QTimer, Qt
import os
import glob
import shutil

# Constants
ACCEL_SCALE = 16  # +/- 16 g
GYRO_SCALE = 2000  # +/- 2000 deg/second
READINGS_PER_FILE = 100
SENSOR_COUNT = 5
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, 'data')
PLOT_WINDOW = 10  # Number of files to display in the plot

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
highest_file_label = QLabel("Current highest file: None")
layout.addWidget(plot_widget)
layout.addWidget(file_range_label)
layout.addWidget(highest_file_label)

# Setup slider
slider = QSlider(Qt.Horizontal)
slider.setMinimum(0)
slider.setMaximum(0)  # Will be updated dynamically based on the number of available files
slider.setValue(0)
layout.addWidget(slider)

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
    files = sorted(glob.glob(os.path.join(DATA_DIR, '*.bin')), key=os.path.getmtime)
    num_files = len(files)
    if num_files == 0:
        file_range_label.setText("Displaying files: None")
        highest_file_label.setText("Current highest file: None")
        slider.setMaximum(0)
        return

    # Check if the slider is at its maximum value
    slider_at_max = slider.value() == slider.maximum()

    # Adjust the slider maximum value to reflect the number of available files
    slider.setMaximum(max(0, num_files - PLOT_WINDOW))

    # If the slider was at its maximum value, keep it at the new maximum value
    if slider_at_max:
        slider.setValue(slider.maximum())

    # Determine the window of files to display based on the slider's current value
    window_start_index = slider.value()
    window_end_index = min(window_start_index + PLOT_WINDOW, num_files)
    displayed_files = files[window_start_index:window_end_index]

    # Update the last processed files to avoid reprocessing the same files
    last_processed_files = displayed_files

    # Read and process the selected files
    all_data = [read_and_process_file(f) for f in displayed_files if os.path.getsize(f) > 0]
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

    file_numbers = [os.path.splitext(os.path.basename(f))[0] for f in displayed_files]
    if file_numbers:
        file_range_label.setText(f"Displaying files: {file_numbers[0]} to {file_numbers[-1]}")
    else:
        file_range_label.setText("Displaying files: None")

    # Update the highest file label
    highest_file_label.setText(f"Current highest file: {os.path.basename(files[-1]) if files else 'None'}")

timer = QTimer()
timer.timeout.connect(update)
timer.start(100)  # Time before next poll

if __name__ == '__main__':
    app.exec_()  # Start the application loop

