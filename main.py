"""Основной модуль запуска приложения."""

import sys
from PyQt5 import QtWidgets
from restapp.ui import SleepTimer

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = SleepTimer()
    window.show()
    sys.exit(app.exec_())
