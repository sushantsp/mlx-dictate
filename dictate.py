import argparse
import os
import queue
import signal
import subprocess
import tempfile
import threading

import mlx.core as mx
import mlx_whisper
from mlx_whisper.transcribe import ModelHolder
from pynput import keyboard

import config

_active_model = config.MODEL

_lock = threading.Lock()
_state = "idle"
_proc = None
_audio_path = None
_jobs = queue.Queue()


def play(sound):
    subprocess.Popen(
        ["afplay", sound],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def start_recording():
    global _proc, _audio_path
    fd, path = tempfile.mkstemp(suffix=".wav", prefix="dictate-")
    os.close(fd)
    _audio_path = path
    _proc = subprocess.Popen(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "avfoundation", "-i", config.DEVICE,
            "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
            path,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def stop_recording():
    _proc.send_signal(signal.SIGINT)
    _proc.wait()
    return _audio_path


def transcribe(path, model=None):
    result = mlx_whisper.transcribe(
        path,
        path_or_hf_repo=model or _active_model,
        language=config.LANGUAGE,
    )
    return result["text"].strip()


def copy_to_clipboard(text):
    subprocess.run("pbcopy", input=text, text=True)


def finish():
    global _state, _proc, _audio_path
    path = None
    try:
        path = stop_recording()
        print("... transcribing", flush=True)
        text = transcribe(path)
        if text:
            copy_to_clipboard(text)
            print(f"{text}\n[copied to clipboard]", flush=True)
            play(config.SOUND_DONE)
        else:
            print("(nothing recognized)", flush=True)
            play(config.SOUND_ERROR)
    except Exception as exc:
        print(f"error: {exc}", flush=True)
        play(config.SOUND_ERROR)
    finally:
        if path and os.path.exists(path):
            os.remove(path)
        _proc = None
        _audio_path = None
        with _lock:
            _state = "idle"


def on_toggle():
    global _state
    with _lock:
        if _state == "transcribing":
            return
        if _state == "idle":
            _state = "recording"
            starting = True
        else:
            _state = "transcribing"
            starting = False

    if starting:
        start_recording()
        play(config.SOUND_START)
        print("recording... (press hotkey again to stop)", flush=True)
    else:
        print("stopped, working...", flush=True)
        _jobs.put("finish")


def main():
    global _active_model

    parser = argparse.ArgumentParser(
        description="Local MLX Whisper dictation on Apple Silicon."
    )
    parser.add_argument("--file", help="transcribe an audio file and exit (no microphone)")
    parser.add_argument("--model", help="override the model from config.py")
    args = parser.parse_args()

    if args.model:
        _active_model = args.model

    if args.file:
        print(transcribe(args.file))
        return

    print(f"loading {_active_model} ...", flush=True)
    ModelHolder.get_model(_active_model, mx.float16)
    print(f"ready. hotkey: {config.HOTKEY}  (Ctrl+C to quit)", flush=True)

    listener = keyboard.GlobalHotKeys({config.HOTKEY: on_toggle})
    listener.start()
    try:
        while listener.is_alive():
            try:
                _jobs.get(timeout=0.25)
            except queue.Empty:
                continue
            finish()
    except KeyboardInterrupt:
        pass
    finally:
        listener.stop()
        if _proc is not None and _proc.poll() is None:
            _proc.send_signal(signal.SIGINT)
            _proc.wait()
        print("bye", flush=True)


if __name__ == "__main__":
    main()
