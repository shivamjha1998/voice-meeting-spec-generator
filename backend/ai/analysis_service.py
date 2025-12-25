import json
import os
import redis
import time
from backend.ai.llm_client import LLMClient
from backend.common import database, models

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

def main():
    print("🤖 Starting AI Analysis Service (Timestamp-based Silence)...")
    
    try:
        redis_client = redis.from_url(REDIS_URL)
        redis_client.ping()
        print(f"✅ Connected to Redis at {REDIS_URL}")
    except Exception as e:
        print(f"❌ Redis Connection Error: {e}")
        return

    llm_client = LLMClient()
    db = database.SessionLocal()

    context_buffer = []
    MAX_BUFFER = 15 
    
    # 1. Configurable Silence Threshold (Seconds)
    SILENCE_THRESHOLD = 3.0 
    last_speech_time = time.time()
    
    current_meeting_id = None

    print(f"📡 Listening... (Will speak after {SILENCE_THRESHOLD}s of silence)")

    while True:
        try:
            # 2. Short timeout (0.5s) to check the clock frequently
            # This prevents blocking for too long if we need to trigger logic
            item = redis_client.blpop("conversation_analysis_queue", timeout=0.5)
            
            should_analyze = False
            current_time = time.time()
            
            if item:
                # --- SPEECH RECEIVED ---
                # Reset the silence clock
                last_speech_time = current_time
                
                _, data_str = item
                data = json.loads(data_str)
                text = data.get("text")
                new_id = data.get("meeting_id")
                speaker = data.get("speaker")

                if new_id:
                    current_meeting_id = new_id

                # Handle Clear Signal
                if text == "CLEAR_BUFFER_SIGNAL":
                    print(f"🧹 Clearing buffer for Meeting {current_meeting_id}")
                    context_buffer = []
                    continue 

                context_buffer.append(f"{speaker}: {text}")
                
                # Sliding Window: Keep buffer manageable, but DON'T trigger analysis
                if len(context_buffer) > MAX_BUFFER:
                    context_buffer.pop(0)

            else:
                # --- IDLE / POLLING ---
                # Calculate how long it has been since the last word
                time_since_speech = current_time - last_speech_time
                
                # Trigger ONLY if we have context AND sufficient silence has passed
                if (len(context_buffer) > 0 and 
                    current_meeting_id and 
                    time_since_speech > SILENCE_THRESHOLD):
                    
                    print(f"⏳ Silence detected ({time_since_speech:.1f}s). Triggering Analysis...")
                    should_analyze = True

            # --- ANALYSIS LOGIC ---
            if should_analyze and context_buffer and current_meeting_id:
                full_context = "\n".join(context_buffer)
                
                # Reset DB session safely
                db.close()
                db = database.SessionLocal()
                q_setting = db.query(models.Setting).filter(models.Setting.key == "question_prompt").first()
                
                default_prompt = (
                    "You are a helpful Project Manager Assistant. "
                    "The speaker has paused. If there is an ambiguity or missing detail in the recent text, ask a short clarification question. "
                    "If everything is clear, say NO_QUESTION."
                )
                prompt = q_setting.value if q_setting else default_prompt
                
                print(f"🤔 Asking AI...")
                question = llm_client.generate_clarifying_question(full_context, prompt)
                
                if question and len(question) > 5 and "NO_QUESTION" not in question:
                    print(f"💡 AI Decided to Speak: {question}")
                    
                    speak_msg = {
                        "meeting_id": current_meeting_id,
                        "text": question
                    }
                    redis_client.rpush("speak_request_queue", json.dumps(speak_msg))
                    
                    # Clear buffer to reset context state
                    context_buffer = []
                    # Reset clock so we don't trigger again immediately for empty buffer
                    last_speech_time = time.time()
                else:
                    print(f"🤐 AI stayed silent.")
                    # If AI had nothing to say, clear buffer to prevent "Silence Loop"
                    # analyzing the same text repeatedly.
                    context_buffer = []
                    last_speech_time = time.time()

        except Exception as e:
            print(f"⚠️ Analysis Service Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()