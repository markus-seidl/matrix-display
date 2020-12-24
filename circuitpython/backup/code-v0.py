import board
import busio
from digitalio import DigitalInOut
import neopixel
#import microcontroller

from adafruit_esp32spi import adafruit_esp32spi
import adafruit_esp32spi.adafruit_esp32spi_wifimanager as wifimanager
import adafruit_esp32spi.adafruit_esp32spi_wsgiserver as server

import displayio
import binascii
import math
import gc
import os
import storage

PANEL_SIZE = [64, 64]

# import adafruit_display_text.label
# from adafruit_display_shapes.rect import Rect
# from adafruit_display_shapes.polygon import Polygon
# from adafruit_bitmap_font import bitmap_font
# from adafruit_matrixportal.network import Network
from adafruit_matrixportal.matrix import Matrix

# --- Display setup ---
matrix = Matrix()
display = matrix.display
# network = Network(status_neopixel=board.NEOPIXEL, debug=False)

class ImageDecoder64:
    """
    Decodes a base64 image to a bitmap. The base64 has to be in the format
    bytes - description
    2 - size of the image (w)       0
    1 - number of frames            2
    1 - number of colors            3
    3 - bytes for each colour       4
    1... - number in the palette for every frame and pixel
    """
    def __init__(self, b64_image):
        self.image_bin = None
        self.update_image(b64_image)

    def update_image(self, b64_image):
        # TODO restrict the length of the image, the colors, etc.
        # also validate length
        self.image_bin = binascii.a2b_base64(b64_image)
        return True

    def no_frames(self):
        # Four characters of the b64 encoded are three bytes exactly
        return self.image_bin[2]

    def no_colors(self):
        return self.image_bin[3]

    def image_size(self):
        return self.image_bin[0], self.image_bin[1]

    def decode_palette(self):
        enc = self.image_bin
        palette_size = self.no_colors()
        palette = displayio.Palette(palette_size)
        for i in range(palette_size):
            palette[i] = ( enc[4 + i*3], enc[4 + i*3 + 1], enc[4 + i*3 + 2] )

        return palette

    def decode_frame(self, no):
        enc = self.image_bin

        palette_size = self.no_colors()
        bitmap = displayio.Bitmap(PANEL_SIZE[0], PANEL_SIZE[1], palette_size)

        width, height = self.image_size()
        print(width, height, PANEL_SIZE)
        offset = 4 + self.no_colors() * 3 + no * width * height
        for x in range(width):
            for y in range(height):
                val = self.image_bin[
                    offset + width * x + y
                ]
                bitmap[x, y] = val

        return bitmap


# https://cryptii.com/pipes/binary-to-base64
image_decoder = ImageDecoder64("")

print(os.listdir())
if 'latest.image' in os.listdir():
    print("Display latest image...")
    with open('/latest.image', 'rb') as fp:
        image_decoder.image_bin = fp.read()

    palette = image_decoder.decode_palette()
    bitmap = image_decoder.decode_frame(0)

    tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
    group = displayio.Group()
    group.append(tile_grid)
    display.show(group)
else:
    print('Blank screen...')
    # Display empty image
    palette = displayio.Palette(1)
    bitmap = displayio.Bitmap(PANEL_SIZE[0], PANEL_SIZE[1], 1)

    tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
    group = displayio.Group()
    group.append(tile_grid)
    display.show(group)

print("...done")

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

    INDEX = "/index.html"
    CHUNK_SIZE = 8912  # max number of bytes to read at once when reading files

    def __init__(self, static_dir=None, debug=False):
        self._debug = debug
        self._listeners = {}
        self._start_response = None
        self._static = static_dir
        if self._static:
            self._static_files = ["/" + file for file in os.listdir(self._static)]

    def __call__(self, environ, start_response):
        """
        Called whenever the server gets a request.
        The environ dict has details about the request per wsgi specification.
        Call start_response with the response status string and headers as a list of tuples.
        Return a single item list with the item being your response data string.
        """
        if self._debug:
            self._log_environ(environ)

        self._start_response = start_response
        status = ""
        headers = []
        resp_data = []

        key = self._get_listener_key(
            environ["REQUEST_METHOD"].lower(), environ["PATH_INFO"]
        )
        if key in self._listeners:
            status, headers, resp_data = self._listeners[key](environ)
        if environ["REQUEST_METHOD"].lower() == "get" and self._static:
            path = environ["PATH_INFO"]
            if path in self._static_files:
                status, headers, resp_data = self.serve_file(
                    path, directory=self._static
                )
            elif path == "/" and self.INDEX in self._static_files:
                status, headers, resp_data = self.serve_file(
                    self.INDEX, directory=self._static
                )

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


def led_color(environ):  # pylint: disable=unused-argument
    print("Beginning of request ", gc.mem_free())
    img_data = environ["wsgi.input"].getvalue()

    # Destroy virtual copy of img_data
    environ["wsgi.input"].close()
    environ["wsgi.input"] = None

    image_decoder.update_image(img_data)

    # Save as file
    #try:
    #    with open("/temp.image", 'w+b') as fp:
    #        fp.write(image_decoder.image_bin)
    #except (ValueError, RuntimeError, OSError) as e:
    #    print("File system may be read-only:", e)

    palette = image_decoder.decode_palette()
    bitmap = image_decoder.decode_frame(0)

    tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
    group = displayio.Group()
    group.append(tile_grid)
    display.show(group)

    print("End of request ", gc.mem_free())
    gc.collect()
    print("After collecting ", gc.mem_free())

    return ("200 OK", [], [])


# Here we create our application, setting the static directory location
# and registering the above request_handlers for specific HTTP requests
# we want to listen and respond to.
static = "/static"
try:
    static_files = os.listdir(static)
    if "index.html" not in static_files:
        raise RuntimeError(
            """
            This example depends on an index.html, but it isn't present.
            Please add it to the {0} directory""".format(
                static
            )
        )
except (OSError) as e:
    raise RuntimeError(
        """
        This example depends on a static asset directory.
        Please create one named {0} in the root of the device filesystem.""".format(
            static
        )
    ) from e

web_app = SimpleWSGIApplication(static_dir=static)
web_app.on("POST", "/ajax/ledcolor", led_color)

# Here we setup our server, passing in our web_app as the application
server.set_interface(esp)
wsgiServer = server.WSGIServer(80, application=web_app)

print("open this IP in your browser: ", esp.pretty_ip(esp.ip_address))

# Start the server
wsgiServer.start()
while True:
    # Our main loop where we have the server poll for incoming requests
    try:
        wsgiServer.update_poll()
        # Could do any other background tasks here, like reading sensors
    except (ValueError, RuntimeError, MemoryError) as e:
        print("Mem free on error ", gc.mem_free())
        print("Failed to update server, restarting hard\n", e)
        # microcontroller.reset()

