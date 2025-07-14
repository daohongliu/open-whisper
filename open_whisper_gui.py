import threading
import time
import pyaudio
import wave
import tempfile
import os
import sys
import json
import winreg
import ctypes
import platform
import re
from datetime import datetime
from pywhispercpp.model import Model
import keyboard
import pyautogui
import tkinter as tk
from tkinter import ttk, messagebox
import pystray
from PIL import Image, ImageDraw

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

class SettingsManager:
    def __init__(self):
        self.settings_file = "open_whisper_settings.json"
        self.default_settings = {
            "hotkey": "ctrl+alt+space",
            "toggle_mode": False,
            "model": "base.en",
            "auto_start": False
        }
        self.settings = self.load_settings()
    
    def load_settings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    for key, value in self.default_settings.items():
                        if key not in settings:
                            settings[key] = value
                    return settings
        except Exception as e:
            print(f"Error loading settings: {e}")
        return self.default_settings.copy()
    
    def save_settings(self):
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def get(self, key):
        return self.settings.get(key, self.default_settings.get(key))
    
    def set(self, key, value):
        self.settings[key] = value
        self.save_settings()

class TranscriptionHistory:
    def __init__(self):
        self.history_file = "transcription_history.json"
        self.history = self.load_history()
    
    def load_history(self):
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading history: {e}")
        return []
    
    def save_history(self):
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            print(f"Error saving history: {e}")
    
    def add_transcription(self, text):
        entry = {
            "text": text,
            "timestamp": datetime.now().isoformat()
        }
        self.history.insert(0, entry)
        if len(self.history) > 1000:
            self.history = self.history[:1000]
        self.save_history()
    
    def get_history(self):
        return self.history

class VoiceTranscriber:
    def __init__(self, model_name, history_manager):
        self.is_recording = False
        self.toggle_recording = False
        self.audio_data = []
        self.audio_stream = None
        self.p = None
        self.last_transcription = ""
        self.model = None
        self.recording_thread = None
        self.model_name = model_name
        self.history_manager = history_manager
        
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
            messagebox.showerror("Error", f"Failed to load Whisper model: {e}")
            sys.exit(1)
    
    def setup_audio(self):
        try:
            self.p = pyaudio.PyAudio()
            print("Audio system initialized")
        except Exception as e:
            print(f"Error initializing audio: {e}")
            messagebox.showerror("Error", f"Failed to initialize audio: {e}")
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
            play_beep(frequency=1200, duration=120)
            
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
            play_beep(frequency=800, duration=120)
            self._process_audio()
            
        except Exception as e:
            print(f"Error stopping recording: {e}")
    
    def toggle_recording_mode(self):
        if not self.toggle_recording:
            self.start_recording()
            self.toggle_recording = True
        else:
            self.stop_recording()
            self.toggle_recording = False
    
    def _process_audio(self):
        if not self.audio_data:
            print("No audio data to process")
            return
        
        try:
            # Pad with silence if duration < 1 second
            total_frames = len(self.audio_data) * self.CHUNK
            min_frames = self.RATE
            if total_frames < min_frames:
                missing_frames = min_frames - total_frames
                silence_chunk = b'\x00' * (self.CHUNK * 2)
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
                self.history_manager.add_transcription(transcription)
                self._type_text(transcription)
            else:
                print("No speech detected")
            
            os.unlink(temp_filename)
            
        except Exception as e:
            print(f"Error processing audio: {e}")
    
    def _inject_text_ctypes(self, text):
        text = text + " "
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

class HotkeyRecorder:
    def __init__(self, callback):
        self.callback = callback
        self.recording = False
        self.recorded_keys = set()
    
    def start_recording(self):
        self.recording = True
        self.recorded_keys.clear()
        keyboard.hook(self._on_key_event)
        return "Recording... Press keys and click 'Stop Recording'"
    
    def stop_recording(self):
        self.recording = False
        keyboard.unhook_all()
        
        if self.recorded_keys:
            hotkey = "+".join(sorted(self.recorded_keys))
            self.callback(hotkey)
            return f"Recorded: {hotkey}"
        else:
            return "No keys recorded"
    
    def _on_key_event(self, e):
        if not self.recording:
            return
        
        if e.event_type == keyboard.KEY_DOWN:
            key_name = e.name.lower()
            if key_name in ['left ctrl', 'right ctrl']:
                key_name = 'ctrl'
            elif key_name in ['left alt', 'right alt']:
                key_name = 'alt'
            elif key_name in ['left shift', 'right shift']:
                key_name = 'shift'
            elif key_name in ['left windows', 'right windows']:
                key_name = 'win'
            
            self.recorded_keys.add(key_name)

class OpenWhisperGUI:
    def __init__(self):
        self.settings = SettingsManager()
        self.history = TranscriptionHistory()
        self.transcriber = None
        self.hotkey_recorder = None
        self.tray_icon = None
        self.is_recording = False
        self.window_visible = True
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("Open Whisper")
        self.root.geometry("700x600")
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
        
        # Apply modern styling
        self.setup_styles()
        
        # Initialize transcriber
        model_name = self.settings.get("model")
        self.transcriber = VoiceTranscriber(model_name, self.history)
        
        self.setup_ui()
        self.setup_hotkeys()
        self.setup_tray()
    
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors for modern look
        style.configure('TFrame', background='#f0f0f0')
        style.configure('TLabel', background='#f0f0f0', foreground='#333333')
        style.configure('TLabelFrame', background='#f0f0f0', foreground='#333333')
        style.configure('TLabelFrame.Label', background='#f0f0f0', foreground='#0066cc')
        style.configure('TButton', padding=(10, 5))
        style.configure('Heading.TLabel', font=('Arial', 12, 'bold'))
    
    def setup_ui(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Open Whisper", style='Heading.TLabel')
        title_label.pack(pady=(0, 20))
        
        # Create notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill="both", expand=True)
        
        # Settings tab
        settings_frame = ttk.Frame(notebook, padding="20")
        notebook.add(settings_frame, text="Settings")
        
        # Hotkey settings
        hotkey_frame = ttk.LabelFrame(settings_frame, text="Hotkey Settings", padding="15")
        hotkey_frame.pack(fill="x", pady=(0, 15))
        
        ttk.Label(hotkey_frame, text="Recording Hotkey:").grid(row=0, column=0, sticky="w", pady=5)
        self.hotkey_var = tk.StringVar(value=self.settings.get("hotkey"))
        self.hotkey_entry = ttk.Entry(hotkey_frame, textvariable=self.hotkey_var, state="readonly", width=25, font=('Consolas', 10))
        self.hotkey_entry.grid(row=0, column=1, padx=(15, 10), pady=5)
        
        self.record_hotkey_btn = ttk.Button(hotkey_frame, text="Record New", command=self.record_hotkey)
        self.record_hotkey_btn.grid(row=0, column=2, padx=5, pady=5)
        
        # Toggle mode
        self.toggle_mode_var = tk.BooleanVar(value=self.settings.get("toggle_mode"))
        toggle_cb = ttk.Checkbutton(hotkey_frame, text="Toggle mode (click once to start/stop recording)", 
                                   variable=self.toggle_mode_var, command=self.save_settings)
        toggle_cb.grid(row=1, column=0, columnspan=3, sticky="w", pady=(10, 5))
        
        # Model settings
        model_frame = ttk.LabelFrame(settings_frame, text="Model Settings", padding="15")
        model_frame.pack(fill="x", pady=(0, 15))
        
        ttk.Label(model_frame, text="Whisper Model:").grid(row=0, column=0, sticky="w", pady=5)
        self.model_var = tk.StringVar(value=self.settings.get("model"))
        models = ["tiny.en", "base.en", "small.en", "medium.en", "large-v3"]
        model_combo = ttk.Combobox(model_frame, textvariable=self.model_var, values=models, 
                                  state="readonly", width=20)
        model_combo.grid(row=0, column=1, padx=(15, 0), pady=5)
        model_combo.bind("<<ComboboxSelected>>", self.change_model)
        
        # Startup settings
        startup_frame = ttk.LabelFrame(settings_frame, text="Startup Settings", padding="15")
        startup_frame.pack(fill="x", pady=(0, 15))
        
        self.auto_start_var = tk.BooleanVar(value=self.settings.get("auto_start"))
        auto_start_cb = ttk.Checkbutton(startup_frame, text="Start with Windows", 
                                       variable=self.auto_start_var, command=self.toggle_auto_start)
        auto_start_cb.pack(anchor="w", pady=5)
        
        # Control section
        control_frame = ttk.LabelFrame(settings_frame, text="Controls", padding="15")
        control_frame.pack(fill="x", pady=(0, 15))
        
        # Status and controls in a grid
        self.status_label = ttk.Label(control_frame, text="Ready", foreground='#0066cc')
        self.status_label.grid(row=0, column=0, sticky="w", pady=5)
        
        self.manual_record_btn = ttk.Button(control_frame, text="Manual Record", command=self.manual_record)
        self.manual_record_btn.grid(row=0, column=1, padx=(20, 0), pady=5)
        
        replay_btn = ttk.Button(control_frame, text="Replay Last", command=self.replay_last)
        replay_btn.grid(row=0, column=2, padx=(10, 0), pady=5)
        
        # History tab
        history_frame = ttk.Frame(notebook, padding="20")
        notebook.add(history_frame, text="History")
        
        # History controls
        history_controls = ttk.Frame(history_frame)
        history_controls.pack(fill="x", pady=(0, 15))
        
        ttk.Button(history_controls, text="Refresh", command=self.refresh_history).pack(side="left")
        ttk.Button(history_controls, text="Clear History", command=self.clear_history).pack(side="left", padx=(10, 0))
        
        # History list with frame
        history_list_frame = ttk.Frame(history_frame)
        history_list_frame.pack(fill="both", expand=True)
        
        self.history_tree = ttk.Treeview(history_list_frame, columns=("timestamp", "text"), show="headings", height=20)
        self.history_tree.heading("timestamp", text="Time")
        self.history_tree.heading("text", text="Transcription")
        self.history_tree.column("timestamp", width=180)
        self.history_tree.column("text", width=450)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(history_list_frame, orient="vertical", command=self.history_tree.yview)
        h_scrollbar = ttk.Scrollbar(history_list_frame, orient="horizontal", command=self.history_tree.xview)
        self.history_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack scrollbars and treeview
        self.history_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        history_list_frame.grid_rowconfigure(0, weight=1)
        history_list_frame.grid_columnconfigure(0, weight=1)
        
        # Bind double-click to replay
        self.history_tree.bind("<Double-1>", self.replay_from_history)
        
        self.refresh_history()
    
    def setup_hotkeys(self):
        self.update_hotkeys()
    
    def update_hotkeys(self):
        try:
            keyboard.unhook_all()
            hotkey = self.settings.get("hotkey")
            toggle_mode = self.settings.get("toggle_mode")
            
            if toggle_mode:
                keyboard.add_hotkey(hotkey, self.toggle_recording)
            else:
                keys = hotkey.split('+')
                main_key = keys[-1]
                modifiers = keys[:-1]
                
                def on_key_event(e):
                    if e.name == main_key:
                        modifiers_pressed = all(keyboard.is_pressed(mod) for mod in modifiers)
                        
                        if e.event_type == keyboard.KEY_DOWN and modifiers_pressed and not self.is_recording:
                            self.start_recording()
                        elif e.event_type == keyboard.KEY_UP and self.is_recording:
                            self.stop_recording()
                
                keyboard.hook(on_key_event)
            
            keyboard.add_hotkey('ctrl+alt+v', self.replay_last)
            
        except Exception as e:
            print(f"Error setting up hotkeys: {e}")
    
    def record_hotkey(self):
        if self.hotkey_recorder:
            result = self.hotkey_recorder.stop_recording()
            self.record_hotkey_btn.config(text="Record New")
            self.status_label.config(text=result)
            self.hotkey_recorder = None
        else:
            self.hotkey_recorder = HotkeyRecorder(self.on_hotkey_recorded)
            result = self.hotkey_recorder.start_recording()
            self.record_hotkey_btn.config(text="Stop Recording")
            self.status_label.config(text=result)
    
    def on_hotkey_recorded(self, hotkey):
        self.hotkey_var.set(hotkey)
        self.settings.set("hotkey", hotkey)
        self.update_hotkeys()
        self.record_hotkey_btn.config(text="Record New")
        self.status_label.config(text=f"Hotkey set to: {hotkey}")
    
    def change_model(self, event=None):
        new_model = self.model_var.get()
        self.settings.set("model", new_model)
        
        self.transcriber.cleanup()
        self.transcriber = VoiceTranscriber(new_model, self.history)
        self.status_label.config(text=f"Model changed to {new_model}")
    
    def save_settings(self):
        self.settings.set("toggle_mode", self.toggle_mode_var.get())
        self.update_hotkeys()
    
    def toggle_auto_start(self):
        auto_start = self.auto_start_var.get()
        self.settings.set("auto_start", auto_start)
        self.set_windows_startup(auto_start)
    
    def set_windows_startup(self, enable):
        if platform.system() != "Windows":
            return
        
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            app_name = "OpenWhisper"
            app_path = os.path.abspath(sys.argv[0])
            
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                if enable:
                    winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{app_path}"')
                    self.status_label.config(text="Added to Windows startup")
                else:
                    try:
                        winreg.DeleteValue(key, app_name)
                        self.status_label.config(text="Removed from Windows startup")
                    except FileNotFoundError:
                        pass
        except Exception as e:
            print(f"Error setting startup: {e}")
    
    def start_recording(self):
        self.is_recording = True
        self.transcriber.start_recording()
        self.status_label.config(text="🔴 Recording...", foreground='red')
        self.manual_record_btn.config(text="Stop Recording")
        self.update_tray_menu()
    
    def stop_recording(self):
        self.is_recording = False
        self.transcriber.stop_recording()
        self.status_label.config(text="Processing...", foreground='orange')
        self.manual_record_btn.config(text="Manual Record")
        self.root.after(3000, lambda: self.status_label.config(text="Ready", foreground='#0066cc'))
        self.update_tray_menu()
    
    def toggle_recording(self):
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()
    
    def manual_record(self):
        self.toggle_recording()
    
    def replay_last(self):
        self.transcriber.replay_last_transcription()
        self.status_label.config(text="Replayed last transcription", foreground='green')
        self.root.after(2000, lambda: self.status_label.config(text="Ready", foreground='#0066cc'))
    
    def refresh_history(self):
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        for entry in self.history.get_history():
            timestamp = datetime.fromisoformat(entry["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
            self.history_tree.insert("", "end", values=(timestamp, entry["text"]))
    
    def clear_history(self):
        if messagebox.askyesno("Clear History", "Are you sure you want to clear all transcription history?"):
            self.history.history.clear()
            self.history.save_history()
            self.refresh_history()
            self.status_label.config(text="History cleared", foreground='green')
            self.root.after(2000, lambda: self.status_label.config(text="Ready", foreground='#0066cc'))
    
    def replay_from_history(self, event):
        selection = self.history_tree.selection()
        if selection:
            item = self.history_tree.item(selection[0])
            text = item["values"][1]
            self.transcriber._type_text(text)
            self.status_label.config(text="Replayed from history", foreground='green')
            self.root.after(2000, lambda: self.status_label.config(text="Ready", foreground='#0066cc'))
    
    def create_tray_image(self):
        image = Image.new('RGB', (64, 64), color='#0066cc')
        draw = ImageDraw.Draw(image)
        draw.ellipse([8, 8, 56, 56], fill='white')
        draw.text((22, 20), "OW", fill='#0066cc', font_size=16)
        return image
    
    def update_tray_menu(self):
        if self.tray_icon:
            record_text = "Stop Recording" if self.is_recording else "Start Recording"
            menu = pystray.Menu(
                pystray.MenuItem("Open Whisper", self.show_window, default=True),
                pystray.MenuItem("Show/Hide", self.toggle_window),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(record_text, self.manual_record),
                pystray.MenuItem("Replay Last", self.replay_last),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Exit", self.quit_app)
            )
            self.tray_icon.menu = menu
    
    def setup_tray(self):
        image = self.create_tray_image()
        
        menu = pystray.Menu(
            pystray.MenuItem("Open Whisper", self.show_window, default=True),
            pystray.MenuItem("Show/Hide", self.toggle_window),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Start Recording", self.manual_record),
            pystray.MenuItem("Replay Last", self.replay_last),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self.quit_app)
        )
        
        self.tray_icon = pystray.Icon("OpenWhisper", image, "Open Whisper", menu)
        
        tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        tray_thread.start()
    
    def show_window(self, icon=None, item=None):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.window_visible = True
    
    def hide_window(self):
        self.root.withdraw()
        self.window_visible = False
    
    def toggle_window(self, icon=None, item=None):
        if self.window_visible:
            self.hide_window()
        else:
            self.show_window()
    
    def quit_app(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
        if self.transcriber:
            self.transcriber.cleanup()
        keyboard.unhook_all()
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        # Hide on startup if auto-start is enabled
        if self.settings.get("auto_start"):
            self.hide_window()
        
        self.root.mainloop()

def main():
    try:
        app = OpenWhisperGUI()
        app.run()
    except Exception as e:
        print(f"Error starting application: {e}")
        messagebox.showerror("Error", f"Failed to start Open Whisper: {e}")

if __name__ == "__main__":
    main()