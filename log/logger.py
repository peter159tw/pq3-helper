import os
import pathlib
import datetime
from PyQt5 import QtCore


class Logger(QtCore.QObject):
    # signal to update UI
    append_log = QtCore.pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.__folder = os.path.realpath(os.path.join(
            os.getcwd(), os.path.dirname(__file__)))
        self.__path = os.path.join(self.__folder, "log")

    def log(self, s):
        s = str(datetime.datetime.now()) + "  " + s
        self.append_log.emit(s)
        with open(self.__path, "a") as f:
            f.write(s)
            f.write("\n")