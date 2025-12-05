import time
import json
import base64
import os
import redis
from backend.transcription.whisper_client import WhisperClient
from backend.common import database, models
from sqlalchemy.orm import Session

# Connect to Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

def main():
    print("🎧 Starting Transcription Service...")
    
    # Initialize Clients
    try:
        redis_client = redis.from_url(REDIS_URL)
        # Check connection
        redis_client.ping()
        print(f"✅ Connected to Redis at {REDIS_URL}")
    except Exception as e:
        print(f"❌ Failed to connect to Redis: {e}")
        return

    whisper_client = WhisperClient()
    
    # Connect to DB
    db = database.SessionLocal()

    print("fw Listening for audio chunks on 'meeting_audio_queue'...")
    
    while True:
        try:
            # Blocking pop: waits until data is available in the queue
            # This is where the service "feeds" off the stream
            item = redis_client.blpop("meeting_audio_queue", timeout=5)
            
            if item:
                # Redis returns a tuple (queue_name, data)
                _, data_str = item
                
                # Parse the JSON message from the Bot
                data = json.loads(data_str)
                meeting_id = data.get("meeting_id")
                audio_b64 = data.get("audio_data")
                
                if audio_b64:
                    # Decode back to raw bytes
                    audio_bytes = base64.b64decode(audio_b64)
                    
                    # Send to Whisper API
                    text = whisper_client.transcribe_stream(audio_bytes)
                    
                    if text and text.strip():
                        print(f"📝 Meeting {meeting_id}: {text}")
                        # Save to Database
                        save_transcript(db, meeting_id, text)
                        
        except Exception as e:
            print(f"⚠️ Error processing chunk: {e}")
            time.sleep(1) # Prevent rapid loop on error

def save_transcript(db: Session, meeting_id: int, text: str):
    try:
        # In the future, 'speaker' will come from diarization
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
