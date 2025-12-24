from backend.bot.common.base import BaseBot
from backend.bot.google_meet.audio import AudioConfigurator
from backend.bot.google_meet.media import MediaController
from backend.bot.google_meet.navigation import MeetingJoiner

class GoogleMeetBot(BaseBot):
    def __init__(self, meeting_id=1):
        super().__init__(meeting_id, profile_dir="google_profile")
        
    def join_meeting(self, meeting_url: str):
        """Main method to join a Google Meet meeting"""
        try:
            # 1. Start Browser
            self._start_browser()
            
            # 2. Check for Stealth (already applied in _start_browser logic)
            # 3. Navigate
            print(f"🌐 Navigating to: {meeting_url}")
            self.page.goto(meeting_url, wait_until="domcontentloaded", timeout=60000)
            self._human_delay(3, 5)

            # Initialize Helpers
            self.audio = AudioConfigurator(self)
            self.media = MediaController(self)
            self.joiner = MeetingJoiner(self)

            # 4. Disable Media
            print("🔇 Disabling camera and microphone...")
            self.media.disable_initial_media()
            self._human_delay(1, 2)
            
            # 5. Select Audio Devices
            print("🎤 Selecting BlackHole Devices...")
            self.audio.configure_devices()
            self._human_delay(1, 2)

            # 6. Join Procedure (Name, Popups, Click Join, Verify)
            # This handles the complex logic of getting into the meeting
            self.joiner.join_meeting()
            
            # 7. Post-Join Setup
            self.is_connected = True
            self.media.unmute_microphone()
            self.media.announce_presence()
            print("✅ Successfully joined the meeting!")

        except Exception as e:
            print(f"❌ Join Error: {e}")
            self.leave_meeting()
            raise e