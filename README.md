# Open Whisper

Open Whisper is a minimal Python wrapper for [whispercpp](https://github.com/aarnphm/pywhispercpp) that lets you use local speech-to-text (STT) with the press of a hotkey. Record your voice and instantly transcribe it to text—no cloud, no hassle.

## Features
- Local, real-time voice-to-text transcription using Whisper models
- Hotkey-based recording and transcription
- No internet connection required
- Lightweight and easy to use

## Requirements
- Python 3.8+
- [PyWhisperCpp](https://github.com/aarnphm/pywhispercpp)
- pyaudio
- pyperclip
- AutoHotkey (Windows)

Install Python dependencies with:
```bash
pip install -r requirements.txt
```

## Usage
1. **Start the application:**
   ```
   openwhisper-hotkeys.ahk
   ```
   Double-click the AutoHotkey script to start. This will automatically launch the Python backend in the background.

2. **Hotkeys:**
   - **Windows+Alt+Space**: Hold to record, release to stop recording and transcribe
   - **Ctrl+Alt+Q**: Quit the application

## How It Works
- The AutoHotkey script automatically starts the Python Flask server in the background
- Audio is recorded from the default microphone using PyAudio
- Audio is transcribed using the selected Whisper model (default: `base.en`)
- The transcribed text is automatically copied to your clipboard for easy pasting
- Communication between AutoHotkey and Python happens via HTTP requests to localhost

## Model Selection
Change the model by editing the instantiation in `open-whisper.py`:
```python
transcriber = VoiceTranscriber("base.en")
```
Available models: `base.en`, `small.en`, `medium.en`, `large-v3`, etc.

## Customizing Hotkeys
Edit the hotkey combinations in `openwhisper-hotkeys.ahk`:
- `#!Space` = Windows+Alt+Space (record)
- `^!q` = Ctrl+Alt+Q (quit)

## License
MIT License

## Credits
- [OpenAI Whisper](https://github.com/openai/whisper)
- [pywhispercpp](https://github.com/aarnphm/pywhispercpp)
- [PyAudio](https://people.csail.mit.edu/hubert/pyaudio/)
- [AutoHotkey](https://www.autohotkey.com/)
