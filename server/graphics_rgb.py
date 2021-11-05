from rgbmatrix import graphics, RGBMatrix, RGBMatrixOptions
from PIL import Image
import binascii
import io
from graphics_mock import Movie, Graphics as GraphicsMock


class Graphics(GraphicsMock):
    def __init__(self):
        options = RGBMatrixOptions()
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
                canvas.SetImage(pil_image)

                canvass.append(canvas)

        return canvass

    def display_canvas(self, canvas, brightness: int):
        canvas.brightness = brightness
        self.matrix.SwapOnVSync(canvas)
