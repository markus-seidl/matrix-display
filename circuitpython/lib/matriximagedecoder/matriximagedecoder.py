import binascii
import gc
import displayio
import time
import math


class MatrixImageDecoder:
    def __init__(self, display, panel_size):
        self._use_file = True
        self._file_decoder = MatrixImageDecoderFile(display, panel_size)
        self._memory_decoder = MatrixImageDecoderMemory(display, panel_size)

    def switch_to_file(self):
        if self._use_file:
            return

        self._memory_decoder.clear()
        self._use_file = True

    def switch_to_memory(self):
        if not self._use_file:
            return

        self._file_decoder.clear()
        self._use_file = False

    def clear(self):
        self._memory_decoder.clear()
        self._file_decoder.clear()

    def load_image(self, filename):
        if self._use_file:
            self._file_decoder.load_image(filename)
        else:
            self._memory_decoder.load_image(filename)

    def set_image(self, image, base64_decode=False):
        if self._use_file:
            return self._file_decoder.set_image(image, base64_decode)
        else:
            return self._memory_decoder.set_image(image, base64_decode)

    def len_frames(self):
        if self._use_file:
            return self._file_decoder.len_frames()
        else:
            return self._memory_decoder.len_frames()

    def no_colors(self):
        if self._use_file:
            return self._file_decoder.no_colors()
        else:
            return self._memory_decoder.no_colors()

    def playspeed(self):
        if self._use_file:
            return self._file_decoder.playspeed()
        else:
            return self._memory_decoder.playspeed()

    def image_size(self):
        if self._use_file:
            return self._file_decoder.image_size()
        else:
            return self._memory_decoder.image_size()

    def palette(self):
        if self._use_file:
            return self._file_decoder.palette()
        else:
            return self._memory_decoder.palette()

    def update_display(self):
        if self._use_file:
            self._file_decoder.update_display()
        else:
            self._memory_decoder.update_display()

    def set_brightness(self, brightness):
        self._file_decoder.set_brightness(brightness)
        self._memory_decoder.set_brightness(brightness)

    def brightness(self):
        return self._memory_decoder.brightness()


class MatrixImageDecoderCommon:
    def __init__(self):
        self._brightness = 1.0
        self._palette_adjusted = True
        self._adjusted_palette = None

    def set_brightness(self, brightness):
        self._palette_adjusted = False
        self._brightness = brightness

    def brightness(self):
        return self._brightness

    def _adjust_palette(self, palette):
        ret = []

        scale = 1  # / 255.0 * (255 - 64)
        offset = 0

        # r = 63 - last off value
        # g = 63 - last off value
        # b = 64 - last off value

        ret = displayio.Palette(len(palette))
        i = 0

        for color in palette:
            r = color[0]
            g = color[1]
            b = color[2]

            h, s, v = rgb_to_hsl(r, g, b)
            v = int(v * self.brightness())
            r, g, b = hsl_to_rgb(h, s, v)

            r = int(r * scale + offset)
            g = int(g * scale + offset)
            b = int(b * scale + offset)

            ret[i] = (r, g, b)
            i += 1

        return ret


class MatrixImageDecoderMemory(MatrixImageDecoderCommon):
    """
        # 2 - size of the image (w)       0
        # 1 - number of frames            2
        # 1 - number of colors            3
        # 1 - frames per second           4
        # 3 - bytes for each colour       5
        # 1... - number in the palette for every frame and pixel

    # Four characters of the b64 encoded are three bytes exactly
    """

    def __init__(self, display, panel_size):
        super().__init__()
        self.image_bin = None
        self._palette = None
        self._panel_size = panel_size
        self._frame_no = 0
        self._fps = 1
        self._last_update = None
        self._display = display

    def clear(self):
        self._palette = None
        self.image_bin = None
        self._frame_no = 0
        self._last_update = None
        self._fps = 1
        gc.collect()

    def load_image(self, filename):
        with open(filename, 'rb') as fp:
            self.set_image(fp.read(), False)

    def set_image(self, image, base64_decode=False):
        self.clear()

        if image:
            if base64_decode:
                self.image_bin = binascii.a2b_base64(image)
            else:
                self.image_bin = image

        self._fps = 1.0 / self.playspeed()

        # TODO restrict the length of the image, the colors, etc.
        # also validate length
        return True

    def len_frames(self):
        return self.image_bin[2]

    def no_colors(self):
        return self.image_bin[3]

    def playspeed(self):
        """Frames per second"""
        return self.image_bin[4]

    def image_size(self):
        return self.image_bin[0], self.image_bin[1]

    def palette(self):
        if self._palette:
            if not self._palette_adjusted:
                self._adjusted_palette = self._adjust_palette(self._palette)

            return self._adjusted_palette

        enc = self.image_bin
        palette_size = self.no_colors()
        palette = []
        for i in range(palette_size):
            palette.append((enc[5 + i * 3], enc[5 + i * 3 + 1], enc[5 + i * 3 + 2]))

        self._palette = palette
        self._adjusted_palette = self._adjust_palette(palette)
        return self._adjusted_palette

    def decode_frame(self, no):
        palette_size = self.no_colors()
        bitmap = displayio.Bitmap(self._panel_size[0], self._panel_size[1], palette_size)

        width, height = self.image_size()

        offset = 5 + self.no_colors() * 3 + no * width * height
        end = offset + width * height
        image = self.image_bin

        for i in range(end - offset):
            bitmap[i] = image[offset + i]

        return bitmap

    def update_display(self):
        if self.image_bin is None:
            return  # No image - no display

        current_time = time.monotonic()
        if self._last_update is None:
            self._last_update = current_time
        elif self._last_update + self._fps > current_time:
            return  # no update necessary

        self._last_update = current_time

        if self._frame_no >= self.len_frames():
            self._frame_no = 0

        palette = self.palette()
        bitmap = self.decode_frame(self._frame_no)

        tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
        group = displayio.Group()
        group.append(tile_grid)
        self._display.show(group)

        self._frame_no += 1


class MatrixImageDecoderFile(MatrixImageDecoderCommon):
    """
        # 2 - size of the image (w)       0
        # 1 - number of frames            2
        # 1 - number of colors            3
        # 1 - frames per second           4
        # 3 - bytes for each colour       5
        # 1... - number in the palette for every frame and pixel

    # Four characters of the b64 encoded are three bytes exactly
    """

    def __init__(self, display, panel_size):
        super().__init__()
        self._palette = None
        self._panel_size = panel_size
        self._frame_no = 0
        self._fps = 1
        self._last_update = None
        self._display = display
        self._f = None

        self._len_frames = None
        self._playspeed = None
        self._no_colors = None
        self._image_size = None
        self._palette = None

        self._bitmap_buffer = None
        self._group = None

        self._fps_sum = 0
        self._fps_count = 0
        # self._brightness = 1.0

    def clear(self):
        self._frame_no = 0
        self._last_update = None
        self._fps = 1
        self._palette = None
        self._bitmap_buffer = None
        if self._f:
            self._f.close()
            self._f = None
        gc.collect()

    def load_image(self, filename):
        self.clear()

        self._f = open(filename, 'rb')
        f = self._f

        width = self.to_int(f.read(1))
        height = self.to_int(f.read(1))
        self._image_size = (width, height)

        self._len_frames = self.to_int(f.read(1))
        self._no_colors = self.to_int(f.read(1))
        self._fps = self.to_int(f.read(1))

        self._fps = 1.0 / self._fps

        self.load_palette()

    def to_int(self, bytes):
        """Converts a byte array to a int using only one byte (0-255)"""
        return int(bytes[0])

    def set_image(self, image, base64_decode=False):
        self.clear()

        return False

    def len_frames(self):
        return self._len_frames

    def no_colors(self):
        return self._no_colors

    def playspeed(self):
        """Frames per second"""
        return self._fps

    def image_size(self):
        return self._image_size

    def palette(self):
        if self._palette:
            if not self._palette_adjusted:
                self._adjusted_palette = self._adjust_palette(self._palette)
            return self._adjusted_palette

        return self._palette

    def load_palette(self):
        palette_size = self.no_colors()

        palette = []

        for i in range(palette_size):
            r = self.to_int(self._f.read(1))
            g = self.to_int(self._f.read(1))
            b = self.to_int(self._f.read(1))

            palette.append((r, g, b))

        self._palette = palette
        self._adjusted_palette = self._adjust_palette(self._palette)

    def load_frame(self, no):
        palette_size = self.no_colors()
        bitmap = displayio.Bitmap(self._panel_size[0], self._panel_size[1], palette_size)

        width, height = self.image_size()
        offset = 5 + self.no_colors() * 3 + no * width * height

        self._f.seek(offset)
        read = self._f.read(width * height)
        len_read = len(read)

        bitmap.fill_from(read)

        # for i in range(len_read):
        #    bitmap[i] = read[i]

        return bitmap

    def update_frame(self, no):
        palette_size = self.no_colors()
        if self._bitmap_buffer is None:
            self._bitmap_buffer = displayio.Bitmap(self._panel_size[0], self._panel_size[1], palette_size)
        bitbuf = self._bitmap_buffer

        width, height = self.image_size()

        offset = 5 + palette_size * 3 + no * width * height
        self._f.seek(offset)
        read = self._f.read(width * height)

        for i in range(len(read)):
            bitbuf[i] = read[i]

        return bitbuf

    def update_display(self):
        if self._f is None:
            return  # No image - no display

        current_time = time.monotonic()
        if self._last_update is None:
            self._last_update = current_time
        elif self._last_update + self._fps > current_time:
            return  # no update necessary

        self._last_update = current_time

        if self._frame_no >= self.len_frames():
            self._frame_no = 0

        palette = self.palette()
        bitmap = self.load_frame(self._frame_no)

        tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
        tile_grid.flip_y = True
        tile_grid.transpose_xy = False
        group = displayio.Group()
        group.append(tile_grid)
        self._group = group

        # print("Took ", time.monotonic() - current_time, "s to decode and construct next frame")
        self._fps_sum += time.monotonic() - current_time
        self._fps_count += 1

        if self._fps_count > 10:
            d = self._fps_sum / float(self._fps_count)
            #print("Took ", d, "s to decode and construct next frame")

            self._fps_sum = 0.0
            self._fps_count = 0

        self._display.show(group)

        self._frame_no += 1


def rgb_to_hsv(r, g, b):
    r = float(r)
    g = float(g)
    b = float(b)
    high = max(r, g, b)
    low = min(r, g, b)
    h, s, v = high, high, high

    d = high - low
    s = 0 if high == 0 else d / high

    if high == low:
        h = 0.0
    else:
        h = {
            r: (g - b) / d + (6 if g < b else 0),
            g: (b - r) / d + 2,
            b: (r - g) / d + 4,
        }[high]
        h /= 6

    return h, s, v


def hsv_to_rgb(h, s, v):
    i = math.floor(h * 6)
    f = h * 6 - i
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)

    r, g, b = [
        (v, t, p),
        (q, v, p),
        (p, v, t),
        (p, q, v),
        (t, p, v),
        (v, p, q),
    ][int(i % 6)]

    return r, g, b


def rgb_to_hsl(r, g, b):
    r = float(r)
    g = float(g)
    b = float(b)
    high = max(r, g, b)
    low = min(r, g, b)
    h, s, v = ((high + low) / 2,) * 3
    l = (high + low) / 2

    if high == low:
        h = 0.0
        s = 0.0
    else:
        d = high - low
        s = d / (2 - high - low) if l > 0.5 else d / (high + low)
        h = {
            r: (g - b) / d + (6 if g < b else 0),
            g: (b - r) / d + 2,
            b: (r - g) / d + 4,
        }[high]
        h /= 6

    return h, s, v


# def hsl_to_rgb(h, s, l):
#     def hue_to_rgb(p, q, t):
#         t += 1 if t < 0 else 0
#         t -= 1 if t > 1 else 0
#         if t < 1 / 6: return p + (q - p) * 6 * t
#         if t < 1 / 2: return q
#         if t < 2 / 3: p + (q - p) * (2 / 3 - t) * 6
#         return p
#
#     if s == 0:
#         r, g, b = l, l, l
#     else:
#         q = l * (1 + s) if l < 0.5 else l + s - l * s
#         p = 2 * l - q
#         r = hue_to_rgb(p, q, h + 1 / 3)
#         g = hue_to_rgb(p, q, h)
#         b = hue_to_rgb(p, q, h - 1 / 3)
#
#     return r, g, b


def hsv_to_hsl(h, s, v):
    l = 0.5 * v * (2 - s)
    s = v * s / (1 - math.fabs(2 * l - 1))
    return h, s, l


def hsl_to_hsv(h, s, l):
    v = (2 * l + s * (1 - math.fabs(2 * l - 1))) / 2
    s = 2 * (v - l) / v
    return h, s, v


def clamp(value, min_value, max_value):
    return max(min_value, min(max_value, value))


def saturate(value):
    return clamp(value, 0.0, 1.0)


def hue_to_rgb(h):
    r = abs(h * 6.0 - 3.0) - 1.0
    g = 2.0 - abs(h * 6.0 - 2.0)
    b = 2.0 - abs(h * 6.0 - 4.0)
    return saturate(r), saturate(g), saturate(b)


def hsl_to_rgb(h, s, l):
    r, g, b = hue_to_rgb(h)
    c = (1.0 - abs(2.0 * l - 1.0)) * s
    r = (r - 0.5) * c + l
    g = (g - 0.5) * c + l
    b = (b - 0.5) * c + l
    return int(r), int(g), int(b)
