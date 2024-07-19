import os
import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSlider, QLabel
from PyQt5.QtCore import QTimer, Qt
import pyqtgraph as pg
from data_processing import read_and_process_file, get_data_files, DATA_DIR, PLOT_WINDOW, READINGS_PER_FILE, SENSOR_COUNT

class MainApplication(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout(self)
        self.plot_widget, self.curves = self.setup_plots()
        
        self.file_range_label = QLabel("Displaying files: None")
        self.highest_file_label = QLabel("Current highest file: None")
        self.layout.addWidget(self.file_range_label)
        self.layout.addWidget(self.highest_file_label)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(0)  # Will be updated dynamically based on the number of available files
        self.slider.setValue(0)
        self.layout.addWidget(self.slider)

        self.setLayout(self.layout)
        self.resize(2600, 1400)
        self.show()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(100)  # Time before next poll

        self.last_processed_files = []

    def setup_plots(self):
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
        self.layout.addWidget(plot_widget)
        return plots, curves

    def update(self):
        files = get_data_files(DATA_DIR)
        num_files = len(files)
        if num_files == 0:
            self.file_range_label.setText("Displaying files: None")
            self.highest_file_label.setText("Current highest file: None")
            self.slider.setMaximum(0)
            return

        slider_at_max = self.slider.value() == self.slider.maximum()
        self.slider.setMaximum(max(0, num_files - PLOT_WINDOW))

        if slider_at_max:
            self.slider.setValue(self.slider.maximum())

        window_start_index = self.slider.value()
        window_end_index = min(window_start_index + PLOT_WINDOW, num_files)
        displayed_files = files[window_start_index:window_end_index]

        self.last_processed_files = displayed_files

        all_data = [read_and_process_file(f) for f in displayed_files if os.path.getsize(f) > 0]
        all_data = [data for data in all_data if data is not None]

        self.update_plots(all_data)

        file_numbers = [os.path.splitext(os.path.basename(f))[0] for f in displayed_files]
        if file_numbers:
            self.file_range_label.setText(f"Displaying files: {file_numbers[0]} to {file_numbers[-1]}")
        else:
            self.file_range_label.setText("Displaying files: None")

        self.highest_file_label.setText(f"Current highest file: {os.path.basename(files[-1]) if files else 'None'}")

    def update_plots(self, all_data):
        for i, curve_group in enumerate(self.curves):
            sensor_index = i // 6
            measure_index = i % 6
            sensor_data = np.vstack([file_data[:, sensor_index * 6 + measure_index] for file_data in all_data if file_data is not None])
            if sensor_data.size > 0:
                flattened_data = sensor_data[-READINGS_PER_FILE:].ravel()  # Flatten the data
                curve_group.setData(flattened_data)
            else:
                print(f"No data for sensor {sensor_index}, measurement {measure_index}")

