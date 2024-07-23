import sys
from PyQt5.QtWidgets import QApplication
from graph import MainApplication
'''
Starts the application, most other functionalty should be implemented in other files
'''
if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_app = MainApplication()
    sys.exit(app.exec_())

