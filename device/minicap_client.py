import socket
import threading
import cv2
import subprocess

from PyQt5.QtCore import QRunnable


def read_bytes(socket, length):
    out = socket.recv(length)
    length -= len(out)
    while length > 0:
        more = socket.recv(length)
        out += more
        length -= len(more)
    return bytearray(out)


def read_frames(socket):
    version = read_bytes(socket, 1)[0]
    #print("Version {}".format(version))
    banner_length = read_bytes(socket, 1)[0]
    banner_rest = read_bytes(socket, banner_length - 2)
    #print("Banner length {}".format(banner_length))

    while True:
        frame_bytes = list(read_bytes(socket, 4))

        total = 0
        frame_bytes.reverse()
        for byte in frame_bytes:
            total = (total << 8) + byte

        jpeg_data = read_bytes(socket, total)
        yield jpeg_data


class MinicapClient(QRunnable):
    # thread-safe

    __connection = None

    __last_frame = bytearray()
    __last_frame_lock = threading.Lock()

    def run(self):
        try:
            self.__connection = socket.create_connection(('127.0.0.1', 1313))
        except ConnectionRefusedError:
            self.__start_minicap()
            raise
        

        for frame in read_frames(self.__connection):
            self.__set_last_frame(frame)

        self.__connection.shutdown(socket.SHUT_RDWR)
        self.__connection.close()

    def __start_minicap(self):
        print("run following commands manually, and keep it alive:")
        print("adb pair 192.168.0.121:43141")
        print("adb shell LD_LIBRARY_PATH=/data/local/tmp /data/local/tmp/minicap -P 2340x1080@2340x1080/0")
        print("adb forward tcp:1313 localabstract:minicap")

    def __set_last_frame(self, frame):
        with self.__last_frame_lock:
            self.__last_frame[:] = frame

    def get_last_frame(self):
        ret: bytearray = bytearray()
        with self.__last_frame_lock:
            ret[:] = self.__last_frame
        return ret
