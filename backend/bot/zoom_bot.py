import time
import threading
import os
import redis
import json
import base64
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from .recorder import AudioRecorder

class ZoomBot:
    def __init__(self):
        self.driver = None
        self.is_connected = False
        self.recorder = AudioRecorder(filename="zoom_meeting.wav")
        self.redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        self.meeting_id = 1

    def join_meeting(self, meeting_url: str):
        """
        Joins a Zoom meeting using Selenium Webdriver.
        Note: This requires Chrome to be installed on the machine running this code.
        """
        print(f"🤖 Bot attempting to join Zoom: {meeting_url}")
        
        # Setup Chrome Options (Headless typically blocked by Zoom, using standard)
        chrome_options = Options()
        # chrome_options.add_argument("--headless") # Zoom often blocks headless
        chrome_options.add_argument("--use-fake-ui-for-media-stream") # Auto-allow mic/cam
        chrome_options.add_argument("--disable-notifications")
        
        try:
            # Initialize Driver
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()), 
                options=chrome_options
            )
            
            # 1. Go to URL
            self.driver.get(meeting_url)
            time.sleep(3) # Wait for redirect logic

            # 2. Handle "Open Zoom Meetings?" popup (Selenium can't click native browser popups easily)
            # The trick is usually to click "Join from Browser" link if it appears, 
            # or we rely on the user having the app. 
            # For a pure bot, we often try to force "Join from Browser".
            
            # Attempt to find "Join from your browser" link
            try:
                # Sometimes this link is hidden behind "Launch Meeting"
                launch_btn = self.driver.find_element(By.CLASS_NAME, "_Tb0_oF2_0") # Class names change often!
                # This part is brittle as Zoom changes class names. 
                # Better strategy: Look for text
                pass
            except:
                pass

            self.is_connected = True
            print("✅ Bot browser launched. Please manually click 'Join' if strictly automated flow fails.")
            
        except Exception as e:
            print(f"❌ Failed to join Zoom: {e}")
            self.leave_meeting()

    def start_audio_stream(self):
        """
        Starts recording system audio (Microphone) as a proxy for meeting audio.
        """
        if not self.is_connected:
            print("⚠️ Warning: Bot not connected to Zoom, but starting mic recording anyway.")
        
        print("🎙️ Starting Audio Stream (Microphone)...")
        self.recorder.start_recording()
        
        # In a real app, we would consume this generator and send to Whisper
        # For now, we run it in a thread to verify it works
        threading.Thread(target=self._consume_stream, daemon=True).start()


    def leave_meeting(self):
        print("mb Bot leaving meeting...")
        self.is_connected = False
        self.recorder.stop_recording()
        if self.driver:
            self.driver.quit()
            self.driver = None

    def _consume_stream(self):
        """Consumes audio from recorder and pushes to Redis."""
        import redis
        import json
        import base64
        
        # Connect to Redis inside the process
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        print("VX Stream publisher started")
        
        for chunk in self.recorder.stream_audio():
            if chunk:
                # Prepare the message payload
                message = {
                    "meeting_id": 1, # Hardcoded ID for this test
                    "audio_data": base64.b64encode(chunk).decode('utf-8'),
                    "timestamp": time.time()
                }
                # Push to the SAME queue name the Transcription service is listening to
                r.rpush("meeting_audio_queue", json.dumps(message))
