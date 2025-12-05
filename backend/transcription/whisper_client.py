import os
import time

class WhisperClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

    def transcribe_audio(self, audio_file_path: str) -> str:
        print(f"Transcribing audio file: {audio_file_path}")
        # Simulate API latency
        time.sleep(2)
        # Return mock transcript
        return "This is a mock transcript of the meeting. We discussed project requirements and timelines."

    def transcribe_stream(self, audio_chunk: bytes) -> str:
        # Real-time transcription simulation
        return " ...streamed text... "
