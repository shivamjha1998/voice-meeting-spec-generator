import time
import json
import os
import redis
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

    print("waiting Waiting for jobs on 'spec_generation_queue'...")

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
        
        # 2. Generate Summary & Spec (Chain of Thought)
        print("   ... Summarizing ...")
        summary = llm_client.summarize_meeting(full_text)
        
        print("   ... Generating Spec ...")
        spec_content = llm_client.generate_specification(summary)
        
        # 3. Save to DB
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
    """
    print("🧠 AI Analyst listening on 'conversation_analysis_queue'...")
    while True:
        try:
            item = redis_client.blpop("conversation_analysis_queue", timeout=1)
            if item:
                _, data_str = item
                data = json.loads(data_str)
                meeting_id = data.get("meeting_id")
                text = data.get("text")
                
                # Ask LLM if we should intervene
                question = llm_client.generate_clarifying_question(text)
                
                if question:
                    print(f"💡 Generated Question: {question}")
                    # Send to TTS Queue
                    redis_client.rpush("speak_request_queue", json.dumps({
                        "meeting_id": meeting_id,
                        "text": question
                    }))
        except Exception as e:
            print(f"Analysis Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()