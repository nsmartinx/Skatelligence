import os
import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QSlider
from PyQt5.QtCore import QTimer, Qt
import pyqtgraph as pg
from data_processing import read_and_process_file, get_data_files, DATA_DIR, PROCESSED_DIR, PLOT_WINDOW, READINGS_PER_FILE, SENSOR_COUNT

'''
App that gets launched from main.py
'''
class MainApplication(QWidget):
    def __init__(self):
        super().__init__()
        
        # The graph can switch between raw data and processed data, self.data_directory is the file path to this. Initialize to raw data
        self.data_directory = DATA_DIR
        self.initUI()

    def initUI(self):
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

    '''
    Initializes the plots, does not actually plot anything
    '''
    def setup_plots(self):
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

    '''
    Called whenever the push button is pressed, this function switches between the raw and processed data
    '''
    def toggle_data_source(self):
        if self.data_directory == DATA_DIR:
            self.data_directory = PROCESSED_DIR
            self.toggle_button.setText("Switch to Raw")
        else:
            self.data_directory = DATA_DIR
            self.toggle_button.setText("Switch to Processed")
        print(f"Data source switched to: {self.data_directory}")

    '''
    Update functioned called every 100ms
    '''
    def update(self):
        # Get_data_files is defined in data_processing.py and returns a sorted list of all files in that directory
        files = get_data_files(self.data_directory)
        num_files = len(get_data_files(DATA_DIR))
      
        # This will only be true if it is displaying the processed directory and some files havent been processed yet
        # Calling this function will filter those unfiltered files 
        if len(files) < num_files:
            read_and_process_file(None)
         
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
        all_data = [read_and_process_file(f) for f in displayed_files if os.path.getsize(f) > 0]
        all_data = [data for data in all_data if data is not None]
        
        if all_data:
            self.update_plots(all_data)
        
        #file_numbers = [os.path.splitext(os.path.basename(f))[0] for f in displayed_files]
        if num_files != 0:
            self.file_range_label.setText(f"Displaying files: {window_start_index} to {window_end_index}")
        else:
            self.file_range_label.setText("Displaying files: None")

        self.highest_file_label.setText(f"Current highest file: {os.path.basename(files[-1]) if files else 'None'}")
    
    '''
    Function to display the data on the plots
    '''
    def update_plots(self, all_data):
        for i, curve_group in enumerate(self.curves):
            sensor_index = i // 6
            measure_index = i % 6
            sensor_data = np.vstack([file_data[:, sensor_index * 6 + measure_index] for file_data in all_data if file_data is not None])
            if sensor_data.size > 0:
                flattened_data = sensor_data[-READINGS_PER_FILE:].ravel()  # Flatten the data
                curve_group.setData(flattened_data)
            else:
                curve_group.clear()  # Clear the plot if no data is available

