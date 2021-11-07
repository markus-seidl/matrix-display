from PIL import Image
import binascii
import io
import json


class Movie:
    def __init__(self, fps: int, frames: list):
        self.fps = fps
        self.frames = frames

    @staticmethod
    def load_from_dict(data):
        fps = data['fps']

        images = list()
        for b64_image in data['frames']:
            base64_png = str(b64_image)
            png = binascii.a2b_base64(base64_png)

            # Keep the file descriptor open
            f = io.BytesIO()
            f.write(png)
            f.seek(0)
            pil_image = Image.open(f)

            images.append(pil_image)

        return Movie(fps, images)

    @staticmethod
    def load_from_json(data):
        return Movie.load_from_dict(json.loads(data))

    def save_to_dict(self) -> dict:
        images = list()
        for frame in self.frames:
            # base64_png = str(b64_image)
            # png = binascii.a2b_base64(base64_png)
            with io.BytesIO() as f:
                frame.save(f)

                f.seek(0)
                b64_image = binascii.b2a_base64(f)

                images.append(b64_image)

        return {
            'fps': self.fps,
            'frames': images
        }

    def save_to_json(self) -> str:
        return json.dumps(self.save_to_dict())


class Graphics:
    def __init__(self, brightness: int):
        pass

    def convert_to_canvas(self, frames: list) -> list:
        return frames

    def set_brightness(self, brightness: int):
        pass

    def display_canvas(self, canvas):
        pass

    def clear(self):
        pass
