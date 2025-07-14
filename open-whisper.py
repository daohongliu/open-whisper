import threading
import time
import pyaudio
import wave
import tempfile
import os
import sys
from pywhispercpp.model import Model
import keyboard
import pyautogui
import tkinter as tk
from tkinter import ttk, messagebox
import ctypes
import platform
import re

# Simple beep function (cross-platform)
def play_beep(frequency=1000, duration=150):
    if platform.system() == 'Windows':
        import winsound
        winsound.Beep(frequency, duration)
    else:
        # Try to play a beep on other platforms
        try:
            sys.stdout.write('\a')
            sys.stdout.flush()
        except Exception:
            pass

class ModelSelector:
    def __init__(self, models):
        self.selected_model = None
        self.models = models

    def show(self):
        self.root = tk.Tk()
        self.root.title("Select Whisper Model")
        self.root.geometry("300x120")
        self.root.resizable(False, False)

        tk.Label(self.root, text="Choose Whisper model:").pack(pady=(15, 5))
        self.model_var = tk.StringVar(value=self.models[0])
        self.dropdown = ttk.Combobox(self.root, textvariable=self.model_var, values=self.models, state="readonly")
        self.dropdown.pack(pady=5)

        start_btn = tk.Button(self.root, text="Start", command=self._on_start)
        start_btn.pack(pady=(5, 15))

        self.root.mainloop()
        return self.selected_model

    def _on_start(self):
        self.selected_model = self.model_var.get()
        self.root.destroy()

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
        if self.is_recording:
            return
        
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
            
            # Start recording in a separate thread
            self.recording_thread = threading.Thread(target=self._record_audio)
            self.recording_thread.start()
            
        except Exception as e:
            print(f"Error starting recording: {e}")
            self.is_recording = False
    
    def _record_audio(self):
        while self.is_recording:
            try:
                data = self.audio_stream.read(self.CHUNK)
                self.audio_data.append(data)
            except Exception as e:
                print(f"Error during recording: {e}")
                break
    
    def stop_recording(self):
        if not self.is_recording:
            return
        
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
            
        except Exception as e:
            print(f"Error stopping recording: {e}")
    
    def _process_audio(self):
        if not self.audio_data:
            print("No audio data to process")
            return
        try:
            # Pad with silence if duration < 1 second
            total_frames = len(self.audio_data) * self.CHUNK
            min_frames = self.RATE  # 1 second of audio
            if total_frames < min_frames:
                missing_frames = min_frames - total_frames
                silence_chunk = b'\x00' * (self.CHUNK * 2)  # 2 bytes per sample for paInt16
                num_silence_chunks = (missing_frames + self.CHUNK - 1) // self.CHUNK
                for _ in range(num_silence_chunks):
                    self.audio_data.append(silence_chunk)
                print(f"Padded audio with {num_silence_chunks} chunks of silence.")
            # Save audio to temporary WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_filename = temp_file.name
                with wave.open(temp_filename, 'wb') as wf:
                    wf.setnchannels(self.CHANNELS)
                    wf.setsampwidth(self.p.get_sample_size(self.FORMAT))
                    wf.setframerate(self.RATE)
                    wf.writeframes(b''.join(self.audio_data))
            # Transcribe audio
            print("Transcribing...")
            segments = self.model.transcribe(temp_filename)
            # Extract text from segments
            transcription = ""
            for segment in segments:
                transcription += segment.text + " "
            transcription = transcription.strip()
            # Ignore all-caps, underscore, square-bracketed output
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
            # Clean up temporary file
            os.unlink(temp_filename)
        except Exception as e:
            print(f"Error processing audio: {e}")
    
    def _inject_text_ctypes(self, text):
        if platform.system() != 'Windows':
            # Fallback for non-Windows
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

def main():
    print("Open Whisper starting...")
    print("Running in background. Hotkeys:")
    print("  Ctrl+Alt+Space: Hold to record, release to transcribe and type")
    print("  Ctrl+Alt+V: Replay last transcription")
    print("  Ctrl+C: Exit")

    # Model selection UI
    available_models = ["base.en", "small.en", "medium.en", "large-v3"]
    selector = ModelSelector(available_models)
    model_name = selector.show()
    if not model_name:
        print("No model selected. Exiting.")
        return

    transcriber = VoiceTranscriber(model_name)
    
    try:
        # Set up hotkey handlers
        recording_key_pressed = False
        
        def on_record_key_press():
            nonlocal recording_key_pressed
            if not recording_key_pressed:
                recording_key_pressed = True
                transcriber.start_recording()
        
        def on_record_key_release():
            nonlocal recording_key_pressed
            if recording_key_pressed:
                recording_key_pressed = False
                transcriber.stop_recording()
        
        def on_replay_key():
            transcriber.replay_last_transcription()
        
        # Register hotkeys using key event handlers instead
        def on_key_event(e):
            if e.event_type == keyboard.KEY_DOWN and e.name == 'space' and keyboard.is_pressed('ctrl') and keyboard.is_pressed('alt'):
                if not recording_key_pressed:
                    on_record_key_press()
            elif e.event_type == keyboard.KEY_UP and e.name == 'space':
                if recording_key_pressed:
                    on_record_key_release()
        
        keyboard.hook(on_key_event)
        keyboard.add_hotkey('ctrl+alt+v', on_replay_key, suppress=True)
        
        print("Ready! Running in background. Use Ctrl+Alt+Space to record.")
        
        # Keep the program running
        keyboard.wait('ctrl+c')
        
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error in main loop: {e}")
    finally:
        transcriber.cleanup()

if __name__ == "__main__":
    main()