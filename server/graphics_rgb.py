from rgbmatrix import graphics, RGBMatrix, RGBMatrixOptions
from PIL import Image
import binascii
import io
from graphics_mock import Movie, Graphics as GraphicsMock


class Graphics(GraphicsMock):
    def __init__(self):
        options = RGBMatrixOptions()
        options.rows = 32
        options.cols = 64
        options.chain_length = 2
        options.pixel_mapper_config = "U-mapper"
        options.hardware_mapping = "adafruit-hat"
        options.gpio_slowdown = 4
        options.brightness = 1
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

    def display_canvas(self, canvas, brightness: int):
        # canvas.brightness = brightness
        self.matrix.brightness = brightness
        self.matrix.SwapOnVSync(canvas)
