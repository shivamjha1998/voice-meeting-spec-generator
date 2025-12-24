import json
from backend.bot.common.base import BaseBot
from backend.bot.recorder import AudioRecorder

class ZoomBot(BaseBot):
    def __init__(self, meeting_id=1):
        super().__init__(meeting_id, profile_dir="google_profile")
        # Override recorder to keep zoom_ filename convention if desired
        self.recorder = AudioRecorder(filename=f"zoom_{meeting_id}.wav")

    def join_meeting(self, meeting_url: str):
        """
        Joins a Zoom meeting using Playwright.
        """
        print(f"🤖 Bot (Playwright) joining: {meeting_url}")
        
        # Convert to Web Client URL if needed
        if "/j/" in meeting_url:
            meeting_url = meeting_url.replace("/j/", "/wc/join/")
        
        # 1. Start Browser (handled by BaseBot)
        self._start_browser()
        
        try:
            self.page.goto(meeting_url)
            self._human_delay(2, 4)
            
            # 1. Handle Cookie/Privacy Popups
            try:
                self.page.get_by_role("button", name="Agree").click(timeout=3000)
                self._human_delay(0.5, 1.5)
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
                                 inputs.nth(i).fill("AI Meeting Assistant")
                                 print("✅ Filled name via generic input fallback")
                                 name_filled = True
                                 break
                 except:
                     pass

            self._human_delay(1, 2)

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

            self._announce_presence()

        except Exception as e:
            print(f"❌ Failed to join: {e}")
            self.leave_meeting()

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
        # Push to the TTS queue (redis_client provided by BaseBot)
        self.redis_client.rpush("speak_request_queue", json.dumps(msg))
        print(f"📣 Presence announcement queued for Meeting {self.meeting_id}")
