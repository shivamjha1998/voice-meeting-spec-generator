class MeetingJoiner:
    def __init__(self, bot):
        self.bot = bot
        self.page = bot.page
        
    def join_meeting(self):
        """Orchestrates the steps to enter the meeting from the lobby"""
        
        # Dismiss any popups/notifications
        self._dismiss_popups()
        
        # Fill in name field
        print("📝 Filling name field...")
        self._fill_name_field()
        
        self.bot._human_delay(2, 3)

        # Try to click Join
        print("🚪 Attempting to join meeting...")
        join_success = self._attempt_join()
        
        if not join_success:
            raise Exception("Could not join the meeting - button not clickable or meeting restricted")

        # Wait and verify we're in the meeting
        print("⌛ Waiting for meeting interface...")
        if self._verify_meeting_joined():
            return True
        else:
            raise Exception("Could not verify successful meeting entry")

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
                            self.bot._human_delay(0.5, 1)
                    except:
                        pass
            except:
                pass

    def _fill_name_field(self):
        """Fill the name field if present"""
        name_patterns = ["Your name", "name", "Name"]
        
        for pattern in name_patterns:
            try:
                field = self.page.get_by_placeholder(pattern).first
                if field.is_visible(timeout=3000):
                    field.click()
                    self.bot._human_delay(0.3, 0.5)
                    field.fill("AI Meeting Assistant")
                    print(f"✅ Name filled via placeholder: {pattern}")
                    return True
            except:
                pass
        
        for pattern in name_patterns:
            try:
                field = self.page.get_by_label(pattern).first
                if field.is_visible(timeout=3000):
                    field.click()
                    self.bot._human_delay(0.3, 0.5)
                    field.fill("AI Meeting Assistant")
                    print(f"✅ Name filled via label: {pattern}")
                    return True
            except:
                pass
        
        try:
            inputs = self.page.locator('input[type="text"]').all()
            if inputs:
                inputs[0].click()
                self.bot._human_delay(0.3, 0.5)
                inputs[0].fill("AI Meeting Assistant")
                print("✅ Name filled via first text input")
                return True
        except:
            pass
        
        print("⚠️ Could not find name field (may not be required)")
        return False

    def _attempt_join(self):
        """Try multiple strategies to join the meeting"""
        self.bot._human_delay(2, 3)
        
        join_patterns = ["Ask to join", "Join now", "Join", "Ask"]
        
        for pattern in join_patterns:
            try:
                button = self.page.get_by_role("button", name=pattern).first
                if button.is_visible(timeout=5000):
                    print(f"🔍 Found button: {pattern}")
                    
                    is_disabled = button.evaluate("btn => btn.disabled || btn.getAttribute('aria-disabled') === 'true'")
                    
                    if is_disabled:
                        print(f"⚠️ Button '{pattern}' is disabled, waiting...")
                        self.bot._human_delay(2, 3)
                        is_disabled = button.evaluate("btn => btn.disabled || btn.getAttribute('aria-disabled') === 'true'")
                    
                    if not is_disabled:
                        button.click(timeout=5000)
                        print(f"✅ Clicked: {pattern}")
                        return True
                    else:
                        print(f"⚠️ Force clicking disabled button...")
                        button.evaluate("btn => btn.click()")
                        return True
            except Exception as e:
                print(f"⚠️ Could not click '{pattern}': {str(e)[:100]}")
        
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
        self.bot._human_delay(5, 7)
        
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
        
        try:
            current_url = self.page.url
            if '/meet/' in current_url or 'meet.google.com' in current_url:
                print(f"✅ URL indicates we're in meeting: {current_url}")
                return True
        except:
            pass
        
        print("⚠️ Could not confirm meeting joined")
        return False
