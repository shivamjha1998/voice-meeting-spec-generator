import time
import sys
import os
from backend.bot.zoom_bot import ZoomBot

def main():
    print("🤖 Starting Meeting Bot Service...")
    
    # Initialize the Bot
    zoom_bot = ZoomBot()

    # For testing purposes, check ENV var instead of blocking input
    print("\n--- TEST MODE ---")
    meeting_url = input("Enter Zoom Meeting URL (or press Enter to skip): ").strip()
    
    if not meeting_url:
        print("ℹ️ No TEST_MEETING_URL provided. Bot is standing by (waiting for commands via Redis in future updates).")
        # Keep the container running
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            pass
        return

    if meeting_url:
        try:
            # 1. Join the Meeting (Opens Browser)
            zoom_bot.join_meeting(meeting_url)
            
            # 2. Start capturing audio (System Mic)
            zoom_bot.start_audio_stream()
            
            print("\n✅ Bot is running. Press Ctrl+C to stop.")
            
            # Keep the script running to maintain the browser and audio stream
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\nStopping bot...")
            zoom_bot.leave_meeting()
            sys.exit(0)
    else:
        print("No URL provided. Exiting.")

if __name__ == "__main__":
    main()
