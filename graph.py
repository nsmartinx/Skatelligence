import os
import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QSlider, QComboBox
from PyQt5.QtCore import QTimer, Qt
import pyqtgraph as pg
from data_processing import read_file, get_data_files, BASE_DIR, DATA_NAME, PROCESSED_NAME, PLOT_WINDOW, READINGS_PER_FILE, SENSOR_COUNT

class MainApplication(QWidget):
    """
    Main application class for the PyQt GUI that plots sensor data. This class handles the GUI creation,
    data plotting, and switching between raw and processed data directories.
    """

    def __init__(self):
        super().__init__()
        
        # The graph can switch between raw data and processed data, self.data_directory is the file path to this. Initialize to raw data
        self.data_path = 'data/live'
        self.data_name = DATA_NAME
        self.data_directory = os.path.join(BASE_DIR, self.data_path, self.data_name)
        self.initUI()

    def initUI(self):
        """
        Initializes the user interface, including layout, plots, buttons, and other interactive elements.
        """

        # Set layout and plots
        self.layout = QVBoxLayout(self)
        self.plot_widget, self.curves = self.setup_plots()
        
        # Initialize text and buttons
        self.file_range_label = QLabel("Displaying files: None")
        self.layout.addWidget(self.file_range_label)

        self.highest_file_label = QLabel("Current highest file: None")
        self.layout.addWidget(self.highest_file_label)

        self.toggle_button = QPushButton("Switch to Processed", self)
        self.toggle_button.clicked.connect(self.toggle_data_source)
        self.toggle_button.setFixedSize(300, 30)
        self.layout.addWidget(self.toggle_button)
        
        self.data_path_dropdown = QComboBox(self)
        self.data_path_dropdown.addItem("Default (data/live)", "data/live")
        self.update_recording_options()
        self.data_path_dropdown.currentIndexChanged.connect(self.change_data_path)
        self.data_path_dropdown.setFixedWidth(300)
        self.layout.addWidget(self.data_path_dropdown)

        # Initilize the slider, min/max values will be changed as filesa re loaded
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(0)
        self.slider.setValue(0)
        self.layout.addWidget(self.slider)
    
        self.setLayout(self.layout)
        self.resize(2600, 1400)
        self.show()
    
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(100)  # Update interval (ms)

    def update_recording_options(self):
        """
        Scans the specified recordings directory and updates the dropdown menu with available recording options.
        It looks for directories that match the pattern 'recording_X' where X is a number, under the BASE_DIR/data/recordings path.
        Each found directory is added as an option to the data path dropdown menu.
        """

        recordings_path = os.path.join(BASE_DIR, "data", "recordings")
        if os.path.exists(recordings_path):
            for entry in os.listdir(recordings_path):
                if os.path.isdir(os.path.join(recordings_path, entry)) and entry.startswith("recording_"):
                    self.data_path_dropdown.addItem(entry, os.path.join("data/recordings", entry))

    def change_data_path(self):
        """
        Updates the data path based on the user's selection from the dropdown menu.
        This method is triggered whenever the selected index in the dropdown changes.
        It sets the new data path, updates the data directory accordingly, and then calls the update method to refresh the data display.
        """

        # Get the selected data path from dropdown
        self.data_path = self.data_path_dropdown.currentData()
        self.data_directory = os.path.join(BASE_DIR, self.data_path, self.data_name)
        print(f"Data path changed to: {self.data_directory}")
        self.update()  # Refresh the plot with the new data path

    def setup_plots(self):
        """
        Initializes the plot widgets for the application, creating individual plots for acceleration and gyroscopic data.
        Returns:
            tuple: A tuple containing the plot widget and a list of curve objects for data plotting.
        """

        plot_widget = pg.GraphicsLayoutWidget()
        plots = []
        curves = []
        for i in range(SENSOR_COUNT):
            # Every sensor has two plots, one for acceleration data, one for gyroscopic
            accel_plot = plot_widget.addPlot(row=i, col=0, title=f"Sensor {i} Acceleration")
            gyro_plot = plot_widget.addPlot(row=i, col=1, title=f"Sensor {i} Gyroscope")
            
            # Add the plots to the list of plots
            plots.extend([accel_plot, gyro_plot])

            # Each plot will ahve three lines on it (for each of x, y, z data)
            curves.extend([accel_plot.plot(pen='r'), accel_plot.plot(pen='g'), accel_plot.plot(pen='b'),
                           gyro_plot.plot(pen='r'), gyro_plot.plot(pen='g'), gyro_plot.plot(pen='b')])

            # Number of readings displayed at a time
            accel_plot.setXRange(0, READINGS_PER_FILE * PLOT_WINDOW)
            gyro_plot.setXRange(0, READINGS_PER_FILE * PLOT_WINDOW)

        self.layout.addWidget(plot_widget)
        return plot_widget, curves

    def toggle_data_source(self):
        """
        Toggles the data source between raw and processed directories and updates the toggle button text accordingly.
        """

        if self.data_name == DATA_NAME:
            self.data_name = PROCESSED_NAME
            self.toggle_button.setText("Switch to Raw")
        else:
            self.data_name = DATA_NAME
            self.toggle_button.setText("Switch to Processed")

        self.data_directory = os.path.join(BASE_DIR, self.data_path, self.data_name)
        print(f"Data source switched to: {self.data_directory}")

    def update(self):
        """
        Periodically updates the data display, checking for new files and adjusting the UI components like sliders
        and labels based on the available data.
        """

        # Get_data_files is defined in data_processing.py and returns a sorted list of all files in that directory
        files = get_data_files(self.data_directory)
        num_files = len(files)
      
        # If the slider is currently at its max position, we will keep it there as new data is loaded. Store this for later
        slider_at_max = self.slider.value() == self.slider.maximum()

        # Calculate the new maximum of the slider
        self.slider.setMaximum(max(0, num_files - PLOT_WINDOW))
        
        # Set the slider to the max value
        if slider_at_max:
            self.slider.setValue(self.slider.maximum())

        # Caluclate the files that should be displayed
        window_start_index = self.slider.value()
        window_end_index = min(window_start_index + PLOT_WINDOW, num_files)
        displayed_files = files[window_start_index:window_end_index]

        # Read in the data from all the files and filter out none values
        all_data = [read_file(f) for f in displayed_files if os.path.getsize(f) > 0]
        all_data = [data for data in all_data if data is not None]
        
        if all_data:
            self.update_plots(all_data)
        
        #file_numbers = [os.path.splitext(os.path.basename(f))[0] for f in displayed_files]
        if num_files != 0:
            self.file_range_label.setText(f"Displaying files: {window_start_index} to {window_end_index}")
        else:
            self.file_range_label.setText("Displaying files: None")

        self.highest_file_label.setText(f"Current highest file: {os.path.basename(files[-1]) if files else 'None'}")
    
    def update_plots(self, all_data):
        """
        Updates the plots with new data.
        Args:
            all_data (list): A list of datasets from multiple files to be plotted.
        """

        for i, curve_group in enumerate(self.curves):
            sensor_index = i // 6
            measure_index = i % 6
            sensor_data = np.vstack([file_data[:, sensor_index * 6 + measure_index] for file_data in all_data if file_data is not None])
            if sensor_data.size > 0:
                flattened_data = sensor_data[-READINGS_PER_FILE:].ravel()  # Flatten the data
                curve_group.setData(flattened_data)
            else:
                curve_group.clear()  # Clear the plot if no data is available

