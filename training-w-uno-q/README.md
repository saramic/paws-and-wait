# training-w-uno-q

A minimal Arduino UNO Q app: a soundboard for the four dog-training
commands — **Dinner**, **Sit**, **Wait**, **OK** — played as MP3s over the
board's speaker, controlled from a phone-friendly web page styled to match
the [paws-and-wait blog](https://saramic.github.io/paws-and-wait/).

Linux-side only — no microcontroller `sketch/` needed (per the
[Arduino App specification](https://github.com/arduino/arduino-app-cli/blob/main/docs/app-specification.md),
a sketch is optional), no bricks/sidecars either. MP3 decoding uses
[PyAV](https://pyav.org/) streamed through the framework's own
`arduino.app_peripherals.speaker.Speaker` API — the same approach validated
in the sibling [hall-w-EV](../../hall-w-EV) project's `play_music`.

## Layout

```
training-w-uno-q/
├── app.yaml               # App descriptor (name, icon, ports — no sketch, no bricks)
├── mise.toml               # install / gen-placeholder-audio / upload / start / stop / deploy tasks
└── python/
    ├── main.py              # Flask app + entry point
    ├── sounds.py            # MP3 decode-and-stream over Speaker
    ├── requirements.txt     # flask, numpy, av
    └── static/
        ├── index.html       # Soundboard UI (paws-and-wait "Detection Bowl" theme)
        └── commands/        # dinner.mp3, sit.mp3, wait.mp3, ok.mp3
```

## Setup

```sh
cd training-w-uno-q
mise run install                 # checks the ssh alias "pollyanna" is reachable — no build toolchain needed
mise run gen-placeholder-audio    # macOS `say` + ffmpeg → spoken-word placeholder MP3s (swap for real recordings any time)
```

Drop real recordings into `python/static/commands/` (same four filenames:
`dinner.mp3`, `sit.mp3`, `wait.mp3`, `ok.mp3`) whenever you have them —
they replace the placeholders with no code changes.

## Deploy & test

```sh
mise run deploy    # rsync app.yaml + python/ to pollyanna, then (re)start the app
```

Then open `http://pollyanna.local:8080/` (or the board's IP) on a phone or
laptop and tap a command button. Volume is exposed as a slider — the
board's PCM mixer defaults low/muted on first boot, per hall-w-EV's
WORK_LOG.md.

Other tasks: `mise run upload`, `mise run start`, `mise run stop`,
`mise run syslog:pollyanna`, `mise run set-start-on-reboot:pollyanna` /
`unset-start-on-reboot:pollyanna`.

## Local sanity check (no board needed)

`python/sounds.py`'s decode-and-stream logic and every Flask route were
smoke-tested locally against the generated placeholder MP3s with a stubbed
`arduino` package (the board-only `app_utils`/`app_peripherals` modules
aren't installable off-board). Real hardware — actual audio out of the
speaker, `amixer` mixer control — still needs a run on pollyanna.
