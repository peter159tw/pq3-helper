import PyQt5
import sys
from PyQt5.QtCore import QByteArray, QFile, QRunnable, QThreadPool, QTimer
from PyQt5.QtWidgets import QApplication, QLabel, QListView, QListWidget, QListWidgetItem, QMainWindow, QPushButton, QScrollArea
from PyQt5.QtGui import QPixmap
from PyQt5 import uic

from log.logger import Logger
from actions import actions

from flow import flow_controller
from device import device_controller


class Window(QMainWindow):
    device = device_controller.DeviceController()
    flow = flow_controller.FlowRunner()
    logger = Logger()

    label1: QLabel
    screenshot_scroll: QScrollArea
    list_logs: QListWidget
    list_state: QListWidget

    def __init__(self):
        super().__init__()

        self.flow.flow.device = self.device
        self.flow.flow.logger = self.logger

        self.device.update_screenshot.connect(self.update_screenshot)
        self.flow.flow.connect_ui(self.update_actions, self.update_state)
        self.logger.append_log.connect(self.append_log)

        uic.loadUi("ui/main.ui", self)

        self.flow_toggler.setText("Start")
        self.flow_toggler.clicked.connect(self.flow_toggler_clicked)
        self.button2.clicked.connect(self.btn2Clicked)

        self.show()

        self.flow.flow.actions.push_front([
            actions.ActionGenerateActionsUntil(
                actions.RootAction()
            )
        ])
        QThreadPool.globalInstance().start(self.flow)
        QThreadPool.globalInstance().start(self.device.minicap_client)

    def flow_toggler_clicked(self):
        if (self.flow.flow.is_enabled()):
            self.flow.flow.enable(False)
            self.flow_toggler.setText("Start")
        else:
            self.flow.flow.enable(True)
            self.flow_toggler.setText("Stop")

    def update_actions(self, actions):
        self.list_actions.clear()
        self.list_actions.addItems(actions)

    def update_state(self, s):
        self.list_state.clear()
        item = QListWidgetItem()
        item.setText(s)
        self.list_state.addItem(item)

    def append_log(self, s):
        item = QListWidgetItem()
        item.setText(s)
        self.list_logs.insertItem(0, item)

        if self.list_logs.count() > 100:
            self.list_logs.takeItem(self.list_logs.count()-1)

    def btn2Clicked(self):
        self.device.capture_screenshot()
        self.update_screenshot()

    def update_screenshot(self):
        pixmap = QPixmap()
        pixmap.load(self.device.last_captured_screenshot_path)
        pixmap = pixmap.scaledToHeight(250)
        self.label1.setPixmap(pixmap)
        self.label1.setFixedSize(pixmap.size())

def main():
    app = QApplication(sys.argv)
    window = Window()
    sys.exit(app.exec_())
