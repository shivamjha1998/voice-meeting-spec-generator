import wave
import pyaudio
import threading
import time

class AudioRecorder:
    def __init__(self, filename="output.wav"):
        self.filename = filename
        self.is_recording = False
        self.frames = []
        self.p = pyaudio.PyAudio()

    def start_recording(self):
        self.is_recording = True
        self.frames = []
        self.stream = self.p.open(format=pyaudio.paInt16,
                                  channels=1,
                                  rate=44100,
                                  input=True,
                                  frames_per_buffer=1024)
        
        self.thread = threading.Thread(target=self._record)
        self.thread.start()
        print(f"Recording started: {self.filename}")

    def _record(self):
        while self.is_recording:
            data = self.stream.read(1024)
            self.frames.append(data)

    def stop_recording(self):
        self.is_recording = False
        if hasattr(self, 'thread'):
            self.thread.join()
        
        if hasattr(self, 'stream'):
            self.stream.stop_stream()
            self.stream.close()
        
        self._save_file()
        print(f"Recording stopped and saved to {self.filename}")

    def _save_file(self):
        wf = wave.open(self.filename, 'wb')
        wf.setnchannels(1)
        wf.setsampwidth(self.p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(44100)
        wf.writeframes(b''.join(self.frames))
        wf.close()
