import subprocess
import socket
import numpy as np
import cv2

from device.minicap_client import MinicapClient
from device.monkey_runner_adaptor import MonkeyRunnerAdaptor
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
    monkey_runner: MonkeyRunnerAdaptor = MonkeyRunnerAdaptor()

    def capture_screenshot2(self):
        self.monkey_runner.take_snapshot(self.last_captured_screenshot_path, "png")
        try:
            self.last_captured_screenshot = cv2.imread(self.last_captured_screenshot_path)
        except:
            self.last_captured_screenshot = None
            return
        self.update_screenshot.emit()

    def capture_screenshot(self):
        try:
            self.last_captured_screenshot = cv2.imdecode(
                np.array(self.minicap_client.get_last_frame()), cv2.IMREAD_UNCHANGED)
        except:
            self.last_captured_screenshot = None
            return
            
        cv2.imwrite(self.last_captured_screenshot_path,
                    self.last_captured_screenshot)
        self.update_screenshot.emit()
        

    def tap(self, x, y):
        #subprocess.call("adb -s 0B111JEC213922 shell input tap {} {}".format(str(x), str(y)), shell=True)
        self.monkey_runner.touch(x, y)

    def drag(self, x1, y1, x2, y2):
        self.monkey_runner.drag(x1,y1,x2,y2)
