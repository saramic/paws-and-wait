import os
import threading
import time

from flask import Flask, jsonify, request, send_from_directory
from arduino.app_utils import App

import sounds

WEB_PORT   = 8080
STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')

web = Flask(__name__)


@web.route('/')
def index():
    return send_from_directory(STATIC_DIR, 'index.html')


@web.route('/health')
def health():
    return jsonify({'status': 'ok'})


@web.route('/api/commands')
def list_commands():
    return jsonify({'commands': sounds.COMMANDS})


@web.route('/api/voices')
def list_voices():
    return jsonify({'voices': sounds.list_voices()})


@web.route('/api/command/<key>', methods=['POST'])
def play_command(key):
    voice = (request.get_json(silent=True) or {}).get('voice', 'default')
    ok, error = sounds.play_command(key, voice)
    return jsonify({'ok': ok, 'error': error}), (200 if ok else 404)


@web.route('/api/play-all', methods=['POST'])
def play_all():
    voice = (request.get_json(silent=True) or {}).get('voice', 'default')
    ok, error = sounds.play_sequence(voice)
    return jsonify({'ok': ok, 'error': error}), (200 if ok else 404)


@web.route('/api/stop', methods=['POST'])
def stop():
    sounds.stop()
    return jsonify({'ok': True})


@web.route('/api/volume', methods=['GET', 'POST'])
def volume():
    if request.method == 'POST':
        percent = (request.get_json(silent=True) or {}).get('percent')
        if percent is None:
            return jsonify({'ok': False, 'error': 'percent required'}), 400
        ok, error = sounds.set_volume(percent)
        return jsonify({'ok': ok, 'error': error}), (200 if ok else 500)

    percent, error = sounds.get_volume()
    if percent is None:
        return jsonify({'ok': False, 'error': error}), 500
    return jsonify({'ok': True, 'percent': percent})


threading.Thread(
    target=lambda: web.run(host='0.0.0.0', port=WEB_PORT, debug=False,
                           use_reloader=False, threaded=True),
    daemon=True,
).start()


def loop():
    time.sleep(2)


print(f"Web UI → http://training-w-uno-q.local:{WEB_PORT}/")
App.run(user_loop=loop)
