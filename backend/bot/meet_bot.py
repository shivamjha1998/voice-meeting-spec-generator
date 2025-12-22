import time
import threading
import os
import redis
import json
import base64
import random
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
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
        """Simulates human-like waiting."""
        time.sleep(random.uniform(min_sec, max_sec))

    def join_meeting(self, meeting_url: str):
        print(f"🤖 Bot starting with persistent profile: {self.user_data_dir}")
        
        self.playwright = sync_playwright().start()
        
        # Launch with persistent context to avoid being flagged as a 'fresh' bot
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=False, # Use False + Xvfb on servers
            args=[
                "--use-fake-ui-for-media-stream", 
                "--use-fake-device-for-media-stream", # Spoofs a physical camera/mic
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
                "--window-position=0,0",
                "--window-size=1280,720",
            ],
            ignore_default_args=["--enable-automation"],
            permissions=["microphone", "camera"],
            viewport={"width": 1280, "height": 720}
        )
        
        self.page = self.context.pages[0]
        stealth_sync(self.page) # Apply advanced evasion

        try:
            self.page.goto(meeting_url, wait_until="networkidle")
            self._human_delay(2, 4)

            # 1. Handle Mic/Camera Muting (Keyboard shortcuts are most reliable)
            try:
                self.page.keyboard.press("Control+d") 
                self._human_delay(0.5, 1)
                self.page.keyboard.press("Control+e")
                print("✅ Mic and Camera muted via shortcuts.")
            except Exception as e:
                print(f"⚠️ Mute shortcuts failed: {e}")

            # 2. Handle Name Input (Only if not logged in)
            try:
                name_field = self.page.locator("input[aria-label='Your name'], input[placeholder='Your name']")
                if name_field.is_visible(timeout=3000):
                    name_field.fill("AI Assistant")
                    self._human_delay(1, 2)
                    print("✅ Entered display name.")
            except:
                print("ℹ️ Skipping name input (perhaps already logged in).")

            # 3. Join Logic
            # Google Meet uses different buttons: 'Join now', 'Ask to join', or 'Rejoin'
            join_selectors = [
                "button:has-text('Join now')",
                "button:has-text('Ask to join')",
                "button:has-text('Rejoin')"
            ]
            
            joined = False
            for selector in join_selectors:
                btn = self.page.locator(selector)
                if btn.is_visible(timeout=5000):
                    btn.click()
                    print(f"✅ Clicked: {selector}")
                    joined = True
                    break
            
            if not joined:
                # Backup: click the first primary button that looks like a join button
                self.page.locator("button[jsname='Q67bS']").click(timeout=5000)
                print("✅ Clicked primary action button (backup).")

            # 4. Verify Entry & Anti-Idle Loop
            self.page.wait_for_selector('button[aria-label*="Leave call"]', timeout=45000)
            self.is_connected = True
            print("✅ Successfully inside the meeting.")
            
            # Start background maintenance thread
            threading.Thread(target=self._maintain_presence, daemon=True).start()

        except Exception as e:
            print(f"❌ Critical Join Error: {e}")
            self.page.screenshot(path="error_state.png")
            self.leave_meeting()

    def _maintain_presence(self):
        """Prevents the bot from being kicked for inactivity/idleness."""
        while self.is_connected:
            try:
                # Randomly move the mouse to simulate activity
                x, y = random.randint(100, 500), random.randint(100, 500)
                self.page.mouse.move(x, y)
                
                # Close any "Are you still there?" popups if they appear
                popup_btn = self.page.locator("button:has-text('OK'), button:has-text('Yes')")
                if popup_btn.is_visible(timeout=500):
                    popup_btn.click()
                    print("🔘 Dismissed an idle popup.")
                
                time.sleep(random.randint(30, 60))
            except:
                break

    def start_audio_stream(self):
        if not self.is_connected:
            print("⚠️ Cannot start audio: Not connected.")
            return
            
        print("🎙️ Starting audio capture...")
        self.recorder.start_recording()
        threading.Thread(target=self._consume_stream, daemon=True).start()

    def _consume_stream(self):
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        for chunk in self.recorder.stream_audio():
            if not self.is_connected: break
            if chunk:
                msg = {
                    "meeting_id": self.meeting_id,
                    "audio_data": base64.b64encode(chunk).decode('utf-8'),
                    "timestamp": time.time()
                }
                r.rpush("meeting_audio_queue", json.dumps(msg))

    def leave_meeting(self):
        print("👋 Cleaning up and leaving...")
        self.is_connected = False
        try: self.recorder.stop_recording()
        except: pass
            
        if self.context:
            self.context.close()
        if self.playwright:
            self.playwright.stop()
        print("🛑 Shutdown Complete.")