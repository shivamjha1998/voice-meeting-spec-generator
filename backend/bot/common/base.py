import os
import time
import random
import platform
import redis
import json
import base64
import threading
from abc import ABC, abstractmethod
from playwright.sync_api import sync_playwright
try:
    from playwright_stealth import stealth_sync
except ImportError:
    stealth_sync = None
    print("⚠️ playwright-stealth not available")

from backend.bot.recorder import AudioRecorder

class BaseBot(ABC):
    def __init__(self, meeting_id=1, profile_dir="google_profile"):
        self.meeting_id = meeting_id
        self.playwright = None
        self.context = None
        self.page = None
        self.is_connected = False
        self.user_data_dir = os.path.join(os.getcwd(), profile_dir)
        
        # Audio & Redis
        # Detect platform for recorder filename or other specifics if needed
        # Derived bots might override filename
        self.recorder = AudioRecorder(filename=f"meeting_{meeting_id}.wav") 
        self.redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        
        # OS Detection
        system = platform.system()
        if system == "Darwin":  # macOS
            self.modifier_key = "Meta"
            print("🍎 Detected macOS - using Command key")
        else:  # Windows or Linux
            self.modifier_key = "Control"
            print(f"🖥️ Detected {system} - using Control key")

    def _human_delay(self, min_sec=1, max_sec=3):
        """Add random human-like delays"""
        time.sleep(random.uniform(min_sec, max_sec))

    def _start_browser(self, headless=False):
        """Initializes Playwright, Context, and Page with Stealth"""
        print(f"🤖 Bot starting with profile: {self.user_data_dir}")
        self.playwright = sync_playwright().start()
        
        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=headless,
            user_agent=user_agent,
            args=[
                "--use-fake-ui-for-media-stream",
                "--disable-dev-shm-usage",
                "--disable-infobars",
                "--disable-blink-features=AutomationControlled",
                "--autoplay-policy=no-user-gesture-required"
            ],
            ignore_default_args=["--enable-automation"], 
            permissions=["microphone", "camera"],
            viewport={"width": 1280, "height": 720},
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

    @abstractmethod
    def join_meeting(self, meeting_url: str):
        """Abstract method to be implemented by specific bots"""
        pass

    @abstractmethod
    def mute_microphone(self):
        """Mute the microphone"""
        pass

    @abstractmethod
    def unmute_microphone(self):
        """Unmute the microphone"""
        pass

    def start_audio_stream(self):
        """Start recording and streaming audio from the meeting"""
        if self.is_connected:
            try:
                self.recorder.start_recording()
                threading.Thread(target=self._consume_stream, daemon=True).start()
            except Exception as e:
                print(f"❌ Failed to start audio recording: {e}")

    def _consume_stream(self):
        """Consume audio chunks and push to Redis queue"""
        # Create a new redis connection for the thread
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        for chunk in self.recorder.stream_audio():
            if not self.is_connected:
                break
            if chunk:
                msg = {
                    "meeting_id": self.meeting_id,
                    "audio_data": base64.b64encode(chunk).decode('utf-8'),
                    "timestamp": time.time()
                }
                r.rpush("meeting_audio_queue", json.dumps(msg))

    def perform_maintenance(self):
        """Called periodically by the main thread to keep the bot active"""
        if not self.is_connected:
            return

        try:
            current_time = time.time()
            if not hasattr(self, '_last_mouse_move'):
                self._last_mouse_move = 0
            
            if current_time - self._last_mouse_move > 45: 
                x = random.randint(200, 800)
                y = random.randint(200, 600)
                try:
                    self.page.mouse.move(x, y)
                except:
                    pass
                
                # Check specifics in subclasses if needed, or keep generic here
                self._last_mouse_move = current_time
        except Exception:
            pass

    def leave_meeting(self):
        """Clean shutdown of the bot and all resources"""
        self.is_connected = False
        
        try:
            self.recorder.close()
        except Exception as e:
            print(f"⚠️ Error stopping recorder: {e}")
        
        try:
            if self.context:
                self.context.close()
        except Exception as e:
            print(f"⚠️ Error closing context: {e}")
        
        try:
            if self.playwright:
                self.playwright.stop()
        except Exception as e:
            print(f"⚠️ Error stopping playwright: {e}")
        
        print("🛑 Shutdown Complete.")
