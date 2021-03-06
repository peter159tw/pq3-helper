import socket
import threading
import cv2
import subprocess
import time

from PyQt5.QtCore import QRunnable, QThreadPool


def read_bytes(socket, length):
    out = socket.recv(length)
    length -= len(out)
    while length > 0:
        more = socket.recv(length)
        if len(more) == 0:
            raise ConnectionAbortedError()

        out += more
        length -= len(more)
    return bytearray(out)


class MinicapServer(QRunnable):
    def run(self) -> None:
        print("Killing old minicap server")
        subprocess.call("killall minicap", shell=True)
        #subprocess.run(["killall", "minicap"], shell=True)

        print("Starting Minicap server")
        #subprocess.run(["/usr/local/bin/adb", "shell", "LD_LIBRARY_PATH=/data/local/tmp", " /data/local/tmp/minicap", "-P", "2340x1080@2340x1080/0"], shell=True)
        subprocess.call("adb -s 0B111JEC213922 shell LD_LIBRARY_PATH=/data/local/tmp /data/local/tmp/minicap -P 2340x1080@2340x1080/0", shell=True)

        print("Minicap server died.")


class MinicapClient(QRunnable):
    # thread-safe

    __connection = None

    __server = None

    def __init__(self):
        super().__init__()
        QThreadPool.globalInstance().start(self)
        self.__last_frame = bytearray()
        self.__last_frame_cond = threading.Condition()

    def run(self):
        print("run following commands manually, and keep it alive:")
        print("adb pair 192.168.0.121:43141")
        print("adb shell killall minicap")
        print("adb shell LD_LIBRARY_PATH=/data/local/tmp /data/local/tmp/minicap -P 2340x1080@2340x1080/0")
        print("adb forward tcp:1313 localabstract:minicap")

        while True:
            try:
                self.__connect_minicap()
                for frame in self.__read_frames(self.__connection):
                    self.__set_last_frame(frame)
            except:
                print("minicap connect is broken... reconnecting")

            try:
                self.__connection.shutdown(socket.SHUT_RDWR)
                self.__connection.close()
            except:
                pass

            self.__server = None
            
    
    def __connect_minicap(self):
        if self.__server is None:
            self.__server = MinicapServer()
            QThreadPool.globalInstance().start(self.__server)
            time.sleep(5)

        self.__forward_minicap_port()
        self.__connection = socket.create_connection(('127.0.0.1', 1313))


    def __forward_minicap_port(self):
        print("kill existing forward")
        #subprocess.run(["/usr/local/bin/adb", "forward", "--remove-all"], shell=True)
        subprocess.call("adb forward --remove-all", shell=True)
        time.sleep(1)

        print("starting forward")
        #subprocess.run(["/usr/local/bin/adb", "forward", "tcp:1313", " localabstract:minicap"], shell=True)
        subprocess.call("adb -s 0B111JEC213922 forward tcp:1313 localabstract:minicap", shell=True)
        print("forward command exited (it's normal...)")
        time.sleep(1)


    def __read_frames(self, socket):
        print("connecting to minicap server")
        version = read_bytes(socket, 1)[0]
        print("Version {}".format(version))
        banner_length = read_bytes(socket, 1)[0]
        banner_rest = read_bytes(socket, banner_length - 2)
        print("Banner length {}".format(banner_length))

        while True:
            frame_bytes = list(read_bytes(socket, 4))

            total = 0
            frame_bytes.reverse()
            for byte in frame_bytes:
                total = (total << 8) + byte

            jpeg_data = read_bytes(socket, total)
            yield jpeg_data


    def __set_last_frame(self, frame):
        with self.__last_frame_cond:
            self.__last_frame[:] = frame
            self.__last_frame_cond.notify_all()

    def get_last_frame(self):
        ret: bytearray = bytearray()
        with self.__last_frame_cond:
            self.__last_frame_cond.wait()
            ret[:] = self.__last_frame
        return ret
