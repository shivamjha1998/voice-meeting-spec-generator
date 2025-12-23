import json
import os
import redis
import time
from backend.ai.llm_client import LLMClient
from backend.common import database, models

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

def main():
    print("🤖 Starting AI Analysis Service (Real-time Questions)...")
    
    try:
        redis_client = redis.from_url(REDIS_URL)
        redis_client.ping()
        print(f"✅ Connected to Redis at {REDIS_URL}")
    except Exception as e:
        print(f"❌ Redis Connection Error: {e}")
        return

    llm_client = LLMClient()
    db = database.SessionLocal()

    # Buffer to hold recent conversation context
    context_buffer = []
    MAX_BUFFER = 5

    print("📡 Listening for conversation on 'conversation_analysis_queue'...")

    while True:
        try:
            # Pop transcript segments pushed by the Transcription service
            item = redis_client.blpop("conversation_analysis_queue", timeout=5)
            
            if item:
                _, data_str = item
                data = json.loads(data_str)
                text = data.get("text")
                meeting_id = data.get("meeting_id")
                speaker = data.get("speaker")

                context_buffer.append(f"{speaker}: {text}")
                
                # Logic: Every X segments, ask the AI if clarification is needed
                if len(context_buffer) >= MAX_BUFFER:
                    full_context = "\n".join(context_buffer)
                    
                    # Fetch prompt from settings
                    q_setting = db.query(models.Setting).filter(models.Setting.key == "question_prompt").first()
                    prompt = q_setting.value if q_setting else None
                    
                    # AI Analysis
                    question = llm_client.generate_clarifying_question(full_context, prompt)
                    
                    if question and len(question) > 5:
                        print(f"💡 AI clarification identified for Meeting {meeting_id}: {question}")
                        
                        # Push to TTS queue
                        speak_msg = {
                            "meeting_id": meeting_id,
                            "text": question
                        }
                        redis_client.rpush("speak_request_queue", json.dumps(speak_msg))
                        
                        # Clear buffer after a question is asked to avoid repetition
                        context_buffer = []
                    else:
                        # Keep a sliding window of context
                        context_buffer = context_buffer[1:]

        except Exception as e:
            print(f"⚠️ Analysis Service Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()