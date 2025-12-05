import os
import io
from openai import OpenAI

class WhisperClient:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("⚠️ WARNING: OPENAI_API_KEY is not set. Transcription will fail.")
        self.client = OpenAI(api_key=api_key)

    def transcribe_stream(self, audio_bytes: bytes) -> str:
        """
        Sends audio bytes to OpenAI Whisper API.
        """
        try:
            # OpenAI API expects a file-like object with a name
            # We wrap the raw bytes in BytesIO
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = "chunk.wav" 

            # Call Whisper API
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file,
                language="en" # Forcing English improves accuracy for now
            )
            return transcript.text
        except Exception as e:
            print(f"❌ Whisper API Error: {e}")
            return ""
