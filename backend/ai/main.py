import time
import json
import os
import redis
import threading
from sqlalchemy.orm import Session
from backend.common import database, models
from backend.ai.llm_client import LLMClient

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

def main():
    print("🧠 Starting AI Processing Service...")
    
    # Initialize Clients
    try:
        redis_client = redis.from_url(REDIS_URL)
        llm_client = LLMClient()
    except Exception as e:
        print(f"❌ Initialization Failed: {e}")
        return

    # --- Start Real-time Analyst in a separate thread ---
    print("🚀 Launching Real-time Analyst Thread...")
    analysis_thread = threading.Thread(
        target=run_realtime_analysis, 
        args=(redis_client, llm_client),
        daemon=True
    )
    analysis_thread.start()

    print("waiting Waiting for jobs on 'spec_generation_queue'...")

    # Main thread handles Specification Generation (heavy task)
    while True:
        try:
            # Blocking pop: waits for a job
            item = redis_client.blpop("spec_generation_queue", timeout=5)
            
            if item:
                _, job_data_str = item
                job_data = json.loads(job_data_str)
                meeting_id = job_data.get("meeting_id")
                project_id = job_data.get("project_id")
                
                print(f"⚙️ Processing Meeting ID: {meeting_id}")
                process_meeting(meeting_id, project_id, llm_client)
                
        except Exception as e:
            print(f"⚠️ Worker Error: {e}")
            time.sleep(1)

def process_meeting(meeting_id: int, project_id: int, llm_client: LLMClient):
    db = database.SessionLocal()
    try:
        # 1. Fetch Transcripts
        transcripts = db.query(models.Transcript)\
            .filter(models.Transcript.meeting_id == meeting_id)\
            .order_by(models.Transcript.timestamp).all()
        
        if not transcripts:
            print("❌ No transcripts found. Skipping.")
            return

        # Combine into one text block
        full_text = "\n".join([f"{t.speaker}: {t.text}" for t in transcripts])
        
        # 2. Fetch Custom Spec Prompt from Settings
        spec_setting = db.query(models.Setting).filter(models.Setting.key == "spec_prompt").first()
        custom_prompt = spec_setting.value if spec_setting else None

        # 3. Generate Summary & Spec (Chain of Thought)
        print("   ... Summarizing ...")
        summary = llm_client.summarize_meeting(full_text)
        
        print(f"   ... Generating Spec {'(Custom Prompt)' if custom_prompt else ''} ...")
        spec_content = llm_client.generate_specification(summary, custom_prompt=custom_prompt)
        
        # 4. Save to DB
        spec = models.Specification(
            project_id=project_id,
            meeting_id=meeting_id,
            content=spec_content,
            version="1.0.0"
        )
        db.add(spec)
        db.commit()
        print("✅ Specification Saved!")

    except Exception as e:
        print(f"❌ Processing Failed: {e}")
        db.rollback()
    finally:
        db.close()

def run_realtime_analysis(redis_client, llm_client):
    """
    Listens for live transcript segments and generates questions.
    Uses the passed redis_client instance.
    """
    print("🧠 AI Analyst listening on 'conversation_analysis_queue'...")
    
    while True:
        try:
            item = redis_client.blpop("conversation_analysis_queue", timeout=5)
            
            if item:
                _, data_str = item
                data = json.loads(data_str)
                meeting_id = data.get("meeting_id")
                text = data.get("text")
                speaker = data.get("speaker")
                
                print(f"   🔍 Analyzing segment from {speaker}...")
                
                # Fetch Question Prompt from Settings
                # (We open a short-lived session here to get dynamic updates)
                db = database.SessionLocal()
                q_setting = db.query(models.Setting).filter(models.Setting.key == "question_prompt").first()
                custom_q_prompt = q_setting.value if q_setting else None
                db.close()

                # Ask LLM if we should intervene
                question = llm_client.generate_clarifying_question(text, custom_prompt=custom_q_prompt)
                
                if question and question != "NO_QUESTION":
                    print(f"💡 Generated Question: {question}")
                    
                    # Send to TTS Queue using the same client
                    redis_client.rpush("speak_request_queue", json.dumps({
                        "meeting_id": meeting_id,
                        "text": question
                    }))
        except Exception as e:
            print(f"Analysis Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()