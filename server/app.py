from flask import Flask, request
from graphics_mock import Movie
from graphics_mock import Graphics
import threading
import time

app = Flask(__name__)

GLOBAL_GRAPHICS = Graphics()
CURRENT_MOVIE: Movie = None
NEXT_MOVIE: Movie = None
BRIGHTNESS: int = 255


def graphics_main():
    global CURRENT_MOVIE, NEXT_MOVIE, BRIGHTNESS
    frame = 0
    while True:
        switched_movie = False
        if CURRENT_MOVIE is None and NEXT_MOVIE is None:
            print("No movie loaded.")
            time.sleep(1)
            continue
        elif CURRENT_MOVIE is None or NEXT_MOVIE is not None:
            switched_movie = True
            CURRENT_MOVIE = NEXT_MOVIE
            NEXT_MOVIE = None

        if switched_movie:
            print(f"Displaying new Movie {len(CURRENT_MOVIE.canvass)} frames at {CURRENT_MOVIE.fps} fps")
            frame = 0

        GLOBAL_GRAPHICS.display_canvas(CURRENT_MOVIE.canvass[frame], BRIGHTNESS)
        frame = min(frame + 1, len(CURRENT_MOVIE.canvass) - 1)

        wait_time = min(1.0 / 60.0, 1.0 / float(CURRENT_MOVIE.fps) - 0.005)  # limit to 60fps
        time.sleep(wait_time)


# web_app.on("POST", "/rest/v1/image", request_set_image)
# web_app.on("POST", "/rest/v1/brightness", request_set_brightness)
# web_app.on("GET", "/rest/v1/debug/achieved_fps", request_get_achieved_fps)
# web_app.on("GET", "/rest/v1/debug/fs_writable", request_get_fs_writable)
# web_app.on("GET", "/rest/v1/debug/memory", request_get_memory)

@app.route('/rest/v1/image', methods=['POST'])
def set_image():
    global NEXT_MOVIE
    payload = request.json
    NEXT_MOVIE = GLOBAL_GRAPHICS.read_payload(payload)

    return {
        'frames': len(NEXT_MOVIE.canvass),
        'message': 'ok'
    }


@app.route('/rest/v1/brightness', methods=['POST', 'GET'])
def set_brightness():
    global BRIGHTNESS
    if request.method == 'POST':
        temp = max(0, min(255, int(request.data)))
        print(f"Set brightness to {temp}")
        BRIGHTNESS = temp

    return {
        'brightness': BRIGHTNESS
    }


@app.route('/rest/v1/debug')
def get_debug():
    return 'Server Works!'


# TODO Start graphics thread

g_thread = threading.Thread(target=graphics_main, daemon=True)
g_thread.start()
