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
    print("🎧 Starting Transcription Service (ElevenLabs + Diarization)...")
    
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
    BUFFER_SIZE_BYTES = 500 * 1024
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
                        result = stt_client.transcribe_stream(bytes(audio_buffer))
                        
                        if result:
                            # Group words by speaker AND push to Redis
                            process_and_save_diarized(db, redis_client, meeting_id, result)
                        
                        # Clear buffer
                        audio_buffer = bytearray()
                        
        except Exception as e:
            print(f"⚠️ Error processing chunk: {e}")
            time.sleep(1)

def process_and_save_diarized(db: Session, redis_client: redis.Redis, meeting_id: int, transcription_result):
    """
    Groups words by speaker_id, saves to DB, and pushes to analysis queue.
    """
    if not transcription_result or not hasattr(transcription_result, 'words'):
        # Fallback for empty or error responses
        if hasattr(transcription_result, 'text') and transcription_result.text:
             save_and_publish(db, redis_client, meeting_id, "Unknown", transcription_result.text)
        return

    current_speaker = None
    current_text = []

    for word in transcription_result.words:
        speaker = getattr(word, 'speaker_id', 'speaker_0') or 'speaker_0'
        text = word.text

        # If speaker changes, save the accumulated text for the previous speaker
        if current_speaker is not None and speaker != current_speaker:
            full_sentence = " ".join(current_text).strip()
            if full_sentence:
                print(f"   🗣️ {current_speaker}: {full_sentence}")
                save_and_publish(db, redis_client, meeting_id, current_speaker, full_sentence)
            current_text = []

        current_speaker = speaker
        current_text.append(text)

    # Save the final buffer
    if current_speaker and current_text:
        full_sentence = " ".join(current_text).strip()
        if full_sentence:
            print(f"   🗣️ {current_speaker}: {full_sentence}")
            save_and_publish(db, redis_client, meeting_id, current_speaker, full_sentence)

def save_and_publish(db: Session, redis_client: redis.Redis, meeting_id: int, speaker: str, text: str):
    """Saves to DB and publishes to Redis for AI analysis"""
    try:
        # 1. Save to DB
        formatted_speaker = speaker.replace("_", " ").title()
        transcript = models.Transcript(
            meeting_id=meeting_id,
            speaker=formatted_speaker,
            text=text
        )
        db.add(transcript)
        db.commit()

        # 2. Publish to AI Analysis Queue
        analysis_payload = {
            "meeting_id": meeting_id,
            "speaker": formatted_speaker,
            "text": text
        }
        redis_client.rpush("conversation_analysis_queue", json.dumps(analysis_payload))
        
    except Exception as e:
        print(f"❌ DB/Redis Error: {e}")
        db.rollback()

if __name__ == "__main__":
    main()