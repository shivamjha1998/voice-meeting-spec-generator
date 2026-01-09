import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from backend.api.main import app
from backend.api.auth import create_access_token
from backend.common import models

def test_websocket_connection(client):
    # Depending on how the websocket is implemented, we might need to mock the Redis PubSub
    # Assuming the websocket subscribes to Redis
    
    # Mock Redis Async
    mock_redis_instance = MagicMock()
    # Ensure pubsub() returns the mock_pubsub object
    mock_pubsub = MagicMock()
    mock_redis_instance.pubsub.return_value = mock_pubsub
    
    # Async mocks
    async def async_subscribe(*args, **kwargs):
        return None
        
    async def async_get_message(*args, **kwargs):
        # Return a message once
        return {"type": "message", "data": b'{"speaker": "Bot", "text": "Hello"}'}

    # IMPORTANT: method calls on MagicMock return another MagicMock by default.
    # We must set side_effect to our async function so that 'await pubsub.subscribe()' works.
    mock_pubsub.subscribe.side_effect = async_subscribe
    mock_pubsub.get_message.side_effect = async_get_message
    mock_pubsub.unsubscribe.side_effect = async_subscribe  # reuse empty async func
    
    # Also need to mock close() as async
    async def async_close():
        return None
    mock_redis_instance.close.side_effect = async_close
    
    # Mock Redis class
    with patch("backend.api.main.redis_async.Redis", return_value=mock_redis_instance):
        # Mock auth token validation
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        
        # Mock meeting retrieval for authorization check
        mock_meeting = MagicMock()
        mock_meeting.id = 1
        mock_meeting.project.owner_id = 1
        
        with patch("backend.api.main.validate_token", return_value=mock_user), \
             patch("backend.api.main.crud.get_meeting", return_value=mock_meeting):
            
            with client.websocket_connect("/ws/meetings/1?token=test_token") as websocket:
                # The endpoint waits for a message. 
                # Our mock yields one immediately.
                data = websocket.receive_text()
                assert "Hello" in data

def test_websocket_rejects_no_token(client):
    """Verify 403/Policy Violation if no token provided."""
    with pytest.raises(Exception): # Starlette TestClient raises on disconnect
        with client.websocket_connect("/ws/meetings/1") as websocket:
            pass

def test_websocket_accepts_valid_token(client, db_session, test_user):
    # 1. Setup Meeting
    project = models.Project(owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    meeting = models.Meeting(project_id=project.id, meeting_url="x")
    db_session.add(meeting)
    db_session.commit()

    # 2. Create Token
    token = create_access_token({"sub": str(test_user.id)})

    # 3. Connect
    with client.websocket_connect(f"/ws/meetings/{meeting.id}?token={token}") as websocket:
        # We assume connection is accepted if no error raised immediately
        pass
