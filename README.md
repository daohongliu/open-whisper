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
## Beep Sounds

Open Whisper uses beep sounds to indicate different stages of operation:

- **Activation beep (high-pitched):** When you start recording (Windows+Alt+Space pressed)
- **Deactivation beep (medium-pitched):** When you stop recording (Windows+Alt+Space released)
- **Clipboard beep (distinct):** When the transcription is copied to your clipboard

These sounds help you know when the program is listening, processing, and ready to paste your text.
1. **Start the application:**
   ```
   openwhisper-hotkeys.ahk
   ```
   Double-click the AutoHotkey script to start. This will automatically launch the Python backend in the background.


**Note:** After recording and transcription, the output is automatically copied to your clipboard. To paste the transcribed text into any application, simply press **Ctrl+V** where you want the text to appear.

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
- [pywhispercpp](https://github.com/absadiki/pywhispercpp)
- [PyAudio](https://people.csail.mit.edu/hubert/pyaudio/)
- [AutoHotkey](https://www.autohotkey.com/)

## Auto-Start on System Startup

For convenience, you can have Open Whisper start automatically when you log in to Windows. Just add a shortcut to `openwhisper-hotkeys.ahk` in your Startup folder:

- Press `Win + R`, type `shell:startup`, and press Enter.
- Place a shortcut to `openwhisper-hotkeys.ahk` in the folder that opens.

To disable auto-start, simply remove the shortcut from the Startup folder.
