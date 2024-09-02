# Skatelligence
*An AI powered high-performance training tool for figure skaters*
## Overview
Please the [Skatelligence Website](skatelligence.ca) for the most up to date information, as well as a technical breakdown of how everything works.

Note: As it is not exactly clear what Skatelligence will turn into in the future, some things have been left out of this public repository. At this point it is mostly just some extra Data, and some work on the AI Models.
## Instructions
1. Check out the git repository
2. Run `./setup_directories`
3. Change the wifi name/password and IP adress in `microcontroller.ino` to the appropriate values
4. Connect the ESP32 to the computer and flash it with `microcontroller.ino`
5. Create Python virtual environment and install dependencies:
```
python -m venv venv
. venv/bin/activate
python -m pip install PyQt5 numpy pyqtgraph scipy torch notebook scikit-learn
```
6. From the virtual environment, start the server: `python server.py`
7. From a new terminal, in the virtual environment, launch the application: `python main.py`
8. Connect the ESP32 to power, after a brief delay, you should see the live readings from the IMUs
## Website
The skatelligence website can be found [here](https://skatelligence.ca/)

The repo for the website can be found [here](https://github.com/ayihuang/ayihuang.github.io/)
## Authors
Nathan Martin and Angela Huang
