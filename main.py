import sys
from PyQt5.QtWidgets import QApplication
from graph import MainApplication

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_app = MainApplication()
    sys.exit(app.exec_())

