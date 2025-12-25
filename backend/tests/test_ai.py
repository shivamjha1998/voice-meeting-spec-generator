import pytest
from unittest.mock import MagicMock, patch
from backend.ai.tasks import generate_specification_task
from backend.common import models

@pytest.fixture
def mock_llm_client():
    with patch("backend.ai.tasks.LLMClient") as mock:
        yield mock

def test_generate_spec_task(db_session, mock_llm_client):
    # Setup Logic
    # 1. Create transcripts
    t1 = models.Transcript(meeting_id=50, speaker="User", text="We need a login page.")
    t2 = models.Transcript(meeting_id=50, speaker="PM", text="It should have Google Auth.")
    db_session.add_all([t1, t2])
    db_session.commit()
    
    # 2. Mock LLM Response
    mock_instance = mock_llm_client.return_value
    mock_instance.summarize_meeting.return_value = "Summary: effective login page discussion."
    mock_instance.generate_specification.return_value = "# Final Spec\n- Login Page\n- Google Auth"
    
    # Run Task (synchronously)
    # We mock database.SessionLocal to return our test db_session
    with patch("backend.ai.tasks.database.SessionLocal", return_value=db_session):
        result = generate_specification_task(meeting_id=50, project_id=10)
    
    assert result == "Success"
    
    # Verify Spec in DB
    spec = db_session.query(models.Specification).filter(models.Specification.meeting_id == 50).first()
    assert spec is not None
    assert "Final Spec" in spec.content
    assert spec.project_id == 10

def test_generate_spec_no_transcripts(db_session, mock_llm_client):
    with patch("backend.ai.tasks.database.SessionLocal", return_value=db_session):
        result = generate_specification_task(meeting_id=999, project_id=10)
    
    assert result == "No transcripts"
