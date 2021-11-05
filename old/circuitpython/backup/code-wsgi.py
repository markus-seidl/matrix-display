import board
import busio
from digitalio import DigitalInOut
import neopixel

from adafruit_esp32spi import adafruit_esp32spi
import adafruit_esp32spi.adafruit_esp32spi_wifimanager as wifimanager
import adafruit_esp32spi.adafruit_esp32spi_wsgiserver as server
from adafruit_wsgi.wsgi_app import WSGIApp

import displayio
import adafruit_binascii as binascii
import math
import gc

PANEL_SIZE = [64, 32]

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
        return (self.image_bin[0], self.image_bin[1])

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
        offset = 4 + self.no_colors() * 3 + no * width * height
        for x in range(width):
            for y in range(height):
                val = self.image_bin[
                    offset + width * x + y
                ]
                bitmap[x, y] = val

        return bitmap

print("Constructing image")

# https://cryptii.com/pipes/binary-to-base64
image_decoder = ImageDecoder64("")

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

## If you want to create a WIFI hotspot to connect to with secrets:
# secrets = {"ssid": "My ESP32 AP!", "password": "supersecret"}
# wifi = wifimanager.ESPSPI_WiFiManager(esp, secrets, status_light)
# wifi.create_ap()

## To you want to create an un-protected WIFI hotspot to connect to with secrets:"
# secrets = {"ssid": "My ESP32 AP!"}
# wifi = wifimanager.ESPSPI_WiFiManager(esp, secrets, status_light)
# wifi.create_ap()

# Here we create our application, registering the
# following functions to be called on specific HTTP GET requests routes

web_app = WSGIApp()

@web_app.route("/display/64/")
def request_display_b64(request):  # pylint: disable=unused-argument
    print("Called display b64")
    # Convert request body to string
    request.body.seek(0)
    img_data = request.body.getvalue()
    print(img_data)

    #image_decoder.update_image(img_data)

    #palette = image_decoder.decode_palette()
    #bitmap = image_decoder.decode_frame(0)

    #tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
    #group = displayio.Group()
    #group.append(tile_grid)
    #display.show(group)

    return ("200 OK", [], "")


@web_app.route("/led_off")
def led_off(request):  # pylint: disable=unused-argument
    print("led off!")
    status_light.fill(0)
    return ("200 OK", [], "")


# Here we setup our server, passing in our web_app as the application
server.set_interface(esp)
wsgiServer = server.WSGIServer(80, application=web_app)

print("open this IP in your browser: ", esp.pretty_ip(esp.ip_address))

# print(esp.get_time())
# Start the server
wsgiServer.start()
while True:
    # Our main loop where we have the server poll for incoming requests
    try:
        wsgiServer.update_poll()
        # Could do any other background tasks here, like reading sensors
    except (ValueError, RuntimeError) as e:
        print("Failed to update server, restarting ESP32\n", e)
        wifi.reset()


