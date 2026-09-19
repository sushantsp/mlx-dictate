# mlx-dictate

Push-to-talk dictation for **macOS on Apple Silicon**. Press a global hotkey, speak, press it again — the transcript is copied to your clipboard. Everything runs **locally on the GPU** via [MLX Whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper). No cloud, no API keys.

## Features

- 100% local transcription (MLX + Metal, no network after the first model download)
- Global hotkey toggle — start and stop with one key
- Transcript automatically copied to the clipboard (`pbcopy`)
- **Warm model**: loads once at startup, later transcriptions are fast
- Sound cues for start / done / error
- Runs on the main thread for MLX safety, with a responsive hotkey listener

## Requirements

- macOS on Apple Silicon (M-series)
- [ffmpeg](https://formulae.brew.sh/formula/ffmpeg) — used to capture the mic
- Python 3.13+ and [uv](https://docs.astral.sh/uv/)
- A microphone

## Install

```sh
git clone https://github.com/<you>/mlx-dictate.git
cd mlx-dictate
uv sync
brew install ffmpeg
```

## Usage

```sh
uv run dictate.py
```

Wait for `ready. hotkey: <ctrl>+<alt>+<space>` (the first run downloads the model).

1. Press **Ctrl + Option + Space** → *Pop* sound, `recording...`
2. Speak
3. Press **Ctrl + Option + Space** again → *Glass* sound, transcript is copied to your clipboard

`Ctrl+C` in the terminal quits.

### Transcribe a file (no microphone)

Use `--file` to run the pipeline on an existing audio file — handy for testing or for anyone evaluating the repo without granting mic permissions:

```sh
uv run dictate.py --file samples/hello.wav
```

Tip: for a quick first test, pass `--model mlx-community/whisper-tiny-mlx` so it doesn't download ~3 GB.

## macOS permissions

Two permissions are required, granted to **the app that launches the script** (Terminal, iTerm, VS Code, …):

- **Microphone** — so `ffmpeg` can read the mic.
- **Accessibility** and/or **Input Monitoring** — so global hotkeys work.

Without them the hotkey **silently does nothing**, and you may see:

```
This process is not trusted! Input event monitoring will not be possible
until it is added to accessibility clients.
```

Grant them in **System Settings → Privacy & Security → Accessibility** and **Input Monitoring**, then **restart the terminal app** (permissions are read at launch). If you switch launchers, you must grant them again for the new one.

## Configuration

Everything lives in **`config.py`** — no need to edit `dictate.py`:

| Constant | Default | Notes |
|---|---|---|
| `MODEL` | `mlx-community/whisper-large-v3-mlx` | any `mlx-community` MLX Whisper repo |
| `DEVICE` | `:1` | ffmpeg `avfoundation` input index |
| `HOTKEY` | `<ctrl>+<alt>+<space>` | `pynput` syntax (`<alt>` = Option) |
| `LANGUAGE` | `None` | e.g. `"en"`; `None` auto-detects |
| `SOUND_START` / `SOUND_DONE` / `SOUND_ERROR` | system `.aiff` files | sound cues |

You can also override the model per-run without touching the config:

```sh
uv run dictate.py --model mlx-community/whisper-small-mlx
```

Precedence: **CLI `--model` > `config.py`**.

Find your mic device index:

```sh
ffmpeg -f avfoundation -list_devices true -i ""
```

### Models

| Repo | Size | Speed |
|---|---|---|
| `mlx-community/whisper-tiny-mlx` | ~75 MB | fastest |
| `mlx-community/whisper-base-mlx` | ~150 MB | very fast |
| `mlx-community/whisper-small-mlx` | ~480 MB | fast |
| `mlx-community/whisper-large-v3-turbo` | ~1.6 GB | fast, near-best |
| `mlx-community/whisper-large-v3-mlx` | ~3 GB | slow, best accuracy |

## Troubleshooting

- **Hotkey does nothing** → missing Accessibility / Input Monitoring permission for the launching app (see above).
- **`(nothing recognized)`** → the recording was silent; check the mic device index and that the right input is selected.
- **`There is no Stream(gpu, 1) in current thread`** → MLX work ran off the thread that loaded the model. This script avoids it by transcribing on the main thread; keep that design if you modify it.
- **First transcription slow** → the model is loading; subsequent ones are fast.

## How it works

1. Hotkey press → `ffmpeg` starts recording 16 kHz mono to a temp `.wav`.
2. Hotkey press again → `SIGINT` makes `ffmpeg` finalize the file cleanly.
3. A job is queued; the **main thread** (where the model was loaded) transcribes with `mlx_whisper`.
4. The text is piped to `pbcopy` and a done sound plays.

## License

MIT
