import json

class MediaController:
    def __init__(self, bot):
        self.bot = bot
        self.page = bot.page

    def disable_initial_media(self):
        """Disable camera and microphone before joining"""
        self.bot._human_delay(1, 2)
        
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
            buttons = self.page.locator('button').all()
            
            for btn in buttons[:10]:
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
        """Try keyboard shortcuts to disable media - cross-platform"""
        try:
            self.page.keyboard.press(f"{self.bot.modifier_key}+e")  # Camera toggle
            self.bot._human_delay(0.3, 0.5)
            self.page.keyboard.press(f"{self.bot.modifier_key}+d")  # Mic toggle
            print("✅ Media toggled via keyboard shortcuts")
            return True
        except:
            return False

    def unmute_microphone(self):
        """Unmute the microphone after joining - cross-platform"""
        print("🎤 Initial microphone unmute...")
        try:
            # Wait for UI to be ready
            self.bot._human_delay(1, 2)
            
            # Check current state (Optional debug)
            try:
                mic_button = self.page.locator('button[aria-label*="microphone" i]').first
                label = mic_button.get_attribute("aria-label") or ""
                print(f"🎤 Current mic state: {label}")
            except:
                pass
            
            # Toggle microphone - works on Mac, Windows, and Linux
            self.page.keyboard.press(f"{self.bot.modifier_key}+d")
            self.bot._human_delay(1, 1.5)
            
            # Verify new state
            try:
                mic_button = self.page.locator('button[aria-label*="microphone" i]').first
                new_label = mic_button.get_attribute("aria-label") or ""
                print(f"✅ Mic toggled. New state: {new_label}")
            except:
                print("✅ Microphone toggle command sent")
                
        except Exception as e:
            print(f"⚠️ Failed to unmute: {e}")

    def ensure_unmuted(self):
        """Verifies microphone status and unmutes if necessary before speaking - cross-platform"""
        try:
            # Wait for the meeting UI to stabilize
            self.bot._human_delay(2, 3)
            
            # Multiple strategies to check and unmute
            unmuted = False
            
            # Strategy 1: Check aria-label for mute status
            try:
                mic_button = self.page.locator('button[aria-label*="microphone" i]').first
                if mic_button.is_visible(timeout=3000):
                    label = mic_button.get_attribute("aria-label") or ""
                    # print(f"🎤 Microphone button label: {label}")
                    
                    # If label contains "Turn on" or "unmute", bot is muted
                    if "turn on" in label.lower() or "unmute" in label.lower():
                        print("🎤 Bot is muted. Unmuting now...")
                        self.page.keyboard.press(f"{self.bot.modifier_key}+d")
                        self.bot._human_delay(1, 2)
                        unmuted = True
                    else:
                        # print("✅ Bot appears to be unmuted (via label check)")
                        unmuted = True
            except Exception as e:
                print(f"⚠️ Strategy 1 failed: {e}")
            
            # Strategy 2: Look for visual mute indicators
            if not unmuted:
                try:
                    # Check for muted icon or indicator
                    muted_indicator = self.page.locator('[data-is-muted="true"]').first
                    if muted_indicator.is_visible(timeout=2000):
                        print("🎤 Muted indicator found. Unmuting...")
                        self.page.keyboard.press(f"{self.bot.modifier_key}+d")
                        self.bot._human_delay(1, 2)
                        unmuted = True
                except:
                    pass
            
            # Strategy 3: Just toggle with keyboard shortcut to be safe
            if not unmuted:
                print("🎤 Forcing unmute with keyboard shortcut...")
                # Press twice to ensure we end up unmuted (toggle off then on if needed)
                self.page.keyboard.press(f"{self.bot.modifier_key}+d")
                self.bot._human_delay(0.5, 1)
                
                # Check the state after toggle
                try:
                    mic_button = self.page.locator('button[aria-label*="microphone" i]').first
                    label = mic_button.get_attribute("aria-label") or ""
                    
                    # If still showing "turn on", press again
                    if "turn on" in label.lower():
                        print("🎤 Still muted after first toggle, pressing again...")
                        self.page.keyboard.press(f"{self.bot.modifier_key}+d")
                        self.bot._human_delay(0.5, 1)
                except:
                    pass
                
                print("✅ Unmute command sent")
            
            # Final verification checks
            self.bot._human_delay(1, 1.5)
            # (We could raise warning here if still muted, but we proceed)

        except Exception as e:
            print(f"❌ Error in unmute process: {e}")

    def announce_presence(self):
        """Triggers the bot's initial voice introduction"""
        print("📣 Preparing presence announcement...")
        
        # CRITICAL: Wait for meeting UI to fully stabilize
        self.bot._human_delay(3, 5)
        
        # Ensure unmuted BEFORE queuing speech
        self.ensure_unmuted()
        
        # Additional delay to ensure unmute took effect
        self.bot._human_delay(1, 2)
        
        announcement = (
            "Hello everyone, I am the AI Meeting Assistant. "
            "I have joined to record and transcribe this meeting to generate specifications. "
            "Recording is now active."
        )
        
        msg = {
            "meeting_id": self.bot.meeting_id,
            "text": announcement
        }
        self.bot.redis_client.rpush("speak_request_queue", json.dumps(msg))
        print(f"📣 Presence announcement queued for Meeting {self.bot.meeting_id}")
