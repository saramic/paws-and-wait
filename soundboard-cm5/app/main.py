import os

from flask import Flask, jsonify, request, send_from_directory

import player

STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')
WEB_PORT = 8090

app = Flask(__name__)


@app.route('/')
def index():
    return send_from_directory(STATIC_DIR, 'index.html')


@app.route('/health')
def health():
    return jsonify({'status': 'ok'})


@app.route('/api/sounds')
def sounds():
    return jsonify({'sounds': player.sounds_payload()})


@app.route('/api/play/<name>', methods=['POST'])
def play(name):
    ok, error = player.play_sound(name)
    return jsonify({'ok': ok, 'error': error}), (200 if ok else 404)


@app.route('/api/speak', methods=['POST'])
def speak():
    text = (request.get_json(silent=True) or {}).get('text', '')
    ok, error = player.speak(text)
    return jsonify({'ok': ok, 'error': error}), (200 if ok else 400)


@app.route('/api/stop', methods=['POST'])
def stop():
    player.stop()
    return jsonify({'ok': True})


@app.route('/api/volume', methods=['GET', 'POST'])
def volume():
    if request.method == 'POST':
        percent = (request.get_json(silent=True) or {}).get('percent')
        if percent is None:
            return jsonify({'ok': False, 'error': 'percent required'}), 400
        ok, error = player.set_volume(percent)
        return jsonify({'ok': ok, 'error': error}), (200 if ok else 500)

    percent, error = player.get_volume()
    if percent is None:
        return jsonify({'ok': False, 'error': error}), 500
    return jsonify({'ok': True, 'percent': percent})


if __name__ == '__main__':
    print(f"Soundboard → http://quintessa.local:{WEB_PORT}/")
    app.run(host='0.0.0.0', port=WEB_PORT, debug=False, threaded=True)
