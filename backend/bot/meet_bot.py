import time
import threading
import os
import redis
import json
import base64
import random
from playwright.sync_api import sync_playwright, expect

# Fix stealth import
try:
    from playwright_stealth import stealth_sync
except ImportError:
    try:
        from playwright_stealth import stealth
        stealth_sync = stealth
    except ImportError:
        stealth_sync = None
        print("⚠️ playwright-stealth not available")

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
                "--use-fake-device-for-media-stream",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
                "--disable-dev-shm-usage",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
            ignore_default_args=["--enable-automation", "--enable-blink-features=AutomationControlled"],
            permissions=["microphone", "camera"],
            viewport={"width": 1280, "height": 720},
            bypass_csp=True,
        )
        
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        
        # Apply stealth correctly
        if stealth_sync:
            try:
                stealth_sync(self.page)
                print("✅ Stealth applied successfully")
            except Exception as e:
                print(f"⚠️ Stealth error: {e}")
        
        # Override webdriver property
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        try:
            print(f"🌐 Navigating to: {meeting_url}")
            self.page.goto(meeting_url, wait_until="domcontentloaded", timeout=60000)
            
            # Wait for page to stabilize
            self._human_delay(3, 5)
            self.page.screenshot(path="debug_01_landing.png")

            # Dismiss any popups/notifications
            self._dismiss_popups()

            # Turn off camera and microphone FIRST
            print("🔇 Disabling camera and microphone...")
            self._disable_media_devices()
            self._human_delay(1, 2)

            # Fill in name field - THIS IS CRITICAL
            print("📝 Filling name field...")
            name_filled = self._fill_name_field()
            if not name_filled:
                print("⚠️ Could not fill name field - trying alternative method")
                self._fill_name_alternative()
            
            self._human_delay(2, 3)
            self.page.screenshot(path="debug_02_name_filled.png")

            # Now try to join
            print("🚪 Attempting to join meeting...")
            join_success = self._click_join_button()
            
            if not join_success:
                self.page.screenshot(path="debug_03_join_failed.png")
                # Try one more time with force
                print("⚠️ First join attempt failed, trying with force...")
                self._human_delay(2, 3)
                join_success = self._click_join_button(force=True)
            
            if not join_success:
                raise Exception("Could not click join button after multiple attempts")

            # Verify we're in the meeting
            print("⌛ Waiting for meeting interface...")
            self._human_delay(3, 5)
            
            try:
                # Check for various indicators that we're in the meeting
                in_meeting = (
                    self.page.locator('button[aria-label*="Leave"]').is_visible(timeout=15000) or
                    self.page.locator('[data-call-ended="false"]').is_visible(timeout=5000) or
                    self.page.locator('[data-meeting-title]').is_visible(timeout=5000)
                )
                
                if in_meeting:
                    self.is_connected = True
                    print("✅ Successfully joined the meeting!")
                    self.page.screenshot(path="debug_04_success.png")
                    threading.Thread(target=self._maintain_presence, daemon=True).start()
                else:
                    raise Exception("Could not verify meeting entry")
                    
            except Exception as e:
                self.page.screenshot(path="debug_04_timeout.png")
                # Check if we were kicked
                if "can't join this video call" in self.page.content().lower():
                    raise Exception("Bot was blocked/kicked from the meeting")
                raise Exception(f"Timeout waiting for meeting interface: {e}")

        except Exception as e:
            print(f"❌ Join Error: {e}")
            self.page.screenshot(path="error_final.png")
            with open("error_page_content.html", "w", encoding="utf-8") as f:
                f.write(self.page.content())
            self.leave_meeting()
            raise e

    def _dismiss_popups(self):
        """Dismiss any popups or permission requests"""
        try:
            # Dismiss cookie/privacy notices
            dismiss_selectors = [
                "button:has-text('Got it')",
                "button:has-text('Dismiss')",
                "button:has-text('No thanks')",
                "[aria-label='Dismiss']"
            ]
            for selector in dismiss_selectors:
                try:
                    btn = self.page.locator(selector).first
                    if btn.is_visible(timeout=2000):
                        btn.click()
                        self._human_delay(0.5, 1)
                except:
                    pass
        except:
            pass

    def _disable_media_devices(self):
        """Disable camera and microphone before joining"""
        try:
            # Try clicking the camera/mic buttons directly
            cam_selectors = [
                "[aria-label*='camera' i][aria-label*='off' i]",
                "[aria-label*='Turn off camera' i]",
                "button[data-is-muted='false'][aria-label*='camera' i]"
            ]
            
            mic_selectors = [
                "[aria-label*='microphone' i][aria-label*='off' i]",
                "[aria-label*='Turn off microphone' i]",
                "button[data-is-muted='false'][aria-label*='microphone' i]"
            ]
            
            for selector in cam_selectors:
                try:
                    btn = self.page.locator(selector).first
                    if btn.is_visible(timeout=2000):
                        btn.click()
                        print("✅ Camera disabled")
                        break
                except:
                    pass
            
            for selector in mic_selectors:
                try:
                    btn = self.page.locator(selector).first
                    if btn.is_visible(timeout=2000):
                        btn.click()
                        print("✅ Microphone disabled")
                        break
                except:
                    pass
            
            # Also try keyboard shortcuts as backup
            try:
                self.page.keyboard.press("Control+e")  # Toggle camera
                self._human_delay(0.3, 0.5)
                self.page.keyboard.press("Control+d")  # Toggle mic
                print("✅ Media disabled via shortcuts")
            except:
                pass
                
        except Exception as e:
            print(f"⚠️ Could not disable media: {e}")

    def _fill_name_field(self):
        """Fill the name field if present"""
        name_selectors = [
            "input[aria-label='Your name']",
            "input[placeholder='Your name']",
            "input[type='text'][aria-label*='name' i]",
            "input.YPqjbf"  # Google Meet specific class
        ]
        
        for selector in name_selectors:
            try:
                field = self.page.locator(selector).first
                if field.is_visible(timeout=3000):
                    field.click()
                    self._human_delay(0.3, 0.7)
                    field.fill("")  # Clear first
                    self._human_delay(0.2, 0.4)
                    field.type("AI Assistant", delay=random.randint(50, 150))
                    self._human_delay(0.5, 1)
                    print(f"✅ Name filled using selector: {selector}")
                    return True
            except:
                continue
        
        return False

    def _fill_name_alternative(self):
        """Alternative method to fill name using JavaScript"""
        try:
            self.page.evaluate("""
                const inputs = document.querySelectorAll('input[type="text"]');
                for (let input of inputs) {
                    if (input.placeholder?.toLowerCase().includes('name') || 
                        input.ariaLabel?.toLowerCase().includes('name')) {
                        input.value = 'AI Assistant';
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                        return true;
                    }
                }
                return false;
            """)
            print("✅ Name filled using JavaScript")
        except Exception as e:
            print(f"⚠️ Alternative name fill failed: {e}")

    def _click_join_button(self, force=False):
        """Try to click the join button"""
        join_selectors = [
            "button:has-text('Join now')",
            "button:has-text('Ask to join')",
            "button span:has-text('Join now')",
            "button span:has-text('Ask to join')",
            "[jsname='Qx7uuf']",  # Google Meet specific
            "button.VfPpkd-LgbsSe[jsname='Qx7uuf']"
        ]
        
        for selector in join_selectors:
            try:
                btn = self.page.locator(selector).first
                
                # Check if button exists and is visible
                if not btn.is_visible(timeout=5000):
                    continue
                
                print(f"🔍 Found join button: {selector}")
                
                # Wait a bit more for button to be enabled
                self._human_delay(1, 2)
                
                # Check if button is disabled via aria or attribute
                is_disabled = btn.evaluate("el => el.disabled || el.ariaDisabled === 'true'")
                
                if is_disabled and not force:
                    print(f"⚠️ Button is disabled, waiting...")
                    self._human_delay(2, 3)
                    is_disabled = btn.evaluate("el => el.disabled || el.ariaDisabled === 'true'")
                
                if is_disabled and not force:
                    print(f"⚠️ Button still disabled after wait")
                    continue
                
                # Try to click
                if force:
                    # Force click using JavaScript
                    btn.evaluate("el => el.click()")
                    print(f"✅ Force-clicked: {selector}")
                else:
                    btn.click(timeout=5000)
                    print(f"✅ Clicked: {selector}")
                
                return True
                
            except Exception as e:
                print(f"⚠️ Could not click {selector}: {str(e)[:100]}")
                continue
        
        return False

    def _maintain_presence(self):
        """Maintain presence to avoid being kicked for inactivity"""
        while self.is_connected:
            try:
                # Move mouse occasionally
                x = random.randint(100, 500)
                y = random.randint(100, 500)
                self.page.mouse.move(x, y, steps=random.randint(3, 8))
                
                # Occasionally check if we're still in the meeting
                if not self.page.locator('button[aria-label*="Leave"]').is_visible(timeout=5000):
                    print("⚠️ Detected we're no longer in the meeting")
                    self.is_connected = False
                    break
                
                time.sleep(random.randint(30, 60))
            except:
                break

    def start_audio_stream(self):
        if self.is_connected:
            self.recorder.start_recording()
            threading.Thread(target=self._consume_stream, daemon=True).start()

    def _consume_stream(self):
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

    def leave_meeting(self):
        self.is_connected = False
        try:
            self.recorder.stop_recording()
        except:
            pass
        try:
            if self.context:
                self.context.close()
        except:
            pass
        try:
            if self.playwright:
                self.playwright.stop()
        except:
            pass
        print("🛑 Shutdown Complete.")
