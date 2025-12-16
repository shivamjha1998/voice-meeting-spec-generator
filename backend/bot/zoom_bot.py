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
    def __init__(self, meeting_id=1):
        self.driver = None
        self.is_connected = False
        self.recorder = AudioRecorder(filename="zoom_meeting.wav")
        self.redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        self.meeting_id = meeting_id

    def join_meeting(self, meeting_url: str):
        """
        Joins a Zoom meeting using undetected-chromedriver.
        """
        import undetected_chromedriver as uc
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        print(f"🤖 Bot attempting to join Zoom: {meeting_url}")
        
        # Transform URL to Web Client (WC) format to bypass app prompts
        import re
        # Regex to capture domain, meeting id, and existing query params
        # Handles /j/ (join) and /s/ (start) links
        pattern = r"(https?://.*?zoom\.us)/[js]/(\d+)(.*)"
        match = re.search(pattern, meeting_url)
        if match:
             base_url, meeting_id, rest = match.groups()
             # 'rest' contains ?pwd=... or similar
             # Construct WC url
             wc_url = f"{base_url}/wc/{meeting_id}/join{rest}"
             print(f"🔄 Converted to Web Client URL: {wc_url}")
             meeting_url = wc_url
        else:
             print("⚠️ URL did not match standard Zoom pattern, using as-is.")

        # Setup Chrome Options
        options = uc.ChromeOptions()
        options.add_argument("--use-fake-ui-for-media-stream")
        options.add_argument("--disable-notifications")
        options.add_argument("--autoplay-policy=no-user-gesture-required")

        try:
            # Initialize Driver
            self.driver = uc.Chrome(options=options, version_main=143)
            
            # 1. Go to URL (Now directly to Web Client)
            self.driver.get(meeting_url)
            
            # 1.5 Handle Cookie Popup (if present)
            try:
                cookie_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[@id='onetrust-accept-btn-handler' or contains(text(), 'Agree') or contains(text(), 'Accept') or contains(@class, 'osano-cm-accept-all')]"))
                )
                cookie_btn.click()
                print("✅ Accepted Cookies")
            except:
                print("No cookie popup found (or timed out).")

            # 2. Handle "Your Name" Input
            try:
                selectors = [
                    "//input[contains(@id, 'name')]",
                    "//input[@id='inputname']",
                    "//input[@placeholder='Your Name']"
                ]
                
                name_input = None
                for selector in selectors:
                    try:
                        name_input = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, selector))
                        )
                        if name_input:
                            break
                    except:
                        continue
                
                if not name_input:
                    # Final try with longer wait on the most common one
                    name_input = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//input[@id='inputname']"))
                    )

                name_input.clear()
                name_input.send_keys("AI Assistant Bot")
                
                # Check for and Click Join
                join_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Join') and not(@disabled)]"))
                )
                join_btn.click()
                
            except Exception as e:
                print(f"⚠️ Name input not found or not required. Saving screenshot to 'zoom_debug.png'. Error: {e}")
                self.driver.save_screenshot("zoom_debug.png")

            # 3. Handle "Agree" to Terms
            try:
                agree_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Agree') or contains(text(), 'I Agree')]"))
                )
                agree_btn.click()
            except:
                pass
                
            # 4. Handle "Join with Computer Audio"
            try:
                join_audio_btn = WebDriverWait(self.driver, 15).until(
                     EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Join Audio by Computer') or contains(text(), 'Join with Computer Audio')]"))
                )
                join_audio_btn.click()
            except:
                print("⚠️ 'Join Audio' button not found")

            self.is_connected = True
            print("✅ Bot successfully loaded Zoom Web Client.")

            
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
                    "meeting_id": self.meeting_id,
                    "audio_data": base64.b64encode(chunk).decode('utf-8'),
                    "timestamp": time.time()
                }
                r.rpush("meeting_audio_queue", json.dumps(message))
