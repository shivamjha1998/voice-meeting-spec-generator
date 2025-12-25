import pytest
import json
from unittest.mock import patch, MagicMock

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
    
    # We need to patch the Redis class used in the endpoint
    with patch("backend.api.main.redis_async.Redis", return_value=mock_redis_instance):
        with client.websocket_connect("/ws/meetings/1") as websocket:
            # The endpoint waits for a message. 
            # Our mock yields one immediately.
            data = websocket.receive_text()
            assert "Hello" in data
