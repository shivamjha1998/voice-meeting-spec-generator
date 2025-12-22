from backend.celery_app import celery_app
from backend.common import database, models
from backend.ai.llm_client import LLMClient
from sqlalchemy.orm import Session

@celery_app.task(name="generate_specification_task")
def generate_specification_task(meeting_id: int, project_id: int):
    """
    Celery task to generate a specification from meeting transcripts.
    """
    print(f"🚀 Celery Worker starting Spec Gen for Meeting {meeting_id}...")
    
    db = database.SessionLocal()
    try:
        # 1. Fetch Data
        transcripts = db.query(models.Transcript)\
            .filter(models.Transcript.meeting_id == meeting_id)\
            .order_by(models.Transcript.timestamp).all()
        
        if not transcripts:
            print("❌ No transcripts found. Aborting.")
            return "No transcripts"

        full_text = "\n".join([f"{t.speaker}: {t.text}" for t in transcripts])
        
        # 2. Get Settings
        spec_setting = db.query(models.Setting).filter(models.Setting.key == "spec_prompt").first()
        custom_prompt = spec_setting.value if spec_setting else None

        # 3. AI Processing
        llm_client = LLMClient()
        print("   ... Summarizing ...")
        summary = llm_client.summarize_meeting(full_text)
        
        print("   ... Generating Specification ...")
        spec_content = llm_client.generate_specification(summary, custom_prompt=custom_prompt)
        
        # 4. Save Result
        spec = models.Specification(
            project_id=project_id,
            meeting_id=meeting_id,
            content=spec_content,
            version="1.0.0"
        )
        db.add(spec)
        db.commit()
        print(f"✅ Specification created for Meeting {meeting_id}")
        return "Success"

    except Exception as e:
        print(f"❌ Task Failed: {e}")
        db.rollback()
        raise e
    finally:
        db.close()