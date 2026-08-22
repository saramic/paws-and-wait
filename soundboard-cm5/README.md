# soundboard-cm5

A minimal soundboard on the CM5 (quintessa): tap a button to play an MP3,
or type text to have it spoken aloud via [Piper](https://github.com/OHF-Voice/piper1-gpl)
neural TTS. Plain Flask on plain Raspberry Pi OS — no Docker, no app
framework, just systemd and rsync.

Drop MP3s into `app/sounds/` and they show up as buttons automatically —
no code change, no restart. Piper was picked over `espeak-ng` for the
speak feature: noticeably more natural voice, still fast enough for
real-time synthesis on the CM5's four Cortex-A76 cores, confirmed live.

## Layout

```
soundboard-cm5/
├── mise.toml                    # upload / install / start / stop / restart / deploy / sync-sounds / logs
├── systemd/soundboard.service   # autostarts on boot, restarts on crash
├── voices/                      # Piper voice model (fetched by `mise run install`, gitignored)
└── app/
    ├── main.py                  # Flask app
    ├── player.py                # mpg123/Piper+aplay playback, USB speaker auto-detected
    ├── requirements.txt         # flask, piper-tts
    ├── static/index.html        # soundboard UI (paws-and-wait "Detection Bowl" theme)
    └── sounds/                  # drop MP3s here
```

## First-time setup

```sh
cd soundboard-cm5
mise run install    # provisions quintessa: mpg123, python venv, flask+piper-tts, voice model
                     # prompts for quintessa's sudo password once (copies the systemd unit)
mise run start       # enables + starts the service — survives reboots from here on
```

## Everyday use

```sh
mise run deploy        # rsync + restart, after changing main.py/player.py/index.html
mise run sync-sounds   # just push new MP3s from app/sounds/ — no restart, no sudo needed
mise run logs          # tail the service log
mise run status        # is it running?
```

Then open `http://quintessa.local:8090/` on a phone or laptop.

## Adding sounds

Drop an MP3 into `app/sounds/`, e.g. `app/sounds/good_boy.mp3`, then either
`mise run sync-sounds` or just `scp`/copy it directly onto the board at
`~/soundboard-cm5/app/sounds/` — the app rescans that folder on every
`/api/sounds` request (the page polls every 5s), so it shows up with no
restart either way. The button label is the filename with underscores/
dashes turned into spaces and title-cased.

## Notes

- Playback device is auto-detected via `aplay -l` (looks for a `USB Audio`
  card) rather than hardcoded — card indices aren't stable across reboots,
  learned that the hard way getting `amixer` working for
  [training-w-uno-q](../training-w-uno-q) on pollyanna.
- `install`/`start`/`stop`/`restart` need `sudo` on quintessa (systemd unit
  install, service management) — these use `ssh -t` so the password prompt
  comes through when you run them yourself; there's no persistent
  passwordless sudo configured on the board.
- `sync-sounds` needs neither `sudo` nor a restart — safe to run anytime.
