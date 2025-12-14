import time
import sys
import os
import redis
import json 
from backend.bot.zoom_bot import ZoomBot
from backend.bot.meet_bot import GoogleMeetBot

def main():
    print("🤖 Starting Meeting Bot Service...")
    
    redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

    print("🤖 Bot Service Ready. Waiting for join requests in 'bot_join_queue'...")
    
    while True:
        try:
            # Blocking pop with timeout (to allow checking for signals)
            # blpop returns tuple (queue_name, data) or None
            item = redis_client.blpop("bot_join_queue", timeout=5)
            
            if item:
                _, data_str = item
                data = json.loads(data_str)
                print(f"📩 Received Join Request: {data}")
                
                meeting_id = data.get("meeting_id", 1)
                meeting_url = data.get("meeting_url")
                
                if not meeting_url:
                    print("⚠️ Invalid request: No meeting_url")
                    continue

                # Determine Platform
                bot = None
                if "zoom.us" in meeting_url:
                    print(f"Detected Zoom URL. ID: {meeting_id}")
                    bot = ZoomBot(meeting_id)
                elif "meet.google.com" in meeting_url:
                    print(f"Detected Google Meet URL. ID: {meeting_id}")
                    bot = GoogleMeetBot(meeting_id)
                else:
                    print("❌ Unsupported Platform.")
                    continue

                try:
                    # 1. Join
                    bot.join_meeting(meeting_url)
                    
                    # 2. Start audio
                    bot.start_audio_stream()
                    
                    print(f"\n✅ Bot joined Meeting {meeting_id}. Monitoring audio...")
                    
                    # Loop to keep bot alive for THIS meeting until told to stop (or just run indefinitely for now)
                    # For a real multi-tenant bot, we'd spawn a process. For now, we block this thread for one meeting.
                    # We check a 'stop_meeting_{id}' key or just run until manual stop?
                    # Let's run until Exception or playback queue logic.
                    
                    while bot.is_connected:
                        try:
                            # Check for audio playback requests (existing logic)
                            item = redis_client.lpop("audio_playback_queue")
                            if item:
                                playback_data = json.loads(item)
                                file_path = playback_data.get("file_path")
                                if file_path and hasattr(bot, 'recorder'):
                                    bot.recorder.play_audio(file_path)
                        except Exception:
                            pass
                        
                        time.sleep(0.5)
                        
                except Exception as e:
                    print(f"❌ Error during meeting execution: {e}")
                finally:
                    if bot:
                        bot.leave_meeting()
                    print("🔄 Bot finished/left meeting. Waiting for next request...")

            else:
                # No job, just loop back
                pass

        except KeyboardInterrupt:
            print("\n🛑 Stopping Bot Service...")
            sys.exit(0)
        except Exception as e:
            print(f"⚠️ Error in main loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()