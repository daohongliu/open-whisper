# Open Whisper

Open Whisper is a cross-platform voice-to-text transcription tool that uses OpenAI Whisper models for real-time speech recognition and text injection. It features hotkey-based recording, automatic typing of transcribed text, and a simple Flask API for integration with other tools (e.g., AutoHotkey scripts).

## Features
- Real-time voice recording and transcription using Whisper models
- Automatic typing of transcribed text into the active window
- Replay last transcription
- Simple REST API for controlling recording and replay
- Cross-platform beep/notification sounds
- Designed for integration with AutoHotkey or other automation tools

## Requirements
- Python 3.8+
- [PyWhisperCpp](https://github.com/aarnphm/pywhispercpp) (for Whisper model inference)
- pyaudio
- pyautogui
- Flask
- wave
- (Windows only) winsound, ctypes

Install dependencies with:
```bash
pip install -r requirements.txt
```

## Usage
1. **Start the Flask server:**
   ```bash
   python open-whisper.py
   ```
   The server will start on `127.0.0.1:17800`.

2. **Control recording:**
   Use the provided `openwhisper-hotkeys.ahk` AutoHotkey script (or your own tool) to send HTTP POST requests to the API endpoints.

3. **Endpoints:**
   - `POST /start_recording` — Begin recording audio
   - `POST /stop_recording` — Stop recording and transcribe
   - `POST /replay` — Replay (re-type) the last transcription
   - `POST /shutdown` — Cleanly shut down the server

Example using `curl`:
```bash
curl -X POST http://127.0.0.1:17800/start_recording
curl -X POST http://127.0.0.1:17800/stop_recording
```

## How It Works
- Audio is recorded from the default microphone using PyAudio.
- Audio is transcribed using the selected Whisper model (default: `base.en`).
- The transcribed text is automatically typed into the active window using platform-specific methods (ctypes for Windows, pyautogui for others).
- The Flask API allows external scripts to control recording and replay.

## Model Selection
- The default model is `base.en`. You can change the model by editing the instantiation in `open-whisper.py`:
  ```python
  transcriber = VoiceTranscriber("base.en")
  ```
  Available models: `base.en`, `small.en`, `medium.en`, `large-v3`, etc.

## Hotkey Integration
- Use the included `openwhisper-hotkeys.ahk` script (requires [AutoHotkey](https://www.autohotkey.com/)) to control recording with keyboard shortcuts.
- The script sends HTTP requests to the Flask server to start/stop recording and replay.

## Cleanup & Shutdown
- The server handles SIGINT/SIGTERM for graceful shutdown.
- You can also POST to `/shutdown` to clean up resources and stop the server.

## Troubleshooting
- Ensure your microphone is working and accessible.
- If you see errors about missing models, install the required Whisper model or check the model name.
- On Windows, run as administrator if you have issues with text injection.

## License
MIT License

## Credits
- [OpenAI Whisper](https://github.com/openai/whisper)
- [pywhispercpp](https://github.com/aarnphm/pywhispercpp)
- [PyAudio](https://people.csail.mit.edu/hubert/pyaudio/)
- [Flask](https://flask.palletsprojects.com/)
- [AutoHotkey](https://www.autohotkey.com/) 