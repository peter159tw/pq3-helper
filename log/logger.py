from PyQt5 import QtCore


class Logger(QtCore.QObject):
    # signal to update UI
    append_log = QtCore.pyqtSignal(object)

    def log(self, s):
        self.append_log.emit(s)