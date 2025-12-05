import os
import io
import wave
from elevenlabs.client import ElevenLabs

class ElevenLabsClient:
    def __init__(self):
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            print("⚠️ WARNING: ELEVENLABS_API_KEY is not set.")
        self.client = ElevenLabs(api_key=api_key)

    def _add_wav_header(self, pcm_data: bytes, sample_rate=44100, channels=1, sampwidth=2) -> io.BytesIO:
        """
        Wraps raw PCM audio bytes into a valid in-memory WAV file.
        Required because Scribe expects a file format, not raw bytes.
        """
        io_bytes = io.BytesIO()
        with wave.open(io_bytes, 'wb') as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(sampwidth)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm_data)
        io_bytes.seek(0)
        return io_bytes

    def transcribe_stream(self, audio_bytes: bytes) -> str:
        """
        Sends audio to ElevenLabs Scribe API.
        """
        try:
            # 1. Convert raw PCM to WAV container
            # Note: Ensure these match your recorder.py settings (default: 44100Hz, 1ch, 16-bit)
            audio_file = self._add_wav_header(audio_bytes)
            
            # 2. Call ElevenLabs Scribe
            # 'scribe_v1' is their speech-to-text model
            transcription = self.client.speech_to_text.convert(
                file=audio_file,
                model_id="scribe_v1",
                tag_audio_events=False, # Set True if you want [laughter] tags
                language_code="eng",    # Explicitly set for better accuracy
                diarize=False
            )
            
            return transcription.text
            
        except Exception as e:
            print(f"❌ ElevenLabs STT Error: {e}")
            return ""