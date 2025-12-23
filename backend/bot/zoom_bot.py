import time
import threading
import os
import redis
import json
import base64
from playwright.sync_api import sync_playwright
# Fix stealth import - handle both import styles
try:
    from playwright_stealth import stealth_sync
except ImportError:
    stealth_sync = None
    print("⚠️ playwright-stealth not available")

from backend.bot.recorder import AudioRecorder

class ZoomBot:
    def __init__(self, meeting_id=1):
        self.meeting_id = meeting_id
        self.playwright = None # Changed from browser to playwright for consistency
        self.context = None
        self.page = None
        self.is_connected = False
        self.recorder = AudioRecorder(filename=f"zoom_{meeting_id}.wav")
        self.redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        self.user_data_dir = os.path.join(os.getcwd(), "google_profile")

    def join_meeting(self, meeting_url: str):
        """
        Joins a Zoom meeting using Playwright.
        """
        print(f"🤖 Bot (Playwright) joining: {meeting_url}")
        
        # Convert to Web Client URL if needed
        if "/j/" in meeting_url:
            meeting_url = meeting_url.replace("/j/", "/wc/join/")
        
        self.playwright = sync_playwright().start()
        
        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

        # Launch Browser (Chromium) with Persistent Context
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=False,
            user_agent=user_agent,
            args=[
                "--use-fake-ui-for-media-stream",
                "--no-sandbox",
                "--disable-infobars",
                "--disable-blink-features=AutomationControlled",
                "--autoplay-policy=no-user-gesture-required"
            ],
            ignore_default_args=["--enable-automation"],
            permissions=["microphone", "camera"],
            viewport={"width": 1280, "height": 720}
        )
        
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()

        # Apply stealth if available
        if stealth_sync:
            try:
                stealth_sync(self.page)
                print("✅ Stealth applied successfully")
            except Exception as e:
                print(f"⚠️ Stealth error (non-critical): {e}")

        # Override webdriver property
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        try:
            self.page.goto(meeting_url)
            
            # 1. Handle Cookie/Privacy Popups
            try:
                self.page.get_by_role("button", name="Agree").click(timeout=3000)
            except:
                pass

            # 2. Enter Name
            # Try multiple selectors for the name field
            print("📝 Filling name field...")
            name_filled = False
            name_patterns = ["Your Name", "Enter your name", "Name", "inputname"]
            
            for pattern in name_patterns:
                try:
                    # Try placeholder
                    inp = self.page.get_by_placeholder(pattern)
                    if inp.count() > 0 and inp.is_visible():
                        inp.fill("AI Assistant")
                        name_filled = True
                        print(f"✅ Filled name via placeholder: {pattern}")
                        break
                    
                    # Try label
                    inp = self.page.get_by_label(pattern)
                    if inp.count() > 0 and inp.is_visible():
                        inp.fill("AI Assistant")
                        name_filled = True
                        print(f"✅ Filled name via label: {pattern}")
                        break
                        
                    # Try ID
                    inp = self.page.locator(f"#{pattern}")
                    if inp.count() > 0 and inp.is_visible():
                        inp.fill("AI Assistant")
                        name_filled = True
                        print(f"✅ Filled name via ID: {pattern}")
                        break
                except:
                    pass
            
            if not name_filled:
                 # Fallback: try generic input if only one exists or looks right
                 try:
                     inputs = self.page.locator("input[type='text']")
                     if inputs.count() > 0:
                         for i in range(inputs.count()):
                             if inputs.nth(i).is_visible():
                                 inputs.nth(i).fill("AI Assistant")
                                 print("✅ Filled name via generic input fallback")
                                 name_filled = True
                                 break
                 except:
                     pass

            # Click Join Button
            join_btn = self.page.get_by_role("button", name="Join")
            if join_btn.count() > 0 and join_btn.is_visible():
                join_btn.click()
                print("✅ Clicked 'Join' button")
            else:
                # Fallback for Join button
                try:
                    self.page.locator("button.preview-join-button").click()
                    print("✅ Clicked 'Join' button via class")
                except:
                    print("⚠️ Join button not found")

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
            
        if self.context:
            self.context.close()
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
