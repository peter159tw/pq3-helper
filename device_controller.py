import subprocess
import socket
import numpy as np
import cv2

from minicap_client import MinicapClient
from PyQt5.QtCore import QByteArray, QObject
from PyQt5.QtGui import QPixmap
from PyQt5 import QtCore




class DeviceController(QObject):
  # not thread-safe

    # Signal to update UI
    update_screenshot = QtCore.pyqtSignal()

    last_captured_screenshot = None
    last_captured_screenshot_path: str = "/Users/petershih/Documents/pq3-helper/_temp_last_screenshot.png"

    minicap_client: MinicapClient = MinicapClient()

    def capture_screenshot(self):
        self.last_captured_screenshot = cv2.imdecode(np.array(self.minicap_client.get_last_frame()), cv2.IMREAD_UNCHANGED)
        cv2.imwrite(self.last_captured_screenshot_path, self.last_captured_screenshot)
        self.update_screenshot.emit()

    def tap(self, pos_x, pos_y):
        process = subprocess.Popen(
            ["/usr/local/bin/adb", "shell", "input", "tap", str(pos_x), str(pos_y)], stdout=subprocess.PIPE)
        stdout = process.communicate()[0]
