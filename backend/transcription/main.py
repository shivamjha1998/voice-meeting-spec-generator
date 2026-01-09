import time
import json
import sys
import base64
import os

# Fallback if MPS is not availableß
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

import redis
from backend.transcription.elevenlabs_client import ElevenLabsClient
from backend.common import database, models
from sqlalchemy.orm import Session

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
TRANSCRIPTION_PROVIDER = os.getenv("TRANSCRIPTION_PROVIDER", "elevenlabs").lower()

def main():
    print(f"🎧 Starting Transcription Service...")
    print(f"🔧 Configured Provider: {TRANSCRIPTION_PROVIDER.upper()}")
    
    try:
        redis_client = redis.from_url(REDIS_URL)
        redis_client.ping()
        print(f"✅ Connected to Redis at {REDIS_URL}")
    except Exception as e:
        print(f"❌ Failed to connect to Redis: {e}")
        return

    # --- CLIENT SELECTION LOGIC ---
    if TRANSCRIPTION_PROVIDER == "whisper_local":
        print("📥 Initializing Local Whisper Client...")
        from backend.transcription.whisper_local import WhisperLocalClient
        stt_client = WhisperLocalClient(model_size="base")
    else:
        print("☁️ Initializing ElevenLabs Client...")
        stt_client = ElevenLabsClient()

    db = database.SessionLocal()

    print("📡 Listening for audio chunks on 'meeting_audio_queue'...")
    
    # Buffer size
    BUFFER_SIZE_BYTES = 500 * 1024 
    audio_buffer = bytearray()
    
    while True:
        try:
            # 1. Try to get data with a timeout
            item = redis_client.blpop("meeting_audio_queue", timeout=5)
            
            if item:
                # --- DATA RECEIVED ---
                _, data_str = item
                data = json.loads(data_str)
                meeting_id = data.get("meeting_id")
                audio_b64 = data.get("audio_data")
                
                if audio_b64:
                    audio_bytes = base64.b64decode(audio_b64)
                    audio_buffer.extend(audio_bytes)
                    
                    # Process if buffer is full
                    if len(audio_buffer) >= BUFFER_SIZE_BYTES:
                        print(f"🔄 Processing buffer of size {len(audio_buffer)} bytes...")
                        result = stt_client.transcribe_stream(bytes(audio_buffer))
                        if result:
                            process_and_save_diarized(db, redis_client, meeting_id, result)
                        audio_buffer = bytearray()
            
            else:
                # --- TIMEOUT (Silence/End of Stream) ---
                if len(audio_buffer) > 0:
                    print(f"🧹 Flushing remaining buffer of size {len(audio_buffer)} bytes...")
                    
                    result = stt_client.transcribe_stream(bytes(audio_buffer))
                    if result:
                         process_and_save_diarized(db, redis_client, meeting_id, result)
                    
                    audio_buffer = bytearray()

        except KeyboardInterrupt:
            print("\n🛑 Stopping Transcription Service...")
            sys.exit(0)
        except Exception as e:
            print(f"⚠️ Error processing chunk: {e}")
            time.sleep(1)

def process_and_save_diarized(db: Session, redis_client: redis.Redis, meeting_id: int, transcription_result):
    """
    Groups words by speaker_id, saves to DB, and pushes to analysis queue.
    Handles both ElevenLabs (with diarization) and Whisper (text only).
    """
    if not transcription_result:
        return

    # Handle clients that don't return word-level timestamps/diarization (like basic Local Whisper)
    if not hasattr(transcription_result, 'words') or not transcription_result.words:
        if hasattr(transcription_result, 'text') and transcription_result.text:
             # Fallback to "Unknown" speaker
             save_and_publish(db, redis_client, meeting_id, "Unknown", transcription_result.text)
        return

    current_speaker = None
    current_text = []

    for word in transcription_result.words:
        # ElevenLabs returns 'speaker_id', some Whisper variants might differ.
        # We default to 'speaker_0' if missing.
        speaker = getattr(word, 'speaker_id', 'speaker_0') or 'speaker_0'
        text = word.text

        if current_speaker is not None and speaker != current_speaker:
            full_sentence = " ".join(current_text).strip()
            if full_sentence:
                print(f"   🗣️ {current_speaker}: {full_sentence}")
                save_and_publish(db, redis_client, meeting_id, current_speaker, full_sentence)
            current_text = []

        current_speaker = speaker
        current_text.append(text)

    # Flush the final speaker buffer
    if current_speaker and current_text:
        full_sentence = " ".join(current_text).strip()
        if full_sentence:
            print(f"   🗣️ {current_speaker}: {full_sentence}")
            save_and_publish(db, redis_client, meeting_id, current_speaker, full_sentence)

def save_and_publish(db: Session, redis_client: redis.Redis, meeting_id: int, speaker: str, text: str):
    """Saves to DB, queues for AI analysis, and publishes for Real-time UI"""
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
        db.refresh(transcript)

        # Payload for both AI and UI
        payload = {
            "id": transcript.id,
            "meeting_id": meeting_id,
            "speaker": formatted_speaker,
            "text": text,
            "timestamp": transcript.timestamp.isoformat() if transcript.timestamp else str(time.time()) 
        }
        json_payload = json.dumps(payload)

        # 2. Publish to AI Analysis Queue (List)
        redis_client.rpush("conversation_analysis_queue", json_payload)

        # 3. Publish to Real-time UI (Pub/Sub)
        redis_client.publish(f"meeting_{meeting_id}_updates", json_payload)
        
        print(f"   Pb Published update for meeting {meeting_id}")

    except Exception as e:
        print(f"❌ DB/Redis Error: {e}")
        db.rollback()

if __name__ == "__main__":
    main()