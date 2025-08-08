import threading
import time
import pyaudio
import wave
import tempfile
import os
import sys
from pywhispercpp.model import Model
import pyautogui
import ctypes
import platform
import re
from flask import Flask, request, jsonify
import signal

# Simple beep function (cross-platform)
def play_beep(frequency=1000, duration=150):
    if platform.system() == 'Windows':
        import winsound
        winsound.Beep(frequency, duration)
    else:
        try:
            sys.stdout.write('\a')
            sys.stdout.flush()
        except Exception:
            pass

# Removed ModelSelector class (GUI)

class VoiceTranscriber:
    def __init__(self, model_name):
        self.is_recording = False
        self.audio_data = []
        self.audio_stream = None
        self.p = None
        self.last_transcription = ""
        self.model = None
        self.recording_thread = None
        self.model_name = model_name
        self.lock = threading.Lock()
        # Audio settings
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        self.CHUNK = 1024
        self.setup_whisper()
        self.setup_audio()
    
    def setup_whisper(self):
        try:
            self.model = Model(self.model_name)
            print(f"Whisper model '{self.model_name}' loaded successfully")
        except Exception as e:
            print(f"Error loading Whisper model: {e}")
            print("Available models: base.en, small.en, medium.en, large-v3, etc.")
            sys.exit(1)
    
    def setup_audio(self):
        try:
            self.p = pyaudio.PyAudio()
            print("Audio system initialized")
        except Exception as e:
            print(f"Error initializing audio: {e}")
            sys.exit(1)
    
    def start_recording(self):
        with self.lock:
            if self.is_recording:
                return False
            try:
                self.is_recording = True
                self.audio_data = []
                self.audio_stream = self.p.open(
                    format=self.FORMAT,
                    channels=self.CHANNELS,
                    rate=self.RATE,
                    input=True,
                    frames_per_buffer=self.CHUNK
                )
                print("Recording started...")
                play_beep(frequency=1200, duration=120)  # Activation beep
                self.recording_thread = threading.Thread(target=self._record_audio)
                self.recording_thread.start()
                return True
            except Exception as e:
                print(f"Error starting recording: {e}")
                self.is_recording = False
                return False
    
    def _record_audio(self):
        while self.is_recording:
            try:
                data = self.audio_stream.read(self.CHUNK)
                self.audio_data.append(data)
            except Exception as e:
                print(f"Error during recording: {e}")
                break
    
    def stop_recording(self):
        with self.lock:
            if not self.is_recording:
                return False
            self.is_recording = False
            try:
                if self.recording_thread:
                    self.recording_thread.join()
                if self.audio_stream:
                    self.audio_stream.stop_stream()
                    self.audio_stream.close()
                print("Recording stopped. Processing...")
                play_beep(frequency=800, duration=120)  # Deactivation beep
                self._process_audio()
                return True
            except Exception as e:
                print(f"Error stopping recording: {e}")
                return False
    
    def _process_audio(self):
        if not self.audio_data:
            print("No audio data to process")
            return
        try:
            total_frames = len(self.audio_data) * self.CHUNK
            min_frames = self.RATE  # 1 second of audio
            if total_frames < min_frames:
                missing_frames = min_frames - total_frames
                silence_chunk = b'\x00' * (self.CHUNK * 2)  # 2 bytes per sample for paInt16
                num_silence_chunks = (missing_frames + self.CHUNK - 1) // self.CHUNK
                for _ in range(num_silence_chunks):
                    self.audio_data.append(silence_chunk)
                print(f"Padded audio with {num_silence_chunks} chunks of silence.")
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_filename = temp_file.name
                with wave.open(temp_filename, 'wb') as wf:
                    wf.setnchannels(self.CHANNELS)
                    wf.setsampwidth(self.p.get_sample_size(self.FORMAT))
                    wf.setframerate(self.RATE)
                    wf.writeframes(b''.join(self.audio_data))
            print("Transcribing...")
            segments = self.model.transcribe(temp_filename)
            transcription = ""
            for segment in segments:
                transcription += segment.text + " "
            transcription = transcription.strip()
            if re.fullmatch(r"\[[A-Z0-9_ ]+\]", transcription):
                print(f"Ignored non-speech transcription: {transcription}")
                os.unlink(temp_filename)
                return
            if transcription:
                self.last_transcription = transcription
                print(f"Transcription: {transcription}")
                self._type_text(transcription)
            else:
                print("No speech detected")
            os.unlink(temp_filename)
        except Exception as e:
            print(f"Error processing audio: {e}")
    
    def _inject_text_ctypes(self, text):
        text = text + " "  # Always append a space
        if platform.system() != 'Windows':
            pyautogui.typewrite(text)
            return
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        WM_CHAR = 0x0102
        for char in text:
            user32.PostMessageW(hwnd, WM_CHAR, ord(char), 0)
        print(f"Injected (ctypes): {text}")

    def _type_text(self, text):
        try:
            time.sleep(0.1)
            self._inject_text_ctypes(text)
        except Exception as e:
            print(f"Error typing text: {e}")
    
    def replay_last_transcription(self):
        if self.last_transcription:
            print(f"Replaying: {self.last_transcription}")
            self._type_text(self.last_transcription)
        else:
            print("No previous transcription to replay")
    
    def cleanup(self):
        if self.is_recording:
            self.stop_recording()
        if self.p:
            self.p.terminate()
        print("Cleanup completed")

# Flask app for IPC
app = Flask(__name__)
transcriber = VoiceTranscriber("base.en")

@app.route("/start_recording", methods=["POST", "GET"])
def start_recording():
    if request.method == "GET":
        # This is just for connection testing
        return jsonify({"status": "server_running"})
    success = transcriber.start_recording()
    return jsonify({"success": success})

@app.route("/stop_recording", methods=["POST"])
def stop_recording():
    success = transcriber.stop_recording()
    return jsonify({"success": success})

@app.route("/replay", methods=["POST"])
def replay():
    transcriber.replay_last_transcription()
    return jsonify({"success": True})

@app.route("/shutdown", methods=["POST"])
def shutdown():
    print("Shutdown requested via /shutdown endpoint.")
    transcriber.cleanup()
    return jsonify({"success": True})

if __name__ == "__main__":
    def handle_exit(signum, frame):
        print("Signal received, cleaning up...")
        transcriber.cleanup()
        os._exit(0)

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    try:
        print("Open Whisper Flask server starting...")
        print("Endpoints:")
        print("  POST /start_recording")
        print("  POST /stop_recording")
        print("  POST /replay")
        print("  POST /shutdown")
        print("Use the AutoHotkey script to control recording.")
        app.run(host="127.0.0.1", port=17800, debug=False, use_reloader=False)
    finally:
        transcriber.cleanup()
        os._exit(0)