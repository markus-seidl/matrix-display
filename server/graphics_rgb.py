from rgbmatrix import graphics, RGBMatrix, RGBMatrixOptions
from PIL import Image
import binascii
import io
from graphics_mock import Movie, Graphics as GraphicsMock


class Graphics(GraphicsMock):
    def __init__(self, brightness: int):
        self.brightness = max(1, min(100, brightness))
        self._do_init()

    def _do_init(self):
        options = RGBMatrixOptions()
        options.rows = 32
        options.cols = 64
        options.chain_length = 2
        options.pixel_mapper_config = "U-mapper"
        options.hardware_mapping = "adafruit-hat"
        options.gpio_slowdown = 4
        options.brightness = self.brightness
        self.matrix = RGBMatrix(options=options)

    def convert_to_canvas(self, b64_images: list):
        canvass = list()
        for b64_image in b64_images:
            base64_png = str(b64_image)
            png = binascii.a2b_base64(base64_png)
            with io.BytesIO() as f:
                f.write(png)
                f.seek(0)
                pil_image = Image.open(f)

                canvas = self.matrix.CreateFrameCanvas()
                pil_image = pil_image.convert('RGB')
                canvas.SetImage(pil_image, unsafe=False)

                canvass.append(canvas)

        return canvass

    def set_brightness(self, brightness: int):
        self.brightness = brightness
        self.matrix.brightness = brightness  # doesn't work
        # causes segmentation fault self._do_init()

    def display_canvas(self, canvas):
        self.matrix.SwapOnVSync(canvas)

    def clear(self):
        self.matrix.clear()


