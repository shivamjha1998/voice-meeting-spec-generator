import time
import threading
import os
import redis
import json
import base64
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from .recorder import AudioRecorder

class GoogleMeetBot:
    def __init__(self, meeting_id=1):
        self.driver = None
        self.is_connected = False
        self.recorder = AudioRecorder(filename="meet_meeting.wav")
        self.redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        self.meeting_id = meeting_id

    def join_meeting(self, meeting_url: str):
        """
        Joins a Google Meet meeting using undetected-chromedriver to avoid bot detection.
        """
        import undetected_chromedriver as uc
        print(f"🤖 Bot attempting to join Google Meet: {meeting_url}")
        
        # 1. Setup Chrome Options
        options = uc.ChromeOptions()
        # Allow microphone/camera permissions automatically (needed for the site to load properly)
        options.add_argument("--use-fake-ui-for-media-stream")
        options.add_argument("--disable-notifications")
        options.add_argument("--autoplay-policy=no-user-gesture-required")
        # Default to non-headless for now as headless is easier to detect
        # options.add_argument("--headless") 

        try:
            self.driver = uc.Chrome(options=options, version_main=143)
            
            # 2. Go to the URL
            self.driver.get(meeting_url)
            
            # 3. Handle Pre-Join Screen (Turn off Mic/Cam)
            try:
                body = WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                time.sleep(3)
                body.send_keys(Keys.CONTROL, 'd')
                time.sleep(0.5)
                body.send_keys(Keys.CONTROL, 'e')
                print("Possibly muted mic/cam using shortcuts.")
            except Exception as e:
                print(f"⚠️ Could not use shortcuts to mute: {e}")

            # 3.5 Handle 'What's your name?' input
            try:
                name_input = WebDriverWait(self.driver, 5).until(
                     EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Your name']"))
                )
                if name_input:
                    name_input.clear()
                    name_input.send_keys("AI Assistant Bot")
            except:
                print("Name input not found or not required.")

            # 4. Click 'Join now' or 'Ask to join'
            try:
                # Find the button first to check its text
                join_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Join now') or contains(text(), 'Ask to join')]/ancestor::button"))
                )
                button_text = join_button.text
                print(f"🖱️ Found Join Button. Text: '{button_text}'")
                join_button.click()
                print(f"✅ Clicked '{button_text}'")
            except Exception as e:
                print(f"❌ Could not find/click Join button. You may need to click it manually. Error: {e}")

            # 5. Wait to ensure we are in
            time.sleep(5)
            self.is_connected = True
            print("✅ Bot successfully loaded Google Meet.")
            pass

        except Exception as e:
            print(f"❌ Failed to join Google Meet: {e}")
            self.leave_meeting()

    def start_audio_stream(self):
        """
        Starts recording system audio and pushes chunks to Redis.
        """
        if not self.is_connected:
            print("⚠️ Warning: Bot not connected to Meet, but starting mic recording anyway.")
        
        print("🎙️ Starting Audio Stream (Microphone)...")
        self.recorder.start_recording()
        
        # Start the background thread to push audio to Redis
        threading.Thread(target=self._consume_stream, daemon=True).start()

    def leave_meeting(self):
        print("👋 Bot leaving meeting...")
        self.is_connected = False
        try:
            self.recorder.stop_recording()
        except:
            pass
            
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None

    def _consume_stream(self):
        """
        Consumes audio from recorder and pushes to Redis queue 'meeting_audio_queue'.
        This matches the Transcription service's listener.
        """
        # Create a new Redis connection for this thread
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        print("VX Stream publisher started")
        
        for chunk in self.recorder.stream_audio():
            if chunk:
                # Prepare the message payload
                message = {
                    "meeting_id": self.meeting_id,
                    "audio_data": base64.b64encode(chunk).decode('utf-8'),
                    "timestamp": time.time()
                }
                # Push to the SAME queue name the Transcription service is listening to
                r.rpush("meeting_audio_queue", json.dumps(message))