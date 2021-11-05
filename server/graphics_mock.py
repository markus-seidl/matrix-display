from PIL import Image
import binascii
import io


class Movie:
    def __init__(self, fps: int, canvass: list):
        self.fps = fps
        self.canvass = canvass


class Graphics:
    def __init__(self):
        pass

    def read_payload(self, payload: dict) -> Movie:
        return Movie(payload['fps'], self.convert_to_canvas(payload['frames']))

    def convert_to_canvas(self, b64_images: list):
        canvass = list()
        for b64_image in b64_images:
            base64_png = str(b64_image)
            png = binascii.a2b_base64(base64_png)
            with io.BytesIO() as f:
                f.write(png)
                f.seek(0)
                pil_image = Image.open(f)

                canvass.append(pil_image)

        return canvass

    def display_canvas(self, canvas, brightness: int):
        pass

