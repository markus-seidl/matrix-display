from flask import Flask, request
from graphics_mock import Movie
from graphics_rgb import Graphics
import threading
import time

app = Flask(__name__)

BRIGHTNESS: int = 50
GLOBAL_GRAPHICS = Graphics(BRIGHTNESS)
CURRENT_MOVIE: Movie = None
NEXT_MOVIE: Movie = None


def graphics_main():
    global CURRENT_MOVIE, NEXT_MOVIE, BRIGHTNESS
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

                GLOBAL_GRAPHICS.display_canvas(CURRENT_MOVIE.canvass[frame])
                frame = (frame + 1) % (len(CURRENT_MOVIE.canvass) - 1)

                wait_time = max(1.0 / 60.0, 1.0 / float(CURRENT_MOVIE.fps) - 0.005)  # limit to 60fps
                time.sleep(wait_time)
            except Exception as e:
                if exceptions >= 4:
                    CURRENT_MOVIE = None
                exceptions += 1
                print("Exception: ")
                print(e)
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
    NEXT_MOVIE = Movie.load_from_dict(payload)
    NEXT_MOVIE.canvass = GLOBAL_GRAPHICS.convert_to_canvas(NEXT_MOVIE.frames)

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


@app.route('/rest/v1/debug')
def get_debug():
    return 'Server Works!'


# TODO Start graphics thread

g_thread = threading.Thread(target=graphics_main, daemon=True)
g_thread.start()
