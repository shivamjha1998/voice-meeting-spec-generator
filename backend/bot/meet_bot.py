import time
import threading
import os
import redis
import json
import base64
import random
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth as stealth_sync # 'stealth' is exposed in this version, aliasing to 'stealth_sync'
from backend.bot.recorder import AudioRecorder

class GoogleMeetBot:
    def __init__(self, meeting_id=1):
        self.meeting_id = meeting_id
        self.playwright = None
        self.context = None
        self.page = None
        self.is_connected = False
        self.recorder = AudioRecorder(filename=f"meet_{meeting_id}.wav")
        self.redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        # Path for browser profile to persist login/cookies
        self.user_data_dir = os.path.join(os.getcwd(), "google_profile")

    def _human_delay(self, min_sec=1, max_sec=3):
        time.sleep(random.uniform(min_sec, max_sec))

    def join_meeting(self, meeting_url: str):
        print(f"🤖 Bot starting with profile: {self.user_data_dir}")
        self.playwright = sync_playwright().start()
        
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=False,
            user_agent=user_agent,
            args=[
                "--use-fake-ui-for-media-stream",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
                "--mute-audio=false",
            ],
            ignore_default_args=["--enable-automation"],
            permissions=["microphone", "camera"],
            viewport={"width": 1280, "height": 720}
        )
        
        self.page = self.context.pages[0]
        
        # 1. Apply Stealth Corrected
        try:
            stealth_sync(self.page)
        except Exception as e:
            print(f"⚠️ Stealth error: {e}")

        try:
            self.page.goto(meeting_url, wait_until="networkidle")
            self._human_delay(5, 8) # Give extra time for hardware checks

            # 2. Mute Media
            try:
                self.page.keyboard.press("Control+d") 
                self._human_delay(0.5, 1)
                self.page.keyboard.press("Control+e")
                print("✅ Media muted via shortcuts.")
            except: pass

            # 3. Handle Name Entry (FORCE CHECK)
            # If the join button is disabled, it's usually because the name is empty.
            name_selectors = ["input[aria-label='Your name']", "input[placeholder='Your name']"]
            for sel in name_selectors:
                name_field = self.page.locator(sel)
                if name_field.is_visible(timeout=3000):
                    name_field.fill("AI Assistant")
                    self._human_delay(1, 2)
                    print(f"✅ Filled name field found via: {sel}")

            # 4. Join Logic with "Wait for Enabled"
            join_selectors = [
                "button:has-text('Join now')",
                "button:has-text('Ask to join')",
                "button:has-text('Rejoin')",
                "[jsname='Q67bS']"
            ]
            
            joined = False
            for selector in join_selectors:
                btn = self.page.locator(selector)
                if btn.is_visible(timeout=5000):
                    print(f"⌛ Found {selector}, waiting for it to be enabled...")
                    try:
                        # Wait specifically for the button to not be disabled
                        btn.wait_for(state="visible", timeout=10000)
                        # Attempt to click even if Playwright thinks it's disabled 
                        # using force=True if it hangs, but usually waiting is better
                        btn.click(timeout=10000)
                        print(f"✅ Clicked: {selector}")
                        joined = True
                        break
                    except Exception as click_err:
                        print(f"⚠️ Could not click {selector}: {click_err}")
            
            if not joined:
                raise Exception("Join button was found but remained disabled or non-clickable.")

            # 5. Verify Entry
            self.page.wait_for_selector('button[aria-label*="Leave call"]', timeout=30000)
            self.is_connected = True
            print("✅ Successfully inside the meeting.")
            threading.Thread(target=self._maintain_presence, daemon=True).start()

        except Exception as e:
            print(f"❌ Join Error: {e}")
            self.page.screenshot(path="error_debug.png")
            self.leave_meeting()

    def _maintain_presence(self):
        while self.is_connected:
            try:
                self.page.mouse.move(random.randint(100, 500), random.randint(100, 500), steps=5)
                time.sleep(random.randint(30, 60))
            except: break

    def start_audio_stream(self):
        if self.is_connected:
            self.recorder.start_recording()
            threading.Thread(target=self._consume_stream, daemon=True).start()

    def _consume_stream(self):
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        for chunk in self.recorder.stream_audio():
            if not self.is_connected: break
            if chunk:
                msg = {"meeting_id": self.meeting_id, "audio_data": base64.b64encode(chunk).decode('utf-8'), "timestamp": time.time()}
                r.rpush("meeting_audio_queue", json.dumps(msg))

    def leave_meeting(self):
        self.is_connected = False
        try: self.recorder.stop_recording()
        except: pass
        if self.context: self.context.close()
        if self.playwright: self.playwright.stop()
        print("🛑 Shutdown Complete.")