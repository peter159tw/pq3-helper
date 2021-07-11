import time
import subprocess
from java.util.logging import Level, Logger, StreamHandler, SimpleFormatter
from java.io import ByteArrayOutputStream
from com.android.monkeyrunner import MonkeyRunner, MonkeyDevice
from SimpleXMLRPCServer import SimpleXMLRPCServer
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler

device = None


def connect_device():
    print("connecting to device")
    subprocess.call(
        "adb shell kill -9 $(adb shell ps | grep monkey | awk '{print $2}')", shell=True)
    ret = MonkeyRunner.waitForConnection()
    print("device connected")
    return ret


def is_healthy():
    if device is None:
        return False
    print("checking device healthy by calling clock.realtime...")
    v = device.getProperty("clock.realtime")
    print("got clock.realtime: " + str(v))
    return v > 0


def perform_until_healthy(f):
    global device
    while True:
        if device is not None:
            f(device)
        if is_healthy():
            break
        device = connect_device()


class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/RPC2',)


server = SimpleXMLRPCServer(("localhost", 13728),
                            requestHandler=RequestHandler,
                            allow_none=True)
server.register_introspection_functions()


def noop():
    pass


server.register_function(noop, "noop")


def touch_down_and_up(x, y):
    perform_until_healthy(lambda device: device.touch(
        x, y, MonkeyDevice.DOWN_AND_UP))


server.register_function(touch_down_and_up, "touch_down_and_up")


def drag(x1, y1, x2, y2):
    perform_until_healthy(lambda device: device.drag(
        (x1, y1), (x2, y2), 0.1))


server.register_function(drag, "drag")


def take_snapshot(path, format):
    perform_until_healthy(lambda device:
        device.takeSnapshot().writeToFile(path, format))


server.register_function(take_snapshot, "take_snapshot")

print("starting rpc server")
server.serve_forever()
