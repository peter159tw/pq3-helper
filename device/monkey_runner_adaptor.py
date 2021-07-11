import xmlrpc.client

import subprocess
import time
from PyQt5.QtCore import QRunnable, QThreadPool
from PyQt5.sip import delete

class MonkeyRunnerTargetRunner(QRunnable):
    def run(self) -> None:
        print("starting monkey runner")
        subprocess.call("kill $(lsof -ti tcp:13728)", shell=True)
        subprocess.call("/Users/petershih/Library/Android/sdk/tools/bin/monkeyrunner /Users/petershih/Documents/pq3-helper/device/monkey_runner_target.py", shell=True)
        print("monkey runner died")

class MonkeyRunnerAdaptor:
    __server = MonkeyRunnerTargetRunner()
    __client = None


    def __init__(self):
        QThreadPool.globalInstance().start(self.__server)

    def __invoke(self, f):
        while True:
            try:
                self.__client = xmlrpc.client.ServerProxy("http://localhost:13728")
                f()
            except Exception as e:
                print("failed to connect monkeyrunner target: " + str(e))
                time.sleep(0.1)
                continue
            break

    def touch(self, x, y):
        self.__invoke(lambda: self.__client.touch_down_and_up(int(x), int(y)))

    def drag(self, x1, y1, x2, y2):
        self.__invoke(lambda: self.__client.drag(int(x1),int(y1),int(x2),int(y2)))

    def take_snapshot(self, path, format):
        self.__invoke(lambda: self.__client.take_snapshot(path, format))

if __name__ == "__main__":
    o = MonkeyRunnerAdaptor()
    while True:
        print("taking snapshot")
        o.take_snapshot("/Users/petershih/Documents/pq3-helper/_temp_last_screenshot_2.png", "png")
    