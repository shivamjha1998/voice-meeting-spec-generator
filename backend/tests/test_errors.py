import pytest
from unittest.mock import patch, MagicMock
from backend.bot.zoom_bot import ZoomBot
import redis

def test_redis_connection_error():
    # Simulate Redis being down for Bot
    with patch("backend.bot.common.base.redis.from_url") as mock_redis_ctor:
        mock_redis_ctor.side_effect = redis.exceptions.ConnectionError("Connection refused")
        
        # Bot initialization should fail or handle it. 
        # Based on code, it creates client at init. 
        with pytest.raises(redis.exceptions.ConnectionError):
            ZoomBot(meeting_id=1) 

def test_bot_join_failure(mock_playwright):
    # Simulate failed join (e.g. timeout)
    # We patch the instance method directly
    
    bot = ZoomBot(meeting_id=1)
    
    # Mock the internal _start_browser to prevent real browser launch
    bot._start_browser = MagicMock()
    
    # Mock page to raise exception on goto
    mock_page = MagicMock()
    mock_page.goto.side_effect = Exception("Timeout waiting for page")
    bot.page = mock_page
    
    # Mock leave_meeting to verify it's called
    bot.leave_meeting = MagicMock()
    
    # Run
    # join_meeting calls _start_browser first, then uses self.page.goto
    # valid url needed to pass early checks
    try:
        bot.join_meeting("https://zoom.us/j/123")
    except Exception:
        pass # The bot re-raises the exception, which is fine
        
    bot.leave_meeting.assert_called()
