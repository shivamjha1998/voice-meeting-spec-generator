import os
import io
import requests

class WhisperClient:
    def __init__(self):
        self.api_key = os.getenv("HUGGING_FACE_KEY") or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            print("⚠️ WARNING: HUGGING_FACE_KEY is not set. Transcription will fail.")
        
        # Using Whisper v3 optimized for speed on HF
        self.model_url = "https://api-inference.huggingface.co/models/openai/whisper-large-v3-turbo"
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def transcribe_stream(self, audio_bytes: bytes) -> str:
        """
        Sends audio bytes to Hugging Face Inference API for ASR.
        """
        try:
            # HF Inference API expects raw bytes for audio files
            response = requests.post(
                self.model_url, 
                headers=self.headers, 
                data=audio_bytes
            )
            
            if response.status_code != 200:
                print(f"❌ HF Whisper Error {response.status_code}: {response.text}")
                return ""

            # Response format: {"text": "transcription..."}
            result = response.json()
            return result.get("text", "")

        except Exception as e:
            print(f"❌ Whisper API Error: {e}")
            return ""
