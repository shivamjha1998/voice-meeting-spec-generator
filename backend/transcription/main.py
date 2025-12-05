import time
import json
import base64
import os
import redis
from backend.transcription.elevenlabs_client import ElevenLabsClient 
from backend.common import database, models
from sqlalchemy.orm import Session

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

def main():
    print("🎧 Starting Transcription Service (ElevenLabs)...")
    
    try:
        redis_client = redis.from_url(REDIS_URL)
        redis_client.ping()
        print(f"✅ Connected to Redis at {REDIS_URL}")
    except Exception as e:
        print(f"❌ Failed to connect to Redis: {e}")
        return

    stt_client = ElevenLabsClient()
    
    db = database.SessionLocal()

    print("📡 Listening for audio chunks on 'meeting_audio_queue'...")
    
    # Buffer for audio chunks
    # 44100 Hz * 2 bytes * 1 channel = 88200 bytes/sec
    # ElevenLabs Scribe likely needs > 0.5s. Let's buffer ~2 seconds (~176KB)
    BUFFER_SIZE_BYTES = 200 * 1024 
    audio_buffer = bytearray()
    
    while True:
        try:
            item = redis_client.blpop("meeting_audio_queue", timeout=5)
            
            if item:
                _, data_str = item
                data = json.loads(data_str)
                meeting_id = data.get("meeting_id")
                audio_b64 = data.get("audio_data")
                
                if audio_b64:
                    audio_bytes = base64.b64decode(audio_b64)
                    audio_buffer.extend(audio_bytes)
                    
                    # Only process if buffer is full enough
                    if len(audio_buffer) >= BUFFER_SIZE_BYTES:
                        print(f"🔄 Processing buffer of size {len(audio_buffer)} bytes...")
                        
                        # Process the buffer
                        text = stt_client.transcribe_stream(bytes(audio_buffer))
                        
                        if text and text.strip():
                            print(f"📝 Meeting {meeting_id}: {text}")
                            save_transcript(db, meeting_id, text)
                        
                        # Clear buffer after processing
                        # Note: In a real stream, you might want overlapping windows
                        audio_buffer = bytearray()
                        
        except Exception as e:
            print(f"⚠️ Error processing chunk: {e}")
            time.sleep(1)

def save_transcript(db: Session, meeting_id: int, text: str):
    try:
        transcript = models.Transcript(
            meeting_id=meeting_id,
            speaker="Speaker", 
            text=text
        )
        db.add(transcript)
        db.commit()
    except Exception as e:
        print(f"❌ DB Error: {e}")
        db.rollback()

if __name__ == "__main__":
    main()
