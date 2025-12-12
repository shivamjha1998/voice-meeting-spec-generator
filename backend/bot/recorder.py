import wave
import pyaudio
import threading
import queue
import subprocess
import os
import wave

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
        self.audio_queue = queue.Queue() # For real-time streaming

    def start_recording(self):
        self.is_recording = True
        self.frames = []
        # Clear queue
        with self.audio_queue.mutex:
            self.audio_queue.queue.clear()
            
        self.stream = self.p.open(format=self.format,
                                  channels=self.channels,
                                  rate=self.rate,
                                  input=True,
                                  frames_per_buffer=self.chunk_size)
        
        self.thread = threading.Thread(target=self._record_loop)
        self.thread.start()
        print(f"🎤 Microphone recording started...")

    def _record_loop(self):
        while self.is_recording:
            try:
                data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                self.frames.append(data)
                self.audio_queue.put(data) # Add to queue for streaming
            except Exception as e:
                print(f"Error recording audio: {e}")
                break

    def stream_audio(self):
        """Generator that yields audio chunks in real-time."""
        while self.is_recording or not self.audio_queue.empty():
            try:
                # Get data with a small timeout to allow checking is_recording
                chunk = self.audio_queue.get(timeout=1)
                yield chunk  # <--- FIXED TYPO HERE
            except queue.Empty:
                continue

    def stop_recording(self):
        self.is_recording = False
        if hasattr(self, 'thread'):
            self.thread.join()
        
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
            wav_path = file_path.replace(".mp3", ".wav")
            try:
                # Use ffmpeg to convert
                subprocess.run([
                    "ffmpeg", "-y", "-i", file_path, 
                    "-ar", "44100", "-ac", "1", "-f", "wav", 
                    wav_path
                ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
                output=True
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
