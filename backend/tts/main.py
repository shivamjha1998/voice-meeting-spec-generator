import time
import json
import os
import redis
from backend.tts.elevenlabs_tts import ElevenLabsTTSClient

# Redis Connection
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

def main():
    print("🗣️ Starting ElevenLabs TTS Service...")
    
    try:
        redis_client = redis.from_url(REDIS_URL)
        redis_client.ping()
        print(f"✅ Connected to Redis at {REDIS_URL}")
    except Exception as e:
        print(f"❌ Failed to connect to Redis: {e}")
        return

    tts_client = ElevenLabsTTSClient()
    
    # Ensure shared audio directory exists
    AUDIO_DIR = os.path.join(os.getcwd(), "backend", "temp_audio")
    os.makedirs(AUDIO_DIR, exist_ok=True)

    print("Fn Listening for jobs on 'speak_request_queue'...")

    while True:
        try:
            # Blocking pop
            item = redis_client.blpop("speak_request_queue", timeout=5)
            
            if item:
                _, data_str = item
                data = json.loads(data_str)
                text = data.get("text")
                meeting_id = data.get("meeting_id")
                
                if text:
                    # Check if this is the standard consent announcement
                    CONSENT_TEXT_PART = "Hello everyone, I am the AI Meeting Assistant"
                    is_consent = CONSENT_TEXT_PART in text
                    
                    if is_consent:
                        # Use a static filename for caching
                        filename = "ai_consent.mp3"
                        file_path = os.path.join(AUDIO_DIR, filename)
                        
                        # Only generate if it doesn't exist
                        if os.path.exists(file_path):
                            print(f"♻️ Using cached consent audio: {file_path}")
                            output_path = file_path
                        else:
                            print("🆕 Generating new consent audio...")
                            output_path = tts_client.synthesize_speech(text, output_file=file_path)
                    else:
                        # Dynamic/Question audio - always new
                        filename = f"question_{meeting_id}_{int(time.time())}.mp3"
                        file_path = os.path.join(AUDIO_DIR, filename)
                        output_path = tts_client.synthesize_speech(text, output_file=file_path)
                    
                    if output_path:
                        # 2. Notify Bot to Play
                        playback_msg = {
                            "meeting_id": meeting_id,
                            "file_path": output_path
                        }
                        redis_client.rpush("audio_playback_queue", json.dumps(playback_msg))
                        print(f"✅ Sent playback request for: {filename}")

        except Exception as e:
            print(f"⚠️ TTS Worker Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()