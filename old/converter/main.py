import binascii
import io
import json
import math

from PIL import Image


class PixelImage:
    def __init__(self, height: int, width: int, fps : int, frames: list):
        self.height = height
        self.width = width
        self.fps = fps
        self.frames = frames


def extract_rect_image(pngio: io.BytesIO, rect: ((int, int), (int, int))):
    image = Image.open(pngio)
    return image.crop(rect)


def extract_size_from_image(pngio: io.BytesIO):
    image = Image.open(pngio)
    return image.height, image.width


def resize_image(image: Image, dest_size) -> Image:
    return image.resize(dest_size, resample=Image.NEAREST)


def load_piskel(file_name) -> PixelImage:
    with open(file_name, 'r') as file:
        j = json.load(file)
        if j['modelVersion'] != 2:
            raise Exception("Unknown model version " + str(j['modelVersion']))

        piskel = j['piskel']
        height = piskel['height']
        width = piskel['width']
        fps = piskel['fps']
        layer0 = piskel['layers'][0]
        jlayer0 = json.decoder.JSONDecoder().decode(layer0)

        base64PNG = jlayer0['chunks'][0]['base64PNG']
        base64PNG = str(base64PNG).removeprefix('data:image/png;base64,')
        png = binascii.a2b_base64(base64PNG)
        with io.BytesIO() as f:
            f.write(png)
            frames = list()
            f.seek(0)
            _, image_width = extract_size_from_image(f)

            for x in range(0, image_width, width):
                f.seek(0)
                part = extract_rect_image(f, (x, 0, width + x, height))
                # part.show()
                frames.append(part)

            return PixelImage(height, width, fps, frames)


class MatrixConverter:
    def find_palette(self, image: PixelImage) -> {(int, int, int)}:
        dp = dict()
        for frame in image.frames:
            pixels = frame.load()
            for x in range(image.width):
                for y in range(image.height):
                    c = pixels[x, y]
                    if c not in dp:
                        dp[c] = 1
        return dp

    def create_numbered_palette(self, colors: {(int, int, int)}) -> ({(int, int, int): int}, [(int, int, int)]):
        l = list()
        for key in colors:
            l.append(key[0:3])

        nd = dict()
        for i in range(len(l)):
            nd[l[i]] = i

        return nd, l

    def convert_frame(self, palette: {(int, int, int): int}, frame: Image) -> [int]:
        pixels = frame.load()
        ret = list()
        for x in range(frame.width):
            for y in range(frame.height):
                c = pixels[x, y]
                ret.append(palette[c[0:3]])

        return ret

    @staticmethod
    def to_byte(i: int) -> int:
        return i.to_bytes(1, byteorder='big')

    def convert(self, image: PixelImage) -> str:
        # 2 - size of the image (w)       0
        # 1 - number of frames            2
        # 1 - number of colors            3
        # 1 - frames per second           4
        # 3 - bytes for each colour       5
        # 1... - number in the palette for every frame and pixel

        with io.BytesIO() as f:
            f.write(self.to_byte(image.width))
            f.write(self.to_byte(image.height))
            f.write(self.to_byte(len(image.frames)))

            palette = self.find_palette(image)
            numbered_dict_palette, list_palette = self.create_numbered_palette(palette)

            f.write(self.to_byte(len(list_palette)))
            f.write(self.to_byte(image.fps))

            for color in list_palette:
                for p in color:
                    f.write(self.to_byte(p))

            for frame in image.frames:
                pi = self.convert_frame(numbered_dict_palette, frame)

                for c in pi:
                    f.write(self.to_byte(c))

            f.flush()
            f.seek(0)

            return binascii.b2a_base64(f.getvalue())


if __name__ == '__main__':
    # piskel = load_piskel('example/color pattern clone-20201219-173220.piskel')
    # piskel = load_piskel('example/Megaman moving-20201220-062820.piskel')
    # piskel = load_piskel('example/snakes-20201222-165907.piskel')
    # piskel = load_piskel('example/frog-ganbatte-merged.piskel')
    # piskel = load_piskel('example/n7.piskel')

    # piskel = load_piskel('example/subnautica-1.piskel')  # https://www.reddit.com/r/PixelArt/comments/8zztr7/my_first_pixel_art_a_custom_subnautica_icon_32x32/
    # piskel = load_piskel('example/subnautica-2.piskel')  # https://www.reddit.com/r/subnautica/comments/hx0h4g/no_spoilers_i_made_a_lifepod_5_pixel_art/
    piskel = load_piskel('example/subnautica-3.piskel')  # https://www.reddit.com/r/PixelArt/comments/hdzzwt/subnautica_pixel_fish_1_peeper/

    # piskel.width = 64
    # piskel.height = 64
    r_frames = list()
    for frame in piskel.frames:
        r_frames.append(resize_image(frame, (64, 64)))
    #r_frames.append(resize_image(piskel.frames[1], (64, 64)))
    # r_frames[0].show()

    piskel.frames = r_frames

    base64_image = MatrixConverter().convert(piskel)
    print(base64_image)

    # write to file
    with open('blah.image', 'w+b') as fp:
        fp.write(binascii.a2b_base64(base64_image))

