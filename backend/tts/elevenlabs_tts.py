import os
from elevenlabs.client import ElevenLabs

class ElevenLabsTTSClient:
    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            print("⚠️ WARNING: ELEVENLABS_API_KEY is not set.")
        self.client = ElevenLabs(api_key=self.api_key)

    def synthesize_speech(self, text: str, output_file: str = "output.mp3") -> str:
        """
        Generates speech using ElevenLabs and saves it to a file.
        """
        print(f"🗣️ Synthesizing speech (ElevenLabs): '{text}'")
        try:
            # Generate audio stream
            audio_generator = self.client.generate(
                text=text,
                voice="Rachel", 
                model="eleven_monolingual_v1"
            )
            
            # Save stream to file
            os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)

            with open(output_file, "wb") as f:
                for chunk in audio_generator:
                    f.write(chunk)
            
            print(f"✅ Audio saved to {output_file}")
            return output_file
            
        except Exception as e:
            print(f"❌ ElevenLabs TTS Error: {e}")
            return None