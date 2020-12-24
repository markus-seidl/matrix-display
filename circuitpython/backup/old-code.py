# ON AIR sign for YouTube livestreaming
# Runs on Airlift Metro M4 with 64x32 RGB Matrix display & shield

import time
import board
import digitalio
import displayio
import adafruit_display_text.label
from adafruit_display_shapes.rect import Rect
from adafruit_display_shapes.polygon import Polygon
from adafruit_bitmap_font import bitmap_font
# from adafruit_matrixportal.network import Network
from adafruit_matrixportal.matrix import Matrix

# --- Display setup ---
matrix = Matrix()
display = matrix.display
# network = Network(status_neopixel=board.NEOPIXEL, debug=False)

# --- Button setup ---
on_air_status = False
button_up = digitalio.DigitalInOut(board.BUTTON_UP)
button_up.direction = digitalio.Direction.INPUT
button_up.pull = digitalio.Pull.UP

button_down = digitalio.DigitalInOut(board.BUTTON_DOWN)
button_down.direction = digitalio.Direction.INPUT
button_down.pull = digitalio.Pull.UP

# --- Drawing setup ---
# Create a Group
group = displayio.Group(max_size=22)
# Create a bitmap object
bitmap = displayio.Bitmap(64, 32, 4)  # width, height, bit depth
# Create a color palette
color = displayio.Palette(4)
color[0] = 0x000000  # black
color[1] = 0xFF0000  # red
color[2] = 0x444444  # dim white
color[3] = 0xFFFF00  # gold
# Create a TileGrid using the Bitmap and Palette
tile_grid = displayio.TileGrid(bitmap, pixel_shader=color)
# Add the TileGrid to the Group
group.append(tile_grid)

# draw the frame for startup
rect1 = Rect(0, 0, 2, 32, fill=color[2])
rect2 = Rect(62, 0, 2, 32, fill=color[2])
rect3 = Rect(2, 0, 10, 2, fill=color[0])
rect4 = Rect(53, 0, 10, 2, fill=color[0])
rect5 = Rect(2, 30, 10, 2, fill=color[0])
rect6 = Rect(52, 30, 12, 2, fill=color[0])

group.append(rect1)
group.append(rect2)
group.append(rect3)
group.append(rect4)
group.append(rect5)
group.append(rect6)


def redraw_frame():  # to adjust spacing at bottom later
    rect3.fill = color[2]
    rect4.fill = color[2]
    rect5.fill = color[2]
    rect6.fill = color[2]


# draw the wings w polygon shapes
wing_polys = []

wing_polys.append(Polygon([(3, 3), (9, 3), (9, 4), (4, 4)], outline=color[1]))
wing_polys.append(Polygon([(5, 6), (9, 6), (9, 7), (6, 7)], outline=color[1]))
wing_polys.append(Polygon([(7, 9), (9, 9), (9, 10), (8, 10)], outline=color[1]))
wing_polys.append(Polygon([(54, 3), (60, 3), (59, 4), (54, 4)], outline=color[1]))
wing_polys.append(Polygon([(54, 6), (58, 6), (57, 7), (54, 7)], outline=color[1]))
wing_polys.append(Polygon([(54, 9), (56, 9), (55, 10), (54, 10)], outline=color[1]))

for wing_poly in wing_polys:
    group.append(wing_poly)


def redraw_wings(index):  # to change colors
    for wing in wing_polys:
        wing.outline = color[index]


# --- Content Setup ---
deco_font = bitmap_font.load_font("/SourceCodePro-Bold-21.bdf")

# Create two lines of text. Besides changing the text, you can also
# customize the color and font (using Adafruit_CircuitPython_Bitmap_Font).

# text positions
on_x = 20
on_y = 9
off_x = 13
off_y = 8
air_x = 13
air_y = 25


text_line1 = adafruit_display_text.label.Label(
    deco_font, color=color[3], text="OFF", max_glyphs=6
)
text_line1.x = off_x
text_line1.y = off_y

text_line2 = adafruit_display_text.label.Label(
    deco_font, color=color[1], text="AIR", max_glyphs=6
)
text_line2.x = air_x
text_line2.y = air_y

# Put each line of text into the Group
group.append(text_line1)
group.append(text_line2)


def startup_text():
    text_line1.text = ""
    text_line1.x = 10
    text_line1.color = color[2]
    text_line2.text = ""
    text_line2.x = 2
    text_line2.color = color[2]
    redraw_wings(0)
    display.show(group)


startup_text()  # display the startup text


def update_text(state):
    if state:  # if switch is on, text is "ON" at startup
        text_line1.text = "ON"
        text_line1.x = on_x
        text_line1.color = color[1]
        text_line2.text = "AIR"
        text_line2.x = air_x
        text_line2.color = color[1]
        redraw_wings(1)
        redraw_frame()
        display.show(group)
    else:  # else, text if "OFF" at startup
        text_line1.text = "OFF"
        text_line1.x = off_x
        text_line1.color = color[3]
        text_line2.text = "AIR"
        text_line2.x = air_x
        text_line2.color = color[3]
        redraw_wings(3)
        redraw_frame()
        display.show(group)


def get_status():
    global on_air_status
    if not button_up.value:
        on_air_status = True
    if not button_down.value:
        on_air_status = False
    return on_air_status


# Synchronize Board's clock to Internet
mode_state = get_status()
update_text(mode_state)
last_check = None


while True:
    # if last_check is None or time.monotonic() > last_check + UPDATE_DELAY:
    # print (button_up.value, button_down.value)
    try:
        status = get_status()
        if status:
            if mode_state == 0:  # state has changed, toggle it
                update_text(1)
                mode_state = 1
        else:
            if mode_state == 1:
                update_text(0)
                mode_state = 0
        time.sleep(0.1)
        # last_check = time.monotonic()
    except RuntimeError as e:
        print("Some error occured, retrying! -", e)
