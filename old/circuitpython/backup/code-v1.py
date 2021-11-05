import board
import busio
from digitalio import DigitalInOut
import neopixel
# import microcontroller
from matriximagedecoder import MatrixImageDecoder

from adafruit_esp32spi import adafruit_esp32spi
import adafruit_esp32spi.adafruit_esp32spi_wifimanager as wifimanager

import displayio
import binascii
import gc
import os
import time
import matrixserver
import io
# from microcontroller import watchdog
# from watchdog import WatchDogMode
#
# watchdog.timeout = 1.0
# watchdog.mode = WatchDogMode.RESET
# watchdog.feed()

PANEL_SIZE = [128, 32]

# import adafruit_display_text.label
# from adafruit_display_shapes.rect import Rect
# from adafruit_display_shapes.polygon import Polygon
# from adafruit_bitmap_font import bitmap_font
# from adafruit_matrixportal.network import Network
from adafruit_matrixportal.matrix import Matrix

# --- Display setup ---
matrix = Matrix(width=PANEL_SIZE[0], height=PANEL_SIZE[1])
display = matrix.display

# https://cryptii.com/pipes/binary-to-base64
image_decoder = MatrixImageDecoder(display, PANEL_SIZE)
image_decoder.switch_to_file()

if 'latest.image' in os.listdir():
    image_decoder.load_image('/latest.image')
    image_decoder.update_display()

# Is file system writeable?
FS_WRITABLE = True
try:
    with open("/.deleteme", "a") as f:
        f.flush()
except OSError:
    FS_WRITABLE = False

print("File system is writable? ", FS_WRITABLE)

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# If you are using a board with pre-defined ESP32 Pins:
esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)

spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(
    spi, esp32_cs, esp32_ready, esp32_reset
)  # pylint: disable=line-too-long

"""Use below for Most Boards"""
status_light = neopixel.NeoPixel(
    board.NEOPIXEL, 1, brightness=0.2
)  # Uncomment for Most Boards
"""Uncomment below for ItsyBitsy M4"""
# import adafruit_dotstar as dotstar
# status_light = dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1, brightness=1)

## If you want to connect to wifi with secrets:
wifi = wifimanager.ESPSPI_WiFiManager(esp, secrets, status_light, debug=True)
wifi.connect()


class SimpleWSGIApplication:
    """
    An example of a simple WSGI Application that supports
    basic route handling and static asset file serving for common file types
    """

    def __init__(self):
        self._listeners = {}
        self._start_response = None

    def __call__(self, environ, start_response):
        """
        Called whenever the server gets a request.
        The environ dict has details about the request per wsgi specification.
        Call start_response with the response status string and headers as a list of tuples.
        Return a single item list with the item being your response data string.
        """
        self._start_response = start_response
        status = ""
        headers = []
        resp_data = []

        key = self._get_listener_key(
            environ["REQUEST_METHOD"].lower(), environ["PATH_INFO"]
        )
        if key in self._listeners:
            status, headers, resp_data = self._listeners[key](environ)

        self._start_response(status, headers)
        return resp_data

    def on(self, method, path, request_handler):
        """
        Register a Request Handler for a particular HTTP method and path.
        request_handler will be called whenever a matching HTTP request is received.
        request_handler should accept the following args:
            (Dict environ)
        request_handler should return a tuple in the shape of:
            (status, header_list, data_iterable)
        :param str method: the method of the HTTP request
        :param str path: the path of the HTTP request
        :param func request_handler: the function to call
        """
        self._listeners[self._get_listener_key(method, path)] = request_handler

    def serve_file(self, file_path, directory=None):
        status = "200 OK"
        headers = [("Content-Type", self._get_content_type(file_path))]

        full_path = file_path if not directory else directory + file_path

        def resp_iter():
            with open(full_path, "rb") as file:
                while True:
                    chunk = file.read(self.CHUNK_SIZE)
                    if chunk:
                        yield chunk
                    else:
                        break

        return (status, headers, resp_iter())

    def _log_environ(self, environ):  # pylint: disable=no-self-use
        print("environ map:")
        for name, value in environ.items():
            print(name, value)

    def _get_listener_key(self, method, path):  # pylint: disable=no-self-use
        return "{0}|{1}".format(method.lower(), path)

    def _get_content_type(self, file):  # pylint: disable=no-self-use
        ext = file.split(".")[-1]
        if ext in ("html", "htm"):
            return "text/html"
        if ext == "js":
            return "application/javascript"
        if ext == "css":
            return "text/css"
        if ext in ("jpg", "jpeg"):
            return "image/jpeg"
        if ext == "png":
            return "image/png"
        return "text/plain"


def request_update_image(environ):  # pylint: disable=unused-argument
    print("Beginning of request ", gc.mem_free())
    content_length = environ['content-length']
    if content_length <= 0:
        print("411 - no content length available")
        return ("411 LENGTH REQUIRED", [], [])

    length = const(4 * 100)
    if FS_WRITABLE:
        image_decoder.switch_to_file()

        with open("/temp.image", "wb") as f:
            client = environ['wsgi.input']
            for i in range(0, content_length, length):
                bin = binascii.a2b_base64(memoryview(client.recv(length)))
                f.write(bin)

        # Switch image to the new one, since we haven't crashed yet
        # TODO validate without switching to it
        os.remove("/latest.image")
        os.rename("/temp.image", "/latest.image")
        valid = image_decoder.load_image("/latest.image")
    else:
        image_decoder.switch_to_memory()

        if content_length >= 30000:  # 20kb seems to be the limit when connected to usb
            print("413 - no content length available")
            return ("413 PAYLOAD TOO LARGE", [], [])

        with io.BytesIO() as f:
            client = environ['wsgi.input']
            for i in range(0, content_length, length):
                bin = binascii.a2b_base64(memoryview(client.recv(length)))
                f.write(bin)

            valid = image_decoder.set_image(memoryview(f.getvalue()), False)

    print("End of request ", gc.mem_free())
    gc.collect()
    print("After collecting ", gc.mem_free())

    if valid:
        return ("200 OK", [], [])
    else:
        return ("400 BAD REQUEST", [], [])


def request_set_brightness(environ):
    content_length = environ['content-length']
    if content_length <= 0:
        print("411 - no content length available")
        return ("411 LENGTH REQUIRED", [], [])

    client = environ['wsgi.input']
    recv = client.recv(content_length)
    brightness = float(recv.decode())
    image_decoder.set_brightness(brightness)

    return ("200 OK", [], [])


web_app = SimpleWSGIApplication()
web_app.on("POST", "/ajax/ledcolor", request_update_image)
web_app.on("POST", "/ajax/brightness", request_set_brightness)

# Here we setup our server, passing in our web_app as the application
matrixserver.set_interface(esp)
wsgiServer = matrixserver.MatrixStreamingServer(80, application=web_app)

print("Open this IP in your browser: ", esp.pretty_ip(esp.ip_address))
print("Memory ", gc.mem_free())

# Start the server
wsgiServer.start()
while True:
    # Our main loop where we have the server poll for incoming requests
    # try:
    wsgiServer.update_poll()
    image_decoder.update_display()
    # except (ValueError, RuntimeError, MemoryError) as e:
    #    print("Mem free on error ", gc.mem_free())
    #    print("Failed to update server, restarting hard\n", e)
    # microcontroller.reset()
