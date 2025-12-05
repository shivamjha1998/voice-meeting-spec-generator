import time

class ZoomBot:
    def __init__(self):
        self.is_connected = False

    def join_meeting(self, meeting_url: str):
        print(f"Joining Zoom meeting: {meeting_url}")
        # Simulate connection delay
        time.sleep(2)
        self.is_connected = True
        print("Joined Zoom meeting successfully.")

    def leave_meeting(self):
        print("Leaving Zoom meeting...")
        self.is_connected = False

    def start_audio_stream(self):
        if not self.is_connected:
            raise Exception("Not connected to a meeting")
        print("Starting audio stream from Zoom...")
        # In a real implementation, this would yield audio chunks
        return True
