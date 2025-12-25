import pytest
from unittest.mock import MagicMock, patch
import json
import base64
from backend.transcription.main import process_and_save_diarized
from backend.common import models

@pytest.fixture
def mock_stt_client():
    with patch("backend.transcription.main.ElevenLabsClient") as mock:
        yield mock

@pytest.fixture
def mock_redis():
    return MagicMock()

def test_process_diarized_save(db_session, mock_redis):
    # Mock result object from ElevenLabs
    mock_result = MagicMock()
    
    # Mock words
    Word = MagicMock
    w1 = MagicMock(text="Hello", speaker_id="speaker_A")
    w2 = MagicMock(text="world", speaker_id="speaker_A")
    w3 = MagicMock(text="Hi", speaker_id="speaker_B")
    
    mock_result.words = [w1, w2, w3]
    
    # Run Function
    process_and_save_diarized(db_session, mock_redis, meeting_id=99, transcription_result=mock_result)
    
    # Verify DB
    transcripts = db_session.query(models.Transcript).filter(models.Transcript.meeting_id == 99).all()
    assert len(transcripts) == 2
    assert transcripts[0].speaker == "Speaker A"
    assert transcripts[0].text == "Hello world"
    assert transcripts[1].speaker == "Speaker B"
    assert transcripts[1].text == "Hi"
    
    # Verify Redis Publish (Analysis + Real-time)
    assert mock_redis.rpush.call_count == 2 # Analysis Queue
    assert mock_redis.publish.call_count == 2 # Realtime Pub/Sub

def test_process_fallback_text(db_session, mock_redis):
    # Test fallback when diarization fails but text exists
    mock_result = MagicMock()
    del mock_result.words # No words
    mock_result.text = "Fallback text"
    
    process_and_save_diarized(db_session, mock_redis, meeting_id=100, transcription_result=mock_result)
    
    transcripts = db_session.query(models.Transcript).filter(models.Transcript.meeting_id == 100).all()
    assert len(transcripts) == 1
    assert transcripts[0].text == "Fallback text"
    assert transcripts[0].speaker == "Unknown"
