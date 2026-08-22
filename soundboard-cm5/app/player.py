"""
Playback for the CM5 soundboard: arbitrary MP3s dropped into sounds/, plus
text-to-speech via Piper — a modern neural TTS, much less robotic than
espeak-ng, and still fast enough for real-time CPU synthesis on the CM5's
four Cortex-A76 cores (confirmed live: a short phrase plays back with no
noticeable delay). espeak-ng was the obvious default but Piper is a
genuinely nicer voice for roughly the same setup effort, so that's what's
wired up here.

Unlike the UNO Q app framework's Speaker API (see ../training-w-uno-q),
this is a plain Raspberry Pi OS box with full apt/pip access — so playback
just shells out to real command-line tools (mpg123, aplay) rather than
needing a custom audio-streaming class.
"""

import os
import re
import subprocess
import threading

APP_DIR = os.path.dirname(os.path.abspath(__file__))
SOUNDS_DIR = os.path.join(APP_DIR, 'sounds')
VOICES_DIR = os.path.join(os.path.dirname(APP_DIR), 'voices')

PIPER_BIN = os.path.join(APP_DIR, 'venv', 'bin', 'piper')
PIPER_MODEL = os.path.join(VOICES_DIR, 'en_US-lessac-medium.onnx')
PIPER_SAMPLE_RATE = 22050  # from en_US-lessac-medium.onnx.json's audio.sample_rate

# ALSA simple-mixer control on the USB speaker — same 'PCM',0 control name
# confirmed working on pollyanna's identical UACDemoV1.0 USB audio chip
# (see ../training-w-uno-q/python/sounds.py). `amixer scontrols -c <card>`
# lists the available names if this ever needs to change for a different
# speaker.
MIXER_CONTROL = 'PCM,0'

_lock = threading.Lock()
_current_procs = []  # whatever's currently playing — terminated on the next press


def _usb_audio_card():
    """ALSA card index of the USB speaker, auto-detected via `aplay -l`
    rather than hardcoded — card index isn't stable across reboots/device
    reordering (see ../training-w-uno-q/python/sounds.py's identical
    _usb_audio_card() — hardcoding this bit us once already on pollyanna,
    not doing that again here). Returns None if no USB Audio card is found."""
    try:
        result = subprocess.run(['aplay', '-l'], capture_output=True, text=True, timeout=2)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    match = re.search(r'^card (\d+):.*USB Audio', result.stdout, re.MULTILINE)
    return match.group(1) if match else None


def _usb_audio_device():
    """ALSA device string (for mpg123 -a / aplay -D) built from the same
    card lookup as _usb_audio_card()."""
    card = _usb_audio_card()
    return f'plughw:{card},0' if card is not None else 'default'


def list_sounds():
    """Scan sounds/ fresh on every call — dropping a new MP3 in just shows
    up on the next page load/poll, no server restart needed."""
    if not os.path.isdir(SOUNDS_DIR):
        return []
    return sorted(f[:-4] for f in os.listdir(SOUNDS_DIR) if f.lower().endswith('.mp3'))


def _label(name):
    return name.replace('_', ' ').replace('-', ' ').title()


def sounds_payload():
    return [{'name': n, 'label': _label(n)} for n in list_sounds()]


def stop():
    with _lock:
        for p in _current_procs:
            p.terminate()
        _current_procs.clear()


def play_sound(name):
    if name not in list_sounds():
        return False, f"unknown sound '{name}'"
    path = os.path.join(SOUNDS_DIR, f'{name}.mp3')

    stop()
    device = _usb_audio_device()
    with _lock:
        proc = subprocess.Popen(
            ['mpg123', '-q', '-a', device, path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        _current_procs.append(proc)
    return True, None


def speak(text):
    text = text.strip()[:300]
    if not text:
        return False, 'no text given'
    if not os.path.exists(PIPER_MODEL):
        return False, f"voice model missing: {PIPER_MODEL} — run `mise run install`"

    stop()
    device = _usb_audio_device()
    with _lock:
        piper_proc = subprocess.Popen(
            [PIPER_BIN, '-m', PIPER_MODEL, '--output-raw'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        aplay_proc = subprocess.Popen(
            ['aplay', '-D', device, '-r', str(PIPER_SAMPLE_RATE), '-f', 'S16_LE', '-t', 'raw', '-c', '1'],
            stdin=piper_proc.stdout, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        piper_proc.stdout.close()  # so aplay_proc sees EOF/SIGPIPE, not us holding it open
        _current_procs.extend([piper_proc, aplay_proc])

    piper_proc.stdin.write(text.encode('utf-8'))
    piper_proc.stdin.close()
    return True, None


# ── Volume ────────────────────────────────────────────────────────────────

def _amixer(*args):
    cmd = ['amixer']
    card = _usb_audio_card()
    if card is not None:
        cmd += ['-c', card]
    cmd += list(args)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=2)


def get_volume():
    try:
        result = _amixer('sget', MIXER_CONTROL)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return None, str(e)
    if result.returncode != 0:
        return None, result.stderr.strip() or 'amixer sget failed'

    match = re.search(r'\[(\d+)%\]', result.stdout)
    if not match:
        return None, "couldn't parse amixer output"
    return int(match.group(1)), None


def set_volume(percent):
    try:
        percent = max(0, min(100, int(percent)))
    except (TypeError, ValueError):
        return False, 'percent must be a number'

    try:
        result = _amixer('sset', MIXER_CONTROL, f'{percent}%')
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return False, str(e)
    if result.returncode != 0:
        return False, result.stderr.strip() or 'amixer sset failed'
    return True, None
