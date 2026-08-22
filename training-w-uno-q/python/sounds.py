"""
MP3 playback for the UNO Q's Linux/MPU side, over a USB/onboard speaker.

The four training commands are shipped as MP3s (not WAV), so playback goes
through PyAV (`av`) to decode frame-by-frame and streams the PCM out via
`arduino.app_peripherals.speaker.Speaker` — the same approach hall-w-EV's
`play_music` uses for its cruising-music track. PyAV ships prebuilt manylinux
wheels, so there's no compiler or system ffmpeg binary needed on the board;
`av` just needs to be in requirements.txt (auto-installed by the app
framework's own /run.sh on deploy).

Streaming in small chunks (rather than a single blocking play_wav-style call)
is what lets a second button press cut off whatever's currently playing —
there's only ever one "channel" here since these commands are meant to be
heard one at a time.
"""

import os
import re
import subprocess
import threading
import time

import numpy as np
from arduino.app_peripherals.speaker import Speaker

try:
    import av
except ImportError:
    av = None

STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')
COMMANDS_DIR = os.path.join(STATIC_DIR, 'commands')

# Canonical command keys, in "Play All" order.
COMMANDS = ['dinner', 'sit', 'wait', 'ok']

# Gap between tracks in a "Play All" sequence, so commands don't blur
# together into one word.
SEQUENCE_GAP_S = 0.4

# A recording set ("voice") is just a naming convention in
# static/commands/: the bare '<key>.mp3' files are the 'default' voice
# (the generated placeholders), and '<key>_<name>.mp3' files (e.g.
# 'dinner_michaelm.mp3') are the '<name>' voice. No config/manifest file —
# dropping in a new '<key>_<name>.mp3' is enough to make '<name>' show up.

def _voice_path(key, voice):
    if key not in COMMANDS:
        return None
    filename = f'{key}.mp3' if voice in (None, 'default') else f'{key}_{voice}.mp3'
    path = os.path.join(COMMANDS_DIR, filename)
    return path if os.path.exists(path) else None


def list_voices():
    """Every voice with at least one recording, 'default' first (if
    present), the rest alphabetically. A voice missing some commands still
    shows up — play_command/play_sequence report the gap when it's actually
    pressed, rather than hiding an otherwise-usable voice up front."""
    voices = set()
    has_default = False
    try:
        entries = os.listdir(COMMANDS_DIR)
    except OSError:
        entries = []
    for filename in entries:
        stem = filename[:-4] if filename.endswith('.mp3') else None
        if not stem:
            continue
        if stem in COMMANDS:
            has_default = True
            continue
        for key in COMMANDS:
            prefix = f'{key}_'
            if stem.startswith(prefix):
                voices.add(stem[len(prefix):])
                break
    ordered = (['default'] if has_default else []) + sorted(voices)
    return ordered

# ALSA simple-mixer control that gates playback — see hall-w-EV/WORK_LOG.md:
# the board's default PCM level was too low/muted to hear anything until set
# explicitly. `amixer scontrols` lists the available control names if this
# ever needs to change.
#
# pollyanna has two sound cards: card 0 is the onboard Qualcomm codec
# (`ArduinoImolaHPH`, ~1200 low-level codec controls, no plain "PCM" one),
# and the actual USB speaker enumerates separately (`USB-Audio`) with a
# simple 'PCM',0 control. Without `-c <card>`, amixer defaults to card 0 and
# fails with "Unable to find simple control 'PCM',0" — see _usb_audio_card().
MIXER_CONTROL = 'PCM,0'

_stop_event = None  # currently-playing command's stop flag, if any


def _run_playback(target_fn):
    """Thread/error-surfacing scaffolding, shared by every command press.

    `target_fn(stop_event, on_started)` does the decode+stream work; it must
    call `on_started()` once the speaker device is open (before the
    potentially-long streaming loop), so the caller gets a fast, meaningful
    (ok, error) response instead of always guessing "sure, probably fine."
    """
    global _stop_event

    stop_event = threading.Event()
    started = threading.Event()
    error_box = {}

    if _stop_event is not None:
        _stop_event.set()  # cut off whatever was already playing
    _stop_event = stop_event

    def run():
        try:
            target_fn(stop_event, started.set)
        except Exception as e:
            error_box['error'] = str(e)
            started.set()

    threading.Thread(target=run, daemon=True).start()

    started.wait(timeout=1.0)
    if 'error' in error_box:
        return False, error_box['error']
    return True, None


def _stream_file(path, stop_event, on_started=None):
    """Decode one MP3 and stream it to the speaker, chunk by chunk, checking
    stop_event throughout. Shared by a single command press and by each
    track of a "Play All" sequence."""
    container = av.open(path)
    try:
        stream = container.streams.audio[0]
        rate = stream.codec_context.sample_rate
        channels = stream.codec_context.channels
        layout = 'mono' if channels == 1 else 'stereo'
        resampler = av.AudioResampler(format='s16', layout=layout, rate=rate)

        speaker = Speaker(sample_rate=rate, channels=channels, format=np.int16)
        speaker.start()
        if on_started:
            on_started()
        try:
            for frame in container.decode(stream):
                if stop_event.is_set():
                    break
                for rframe in resampler.resample(frame):
                    speaker.play(rframe.to_ndarray().reshape(-1))
                if stop_event.is_set():
                    break
        finally:
            speaker.stop()
    finally:
        container.close()


def play_command(key, voice='default'):
    if av is None:
        return False, "'av' package not installed — check python/requirements.txt was picked up"
    if key not in COMMANDS:
        return False, f"unknown command '{key}'"

    path = _voice_path(key, voice)
    if not path:
        return False, f"no '{voice}' recording for '{key}' — drop {key}_{voice}.mp3 into python/static/commands/"

    def target(stop_event, on_started):
        _stream_file(path, stop_event, on_started)

    return _run_playback(target)


def play_sequence(voice='default', keys=None):
    """Play every command back-to-back in one voice — the "Play All" button.
    Runs as a single background job (one stop_event for the whole run, same
    as a single command) so pressing Stop mid-sequence cuts it cleanly
    instead of just skipping to the next track."""
    if av is None:
        return False, "'av' package not installed — check python/requirements.txt was picked up"

    keys = keys or COMMANDS
    missing = [k for k in keys if not _voice_path(k, voice)]
    if missing:
        return False, f"no '{voice}' recording for: {', '.join(missing)}"

    def target(stop_event, on_started):
        for i, key in enumerate(keys):
            if stop_event.is_set():
                break
            path = _voice_path(key, voice)
            _stream_file(path, stop_event, on_started if i == 0 else None)
            if not stop_event.is_set() and i < len(keys) - 1:
                time.sleep(SEQUENCE_GAP_S)

    return _run_playback(target)


def stop():
    if _stop_event is not None:
        _stop_event.set()


# ── Volume ────────────────────────────────────────────────────────────────

def _usb_audio_card():
    """ALSA card index of the USB speaker (see MIXER_CONTROL comment above).
    `/proc/asound/cards` isn't mounted inside the app's container (only the
    `/dev/snd` device nodes are), so this shells out to `aplay -l` instead —
    it enumerates cards fine straight off those device nodes. Looked up
    fresh each call: cheap, and tolerant of the speaker being plugged in
    after boot / card order changing across a reboot. Returns None if no USB
    Audio card is found (amixer then falls back to its own default card,
    which is what you get without `-c` at all)."""
    try:
        result = subprocess.run(['aplay', '-l'], capture_output=True, text=True, timeout=2)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    match = re.search(r'^card (\d+):.*USB Audio', result.stdout, re.MULTILINE)
    return int(match.group(1)) if match else None


def _amixer(*args):
    cmd = ['amixer']
    card = _usb_audio_card()
    if card is not None:
        cmd += ['-c', str(card)]
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
