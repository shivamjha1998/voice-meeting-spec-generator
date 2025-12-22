import time
import threading
import os
import redis
import json
import base64
from playwright.sync_api import sync_playwright
from backend.bot.recorder import AudioRecorder

class ZoomBot:
    def __init__(self, meeting_id=1):
        self.meeting_id = meeting_id
        self.browser = None
        self.context = None
        self.page = None
        self.is_connected = False
        self.recorder = AudioRecorder(filename=f"zoom_{meeting_id}.wav")
        self.redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

    def join_meeting(self, meeting_url: str):
        """
        Joins a Zoom meeting using Playwright.
        """
        print(f"🤖 Bot (Playwright) joining: {meeting_url}")
        
        # Convert to Web Client URL if needed
        if "/j/" in meeting_url:
            meeting_url = meeting_url.replace("/j/", "/wc/join/")
        
        self.playwright = sync_playwright().start()
        
        # Launch Browser (Chromium)
        # We run 'headed' because we have Xvfb. This avoids detection better than headless.
        self.browser = self.playwright.chromium.launch(
            headless=False, 
            args=[
                "--use-fake-ui-for-media-stream",  # Auto-allow Mic/Cam
                "--autoplay-policy=no-user-gesture-required"
            ]
        )
        
        # Create Context with Permissions
        self.context = self.browser.new_context(
            permissions=["microphone"],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        self.page = self.context.new_page()
        
        try:
            self.page.goto(meeting_url)
            
            # 1. Handle Cookie/Privacy Popups
            try:
                self.page.get_by_role("button", name="Agree").click(timeout=3000)
            except:
                pass

            # 2. Enter Name
            # Playwright selectors are robust. We look for the placeholder.
            name_input = self.page.get_by_placeholder("Your Name")
            if name_input.count() > 0:
                name_input.fill("AI Assistant")
                # Click Join
                self.page.get_by_role("button", name="Join").click()

            # 3. Handle 'Join Audio by Computer'
            # Zoom often shows a preview; we wait for the Join Audio button
            join_audio_btn = self.page.locator("button:has-text('Join Audio by Computer')")
            try:
                join_audio_btn.wait_for(timeout=15000)
                join_audio_btn.click()
                print("✅ Clicked 'Join Audio by Computer'")
            except:
                print("⚠️ 'Join Audio' button not found (might be auto-joined)")

            self.is_connected = True
            print("✅ Bot Successfully Connected to Zoom")

        except Exception as e:
            print(f"❌ Failed to join: {e}")
            # Take a screenshot for debugging in Docker
            self.page.screenshot(path="error_screenshot.png")
            self.leave_meeting()

    def start_audio_stream(self):
        """Starts capturing system audio."""
        if not self.is_connected:
            return
            
        print("🎙️ Bot listening...")
        self.recorder.start_recording()
        
        # Start streaming thread
        threading.Thread(target=self._consume_stream, daemon=True).start()

    def leave_meeting(self):
        self.is_connected = False
        try:
            self.recorder.stop_recording()
        except:
            pass
            
        if self.browser:
            self.browser.close()
        if hasattr(self, 'playwright'):
            self.playwright.stop()
        print("👋 Bot disconnected.")

    def _consume_stream(self):
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        
        for chunk in self.recorder.stream_audio():
            if chunk:
                msg = {
                    "meeting_id": self.meeting_id,
                    "audio_data": base64.b64encode(chunk).decode('utf-8'),
                    "timestamp": time.time()
                }
                r.rpush("meeting_audio_queue", json.dumps(msg))
