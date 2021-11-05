import json

from PIL import Image
import binascii
import base64
import io
import os

FRAMESIZE = (64, 64)


def convert_sprite_b64(filename: str):
    with open(filename, 'rb') as f:
        return base64.b64encode(f.read()).decode('ascii')  # should be safe, because of base64


def convert_directory(directory: str):
    sprite_files = os.listdir(directory)
    sprite_files.sort()

    payload = dict()
    payload['fps'] = 5

    sprites_b64 = list()
    for file in sprite_files:
        sprites_b64.append(convert_sprite_b64(directory + "/" + file))

    payload['frames'] = sprites_b64

    print(json.dumps(payload))


if __name__ == '__main__':
    convert_directory(directory="/Users/msei/Downloads/frog-ganbatte-merged/")
