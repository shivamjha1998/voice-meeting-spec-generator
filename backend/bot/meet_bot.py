import time
import threading
import os
import redis
import json
import base64
import random
from playwright.sync_api import sync_playwright

# Fix stealth import - handle both import styles
try:
    from playwright_stealth import stealth_sync
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
        self.playback_thread_started = False

    def _human_delay(self, min_sec=1, max_sec=3):
        time.sleep(random.uniform(min_sec, max_sec))


    def join_meeting(self, meeting_url: str):
        print(f"🤖 Bot starting with profile: {self.user_data_dir}")
        self.playwright = sync_playwright().start()
        
        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

        # Inside meet_bot.py
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=False,
            user_agent=user_agent,
            args=[
                "--use-fake-ui-for-media-stream",
                "--no-sandbox",
                "--disable-infobars",
                "--disable-blink-features=AutomationControlled",
            ],
            # This is critical to hide automation
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

        try:
            print(f"🌐 Navigating to: {meeting_url}")
            self.page.goto(meeting_url, wait_until="domcontentloaded", timeout=60000)
            
            # Wait for page to stabilize
            self._human_delay(3, 5)


            # Dismiss any popups/notifications
            self._dismiss_popups()

            # Turn off camera and microphone FIRST
            print("🔇 Disabling camera and microphone...")
            self._disable_media_devices()
            self._human_delay(1, 2)

            # Fill in name field
            print("📝 Filling name field...")
            self._fill_name_field()
            
            self._human_delay(2, 3)


            # Try to join meeting
            print("🚪 Attempting to join meeting...")
            join_success = self._attempt_join()
            
            if not join_success:

                raise Exception("Could not join the meeting - button not clickable or meeting restricted")

            # Wait and verify we're in the meeting
            print("⌛ Waiting for meeting interface...")
            if self._verify_meeting_joined():
                self.is_connected = True
                self._announce_presence()
                print("✅ Successfully joined the meeting!")
            else:
                raise Exception("Could not verify successful meeting entry")

        except Exception as e:
            print(f"❌ Join Error: {e}")
            
            self.leave_meeting()
            raise e

    def _dismiss_popups(self):
        """Dismiss any popups or permission requests"""
        dismiss_patterns = [
            "Got it", "Dismiss", "No thanks", "Not now", "Close", "OK"
        ]
        
        for pattern in dismiss_patterns:
            try:
                buttons = self.page.get_by_role("button", name=pattern)
                count = buttons.count()
                for i in range(count):
                    try:
                        if buttons.nth(i).is_visible(timeout=1000):
                            buttons.nth(i).click(timeout=2000)
                            print(f"✅ Dismissed popup: {pattern}")
                            self._human_delay(0.5, 1)
                    except:
                        pass
            except:
                pass

    def _disable_media_devices(self):
        """Disable camera and microphone before joining"""
        # Strategy: Click the toggle buttons in the pre-join screen
        # Google Meet typically shows camera/mic buttons before joining
        
        # Wait a bit for controls to appear
        self._human_delay(1, 2)
        
        # Try multiple strategies to disable media
        strategies = [
            self._disable_via_aria_labels,
            self._disable_via_visual_search,
            self._disable_via_keyboard
        ]
        
        for strategy in strategies:
            try:
                if strategy():
                    return
            except Exception as e:
                print(f"⚠️ Strategy failed: {e}")
        
        print("⚠️ Could not confirm media disabled, but continuing...")

    def _disable_via_aria_labels(self):
        """Try to disable via aria labels"""
        success = False
        
        # Camera patterns
        cam_patterns = ["Turn off camera", "camera", "cam"]
        for pattern in cam_patterns:
            try:
                btn = self.page.get_by_role("button", name=pattern).first
                if btn.is_visible(timeout=2000):
                    btn.click(timeout=2000)
                    print(f"✅ Camera disabled via '{pattern}'")
                    success = True
                    break
            except:
                pass
        
        # Microphone patterns  
        mic_patterns = ["Turn off microphone", "microphone", "mic", "mute"]
        for pattern in mic_patterns:
            try:
                btn = self.page.get_by_role("button", name=pattern).first
                if btn.is_visible(timeout=2000):
                    btn.click(timeout=2000)
                    print(f"✅ Microphone disabled via '{pattern}'")
                    success = True
                    break
            except:
                pass
        
        return success

    def _disable_via_visual_search(self):
        """Try to find and click media buttons visually"""
        try:
            # Look for SVG icons that typically represent camera/mic
            buttons = self.page.locator('button').all()
            
            for btn in buttons[:10]:  # Only check first 10 buttons
                try:
                    if btn.is_visible():
                        aria_label = btn.get_attribute('aria-label') or ''
                        if any(word in aria_label.lower() for word in ['camera', 'microphone', 'video', 'audio']):
                            btn.click(timeout=1000)
                            print(f"✅ Clicked media button: {aria_label}")
                except:
                    pass
            
            return True
        except:
            return False

    def _disable_via_keyboard(self):
        """Try keyboard shortcuts to disable media"""
        try:
            # Google Meet shortcuts
            self.page.keyboard.press("Control+e")  # Toggle camera
            self._human_delay(0.3, 0.5)
            self.page.keyboard.press("Control+d")  # Toggle mic
            print("✅ Media toggled via keyboard shortcuts")
            return True
        except:
            return False

    def _fill_name_field(self):
        """Fill the name field if present"""
        name_patterns = ["Your name", "name", "Name"]
        
        for pattern in name_patterns:
            try:
                field = self.page.get_by_placeholder(pattern).first
                if field.is_visible(timeout=3000):
                    field.click()
                    self._human_delay(0.3, 0.5)
                    field.fill("Meet")
                    print(f"✅ Name filled via placeholder: {pattern}")
                    return True
            except:
                pass
        
        # Try via aria-label
        for pattern in name_patterns:
            try:
                field = self.page.get_by_label(pattern).first
                if field.is_visible(timeout=3000):
                    field.click()
                    self._human_delay(0.3, 0.5)
                    field.fill("AI Assistant")
                    print(f"✅ Name filled via label: {pattern}")
                    return True
            except:
                pass
        
        # Fallback: Try any text input
        try:
            inputs = self.page.locator('input[type="text"]').all()
            if inputs:
                inputs[0].click()
                self._human_delay(0.3, 0.5)
                inputs[0].fill("AI Assistant")
                print("✅ Name filled via first text input")
                return True
        except:
            pass
        
        print("⚠️ Could not find name field (may not be required)")
        return False

    def _attempt_join(self):
        """Try multiple strategies to join the meeting"""
        # Wait a bit for join button to appear
        self._human_delay(2, 3)
        
        # Strategy 1: Look for "Ask to join" or "Join now" buttons
        join_patterns = ["Ask to join", "Join now", "Join", "Ask"]
        
        for pattern in join_patterns:
            try:
                button = self.page.get_by_role("button", name=pattern).first
                if button.is_visible(timeout=5000):
                    print(f"🔍 Found button: {pattern}")
                    
                    # Check if disabled
                    is_disabled = button.evaluate("btn => btn.disabled || btn.getAttribute('aria-disabled') === 'true'")
                    
                    if is_disabled:
                        print(f"⚠️ Button '{pattern}' is disabled, waiting...")
                        self._human_delay(2, 3)
                        # Try again
                        is_disabled = button.evaluate("btn => btn.disabled || btn.getAttribute('aria-disabled') === 'true'")
                    
                    if not is_disabled:
                        button.click(timeout=5000)
                        print(f"✅ Clicked: {pattern}")
                        return True
                    else:
                        # Force click anyway
                        print(f"⚠️ Force clicking disabled button...")
                        button.evaluate("btn => btn.click()")
                        return True
            except Exception as e:
                print(f"⚠️ Could not click '{pattern}': {str(e)[:100]}")
        
        # Strategy 2: Look for any button with "join" in the text
        try:
            buttons = self.page.locator('button').all()
            for btn in buttons:
                try:
                    text = btn.inner_text(timeout=500).lower()
                    if 'join' in text or 'ask' in text:
                        print(f"🔍 Found button with text: {text}")
                        btn.click(timeout=2000)
                        print(f"✅ Clicked button")
                        return True
                except:
                    pass
        except:
            pass
        
        return False

    def _verify_meeting_joined(self):
        """Verify that we successfully joined the meeting"""
        # Wait a bit for the meeting interface to load
        self._human_delay(5, 7)
        
        # Look for indicators that we're in a meeting
        indicators = [
            ('button[aria-label*="Leave"]', "Leave button"),
            ('button[aria-label*="leave"]', "leave button"),
            ('[data-call-ended="false"]', "Active call indicator"),
            ('div[jsname="b0t70b"]', "Google Meet main view"),
        ]
        
        for selector, name in indicators:
            try:
                if self.page.locator(selector).is_visible(timeout=3000):
                    print(f"✅ Found {name}")
                    return True
            except:
                pass
        
        # Check page content for signs we were rejected
        try:
            content = self.page.content().lower()
            rejection_phrases = [
                "can't join this video call",
                "you can't join this call",
                "meeting ended",
                "not allowed",
                "denied"
            ]
            
            for phrase in rejection_phrases:
                if phrase in content:
                    print(f"❌ Detected rejection: '{phrase}'")
                    return False
        except:
            pass
        
        # Last check: see if URL changed to meeting room
        try:
            current_url = self.page.url
            if '/meet/' in current_url or 'meet.google.com' in current_url:
                print(f"✅ URL indicates we're in meeting: {current_url}")
                return True
        except:
            pass
        
        print("⚠️ Could not confirm meeting joined")
        return False

    def perform_maintenance(self):
        """Called periodically by the main thread."""
        if not self.is_connected:
            return

        try:
            current_time = time.time()
            if not hasattr(self, '_last_mouse_move'):
                self._last_mouse_move = 0
            
            if current_time - self._last_mouse_move > 45: 
                x = random.randint(200, 800)
                y = random.randint(200, 600)
                self.page.mouse.move(x, y)
                
                # Check if kicked
                try:
                    if not self.page.locator('button[aria-label*="Leave"]').is_visible(timeout=1000):
                        print("⚠️ Leave button not found - may have been kicked")
                        self.is_connected = False
                except:
                    pass

                self._last_mouse_move = current_time
        except Exception:
            pass

    def start_audio_stream(self):
        if self.is_connected:
            try:
                self.recorder.start_recording()
                threading.Thread(target=self._consume_stream, daemon=True).start()
            except Exception as e:
                print(f"❌ Failed to start audio recording: {e}")

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
        
        # Stop recording
        try:
            self.recorder.stop_recording()
        except Exception as e:
            print(f"⚠️ Error stopping recorder: {e}")
        
        # Close browser
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

    def _announce_presence(self):
        """Triggers the bot's initial voice introduction."""
        announcement = (
            "Hello everyone, I am the AI Meeting Assistant. "
            "I have joined to record and transcribe this meeting to generate specifications. "
            "Recording is now active."
        )
        
        msg = {
            "meeting_id": self.meeting_id,
            "text": announcement
        }
        # Push to the TTS queue
        self.redis_client.rpush("speak_request_queue", json.dumps(msg))
        print(f"📣 Presence announcement queued for Meeting {self.meeting_id}")