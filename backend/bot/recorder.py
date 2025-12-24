import wave
import pyaudio
import threading
import queue
import subprocess
import os
import platform

class AudioRecorder:
    def __init__(self, filename="output.wav", chunk_size=1024, format=pyaudio.paInt16, channels=1, rate=44100):
        self.filename = filename
        self.chunk_size = chunk_size
        self.format = format
        self.channels = channels
        self.rate = rate
        self.p = pyaudio.PyAudio()
        self.is_recording = False
        self.frames = []
        self.audio_queue = queue.Queue()  # For real-time streaming
        self.device_index = None
        self.output_device_index = None
        
        # Auto-detect BlackHole on macOS
        if platform.system() == 'Darwin':  # macOS
            self._find_blackhole_device()

    def _find_blackhole_device(self):
        """Find BlackHole devices on macOS - Prefer 16ch for Output to avoid echo"""
        print("🔍 Searching for BlackHole devices...")
        info = self.p.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')
        
        # Reset indices
        self.device_index = None        # Recording (Input)
        self.output_device_index = None # Speaking (Output)

        # 1. Find Recording Device (Prefer 2ch Input)
        for i in range(num_devices):
            device_info = self.p.get_device_info_by_host_api_device_index(0, i)
            device_name = device_info.get('name')
            
            if 'BlackHole 2ch' in device_name and device_info.get('maxInputChannels') > 0:
                self.device_index = i
                print(f"✅ Found Recording Device: BlackHole 2ch Input (Index {i})")
                break
        
        if self.device_index is None:
             # Fallback to 16ch for input if 2ch missing
            for i in range(num_devices):
                device_info = self.p.get_device_info_by_host_api_device_index(0, i)
                device_name = device_info.get('name')
                if 'BlackHole 16ch' in device_name and device_info.get('maxInputChannels') > 0:
                    self.device_index = i
                    print(f"⚠️ BlackHole 2ch missing. Using BlackHole 16ch Input (Index {i}) for recording")
                    break

        # 2. Find Speaking Device (Prefer 16ch Output to split streams)
        for i in range(num_devices):
            device_info = self.p.get_device_info_by_host_api_device_index(0, i)
            device_name = device_info.get('name')
            
            if 'BlackHole 16ch' in device_name and device_info.get('maxOutputChannels') > 0:
                self.output_device_index = i
                print(f"✅ Found Speaking Device: BlackHole 16ch Output (Index {i})")
                break
        
        if self.output_device_index is None:
            # Fallback to 2ch for output (Will cause echo, but allows function)
            for i in range(num_devices):
                device_info = self.p.get_device_info_by_host_api_device_index(0, i)
                device_name = device_info.get('name')
                if 'BlackHole 2ch' in device_name and device_info.get('maxOutputChannels') > 0:
                    self.output_device_index = i
                    self.output_is_2ch = True
                    print(f"⚠️ BlackHole 16ch missing. Using BlackHole 2ch Output (Index {i}) - CAUTION: MAY CAUSE ECHO")
                    break
        else:
            self.output_is_2ch = False

        if self.device_index is None:
            print("⚠️ No BlackHole Input found.")
            self._list_audio_devices()
        
        if self.output_device_index is None:
             print("⚠️ No BlackHole Output found (Bot voice won't be heard).")

    def _list_audio_devices(self):
        """List all available audio input devices"""
        info = self.p.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')
        
        for i in range(num_devices):
            device_info = self.p.get_device_info_by_host_api_device_index(0, i)
            if device_info.get('maxInputChannels') > 0:
                print(f"   [{i}] {device_info.get('name')} - Channels: {device_info.get('maxInputChannels')}")

    def start_recording(self):
        self.is_recording = True
        self.frames = []
        # Clear queue
        with self.audio_queue.mutex:
            self.audio_queue.queue.clear()
        
        try:
            # Use BlackHole device if found, otherwise use default
            self.stream = self.p.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                input_device_index=self.device_index,  # Use BlackHole device
                frames_per_buffer=self.chunk_size
            )
            
            self.thread = threading.Thread(target=self._record_loop, daemon=True)
            self.thread.start()
            
            device_name = "default device"
            if self.device_index is not None:
                device_info = self.p.get_device_info_by_index(self.device_index)
                device_name = device_info.get('name')
            
            print(f"🎤 Recording started from: {device_name}")
            
        except Exception as e:
            print(f"❌ Failed to start recording: {e}")
            self.is_recording = False
            raise

    def _record_loop(self):
        while self.is_recording:
            try:
                data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                self.frames.append(data)
                self.audio_queue.put(data)  # Add to queue for streaming
            except Exception as e:
                print(f"Error recording audio: {e}")
                break

    def stream_audio(self):
        """Generator that yields audio chunks in real-time."""
        while self.is_recording or not self.audio_queue.empty():
            try:
                # Get data with a small timeout to allow checking is_recording
                chunk = self.audio_queue.get(timeout=1)
                yield chunk
            except queue.Empty:
                continue

    def stop_recording(self):
        self.is_recording = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=2.0)
        
        if hasattr(self, 'stream'):
            self.stream.stop_stream()
            self.stream.close()
        
        self._save_file()
        print(f"🛑 Recording stopped. Saved to {self.filename}")

    def _save_file(self):
        wf = wave.open(self.filename, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.p.get_sample_size(self.format))
        wf.setframerate(self.rate)
        wf.writeframes(b''.join(self.frames))
        wf.close()

    def play_audio(self, file_path: str):
        """
        Plays an audio file (MP3 or WAV) to the default output device.
        Uses ffmpeg to convert MP3 to WAV for PyAudio compatibility.
        """
        print(f"🔊 Playing audio: {file_path}")
        
        wav_path = file_path
        
        # 1. Convert MP3 to WAV if needed
        if file_path.endswith(".mp3"):
            # Fix for local execution: Map /app/backend to local backend
            if file_path.startswith("/app/") and not os.path.exists(file_path):
                local_path = file_path.replace("/app/", "")
                # Try relative to current working directory
                if os.path.exists(local_path):
                    print(f"🔄 Remapped path {file_path} -> {local_path}")
                    file_path = local_path
                else:
                    # Try relative to project root if running from backend/bot
                    # Assuming we are in project root mostly, but just in case
                    pass

            wav_path = file_path.replace(".mp3", ".wav")
            
            # Determine channels: BlackHole 2ch requires 2 channels.
            # BlackHole 16ch also accepts 2 channels (mapped to 1-2).
            ffmpeg_channels = "1"
            if platform.system() == 'Darwin' and self.output_device_index is not None:
                # Force stereo for any BlackHole device on Mac to avoid AUHAL errors
                ffmpeg_channels = "2"
                print(f"🍎 macOS BlackHole detected (Stereo forced): Forcing 2-channel separate audio")

            try:
                # Use ffmpeg to convert
                subprocess.run([
                    "ffmpeg", "-y", "-i", file_path, 
                    "-ar", "44100", "-ac", ffmpeg_channels, "-f", "wav", 
                    wav_path
                ], check=True, stdout=subprocess.DEVNULL)
            except Exception as e:
                print(f"❌ FFmpeg conversion failed: {e}")
                return

        # 2. Play the WAV file
        try:
            wf = wave.open(wav_path, 'rb')
            stream = self.p.open(
                format=self.p.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True,
                output_device_index=self.output_device_index
            )

            chunk_size = 1024
            data = wf.readframes(chunk_size)
            while data:
                stream.write(data)
                data = wf.readframes(chunk_size)

            stream.stop_stream()
            stream.close()
            wf.close()
            
            # Cleanup temporary wav
            if wav_path != file_path and os.path.exists(wav_path):
                os.remove(wav_path)
                
        except Exception as e:
            print(f"❌ Error playing audio: {e}")

    def __del__(self):
        """Cleanup PyAudio instance"""
        if hasattr(self, 'p'):
            self.p.terminate()