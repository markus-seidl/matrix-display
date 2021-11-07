import math

from flask import Flask, request
from graphics_mock import Movie
from graphics_rgb import Graphics
import threading
import time
import traceback
from timeit import default_timer as timer
import os

app = Flask(__name__)

BRIGHTNESS: int = 20
GLOBAL_GRAPHICS = Graphics(BRIGHTNESS)
CURRENT_MOVIE: Movie = None
NEXT_MOVIE: Movie = None

EXECUTION_TIME_START = 0
EXECUTION_TIME_COUNT = 0
ACHIEVED_FPS = -1


def swap_to_default_movie():
    if not os.path.exists('default.movie'):
        print("No default movie exists.")
        return

    with open('default.movie', 'r') as f:
        temp = Movie.load_from_json(f.read())
        temp.canvass = GLOBAL_GRAPHICS.convert_to_canvas(temp.frames)
        NEXT_MOVIE = temp


def clear_frame_timing():
    global EXECUTION_TIME_COUNT, EXECUTION_TIME_START
    EXECUTION_TIME_START = 0
    EXECUTION_TIME_COUNT = 0


def graphics_main():
    global CURRENT_MOVIE, NEXT_MOVIE, BRIGHTNESS, EXECUTION_TIME_COUNT, EXECUTION_TIME_START, ACHIEVED_FPS
    frame = 0
    exceptions = 0
    try:
        while True:
            try:
                switched_movie = False
                if CURRENT_MOVIE is None and NEXT_MOVIE is None:
                    time.sleep(0.5)
                    continue
                elif CURRENT_MOVIE is None or NEXT_MOVIE is not None:
                    switched_movie = True
                    CURRENT_MOVIE = NEXT_MOVIE
                    NEXT_MOVIE = None

                if switched_movie:
                    print(f"Displaying new Movie {len(CURRENT_MOVIE.canvass)} frames at {CURRENT_MOVIE.fps} fps")
                    frame = 0
                    clear_frame_timing()
                    ACHIEVED_FPS = -1
                    EXECUTION_TIME_START = timer()

                GLOBAL_GRAPHICS.display_canvas(CURRENT_MOVIE.canvass[frame])
                if len(CURRENT_MOVIE.canvass) > 1:
                    frame = (frame + 1) % (len(CURRENT_MOVIE.canvass) - 1)
                    wait_time = max(1.0 / 60.0, 1.0 / float(CURRENT_MOVIE.fps) - 0.005)  # limit to 60fps
                else:
                    frame = 0
                    wait_time = 1.0 / 60.0
                end = timer()
                EXECUTION_TIME_COUNT += 1

                if end - EXECUTION_TIME_START >= 1:  # Have we measuring one second at least?
                    if EXECUTION_TIME_COUNT > 1:  # Have we measured one frame at least?
                        ACHIEVED_FPS = (end - EXECUTION_TIME_START) / EXECUTION_TIME_COUNT
                    else:
                        ACHIEVED_FPS = 0.0000001  # "eps"

                time.sleep(wait_time)
            except Exception as e:
                if exceptions >= 4:
                    CURRENT_MOVIE = None
                    GLOBAL_GRAPHICS.clear()
                exceptions += 1
                print("Exception: ")
                print(traceback.format_exc())
    finally:
        GLOBAL_GRAPHICS.clear()
        print("Finally")


# web_app.on("POST", "/rest/v1/image", request_set_image)
# web_app.on("POST", "/rest/v1/brightness", request_set_brightness)
# web_app.on("GET", "/rest/v1/debug/achieved_fps", request_get_achieved_fps)
# web_app.on("GET", "/rest/v1/debug/fs_writable", request_get_fs_writable)
# web_app.on("GET", "/rest/v1/debug/memory", request_get_memory)

@app.route('/rest/v1/image', methods=['POST'])
def set_image():
    global NEXT_MOVIE
    payload = request.json
    temp = Movie.load_from_dict(payload)
    temp.canvass = GLOBAL_GRAPHICS.convert_to_canvas(temp.frames)
    NEXT_MOVIE = temp

    return {
        'frames': len(NEXT_MOVIE.canvass),
        'message': 'ok'
    }


@app.route('/rest/v1/brightness', methods=['POST', 'GET'])
def set_brightness():
    global BRIGHTNESS, CURRENT_MOVIE, NEXT_MOVIE
    if request.method == 'POST':
        temp = max(0, min(100, int(request.data)))
        print(f"Set brightness to {temp}")
        BRIGHTNESS = temp
        GLOBAL_GRAPHICS.set_brightness(BRIGHTNESS)

        # Re-convert current movie
        if CURRENT_MOVIE:
            new_canvass = GLOBAL_GRAPHICS.convert_to_canvas(CURRENT_MOVIE.frames)
            CURRENT_MOVIE.canvass = new_canvass

    return {
        'brightness': BRIGHTNESS
    }


@app.route('/rest/v1/fps', methods=['POST', 'GET'])
def set_get_fps():
    global CURRENT_MOVIE
    if request.method == 'POST':
        temp = max(0, min(60, int(request.data)))
        print(f"Set fps to {temp}")
        if CURRENT_MOVIE:
            CURRENT_MOVIE.fps = temp

    fps = -1
    if CURRENT_MOVIE:
        fps = CURRENT_MOVIE.fps

    return {
        'fps': fps
    }


@app.route('/rest/v1/clear')
def do_clear():
    global CURRENT_MOVIE, GLOBAL_GRAPHICS
    CURRENT_MOVIE = None
    GLOBAL_GRAPHICS.clear()
    return {}


@app.route('/rest/v1/debug')
def get_debug():
    global ACHIEVED_FPS
    fps = -1
    if ACHIEVED_FPS > 0 or ACHIEVED_FPS < 0:
        fps = 1 / ACHIEVED_FPS

    return {
        'fps': 1 / ACHIEVED_FPS
    }


@app.route('/rest/v1/default_movie', methods=['POST'])
def store_default_movie():
    # Sanity check data - do try to load it first
    payload = request.json
    temp = Movie.load_from_dict(payload)

    with open('default.movie', 'w+') as f:
        f.write(temp.save_to_json())


@app.route('/rest/v1/default_movie', methods=['POST'])
def load_default_movie():
    swap_to_default_movie()


# TODO Start graphics thread

g_thread = threading.Thread(target=graphics_main, daemon=True)
g_thread.start()
