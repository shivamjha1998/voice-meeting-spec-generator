import time
import sys
import os
from backend.bot.zoom_bot import ZoomBot
from backend.bot.meet_bot import GoogleMeetBot

def main():
    print("🤖 Starting Meeting Bot Service...")

    # For testing purposes, check ENV var instead of blocking input
    print("\n--- TEST MODE ---")
    meeting_url = input("Enter Meeting URL (Zoom or Google Meet): ").strip()
    
    if not meeting_url:
        print("ℹ️ No URL provided. Waiting loop...")
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            return

    # Determine Platform
    bot = None
    if "zoom.us" in meeting_url:
        print("Detected Zoom URL.")
        bot = ZoomBot()
    elif "meet.google.com" in meeting_url:
        print ("Detected Google Meet URL.")
        bot = GoogleMeetBot()
    else:
        print("❌ Unsupported Platform. Please use a Zoom or Google Meet URL.")
        return

    try:
        # 1. Join
        bot.join_meeting(meeting_url)
        
        # 2. Start audio
        bot.start_audio_stream()
        
        print("\n✅ Bot is running. Press Ctrl+C to stop.")
        
        # Keep the script running to maintain the browser and audio stream
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping bot...")
        bot.leave_meeting()
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error during execution: {e}")
        bot.leave_meeting()
        sys.exit(1)

if __name__ == "__main__":
    main()
