import whisper
import os
import torch
import numpy as np
import tempfile
import wave

class WhisperLocalResult:
    """Standardizes the output to match what main.py expects"""
    def __init__(self, text):
        self.text = text
        # Local Whisper base model doesn't support diarization out of the box.
        # We leave words/speakers empty so main.py falls back to "Unknown" speaker.
        self.words = [] 

class WhisperLocalClient:
    def __init__(self, model_size="base"):
        print(f"📥 Loading Whisper model ('{model_size}')...")
        
        # 1. Detect Hardware
        device = "cpu"
        if torch.cuda.is_available():
            device = "cuda"
        elif torch.backends.mps.is_available():
            device = "mps"
            
        print(f"   Attempting to run on: {device.upper()}")
        
        # 2. Load Model with Safe Fallback
        try:
            self.model = whisper.load_model(model_size, device=device)
            print(f"✅ Whisper model loaded on {device.upper()}.")
            
        except Exception as e:
            # Catch MPS-specific sparse tensor errors or NotImplementedErrors
            if device == "mps":
                print(f"⚠️ Failed to load on MPS: {e}")
                print("🔄 specific MPS sparse tensor support is missing. Falling back to CPU...")
                self.model = whisper.load_model(model_size, device="cpu")
                print("✅ Whisper model loaded on CPU.")
            else:
                # If it's not an MPS issue (e.g. download failed), re-raise
                raise e

    def transcribe_stream(self, audio_bytes: bytes) -> WhisperLocalResult:
        """
        Saves raw audio bytes to a temp file and transcribes them.
        Assumes input is 44.1kHz (or other) and lets Whisper/FFmpeg handle resampling.
        """
        if not audio_bytes or len(audio_bytes) < 1000:
            return None

        temp_path = ""
        try:
            # 1. Save raw bytes to a temporary WAV file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                temp_path = temp_wav.name
                with wave.open(temp_path, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(44100)
                    wf.writeframes(audio_bytes)

            # 2. Transcribe
            result = self.model.transcribe(temp_path, fp16=False)
            text = result.get("text", "").strip()

            if text:
                return WhisperLocalResult(text)
            return None

        except Exception as e:
            print(f"❌ Whisper Transcription Error: {e}")
            return None
        finally:
            # Cleanup temp file
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)