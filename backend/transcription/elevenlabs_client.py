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

    def transcribe_stream(self, audio_bytes: bytes):
        """
        Sends audio to ElevenLabs Scribe API with Diarization enabled.
        Returns the full transcription object containing words/speakers.
        """
        try:
            # 1. Convert raw PCM to WAV container
            audio_file = self._add_wav_header(audio_bytes)
            
            # 2. Call ElevenLabs Scribe
            transcription = self.client.speech_to_text.convert(
                file=audio_file,
                model_id="scribe_v1",
                tag_audio_events=False,
                language_code="eng",
                diarize=True
            )
            
            return transcription
            
        except Exception as e:
            print(f"❌ ElevenLabs STT Error: {e}")
            return None