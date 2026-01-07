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
            # check for join requests
            item = redis_client.blpop("bot_join_queue", timeout=1)
            
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
                    # 1. Join & start audio
                    bot.join_meeting(meeting_url)
                    bot.start_audio_stream()

                    # Clear any previous stop signal
                    stop_key = f"stop_meeting_{meeting_id}"
                    redis_client.delete(stop_key)
                    
                    print(f"\n✅ Bot joined Meeting {meeting_id}. Monitoring audio...")
                    
                    while bot.is_connected:
                        # 1. Check for Manual Stop Signal
                        if redis_client.exists(stop_key):
                            print(f"🛑 Received STOP signal for meeting {meeting_id}")
                            break
                        
                        # 2. Check for Audio Playback (TTS)
                        try:
                            # Use lpop (non-blocking) so we don't freeze the loop
                            item = redis_client.lpop("audio_playback_queue")
                            if item:
                                print(f"DEBUG: Found item in audio_playback_queue: {item}")
                                playback_data = json.loads(item)
                                # Only play if it matches current meeting (simple check)
                                msg_meeting_id = playback_data.get("meeting_id")
                                print(f"DEBUG: Msg Meeting ID: {msg_meeting_id}, Current Meeting ID: {meeting_id}")
                                
                                if str(msg_meeting_id) == str(meeting_id):
                                    file_path = playback_data.get("file_path")
                                    print(f"DEBUG: File Path: {file_path}")
                                    if file_path:
                                        print(f"🗣️ Bot is speaking: {file_path}")

                                        # 1. Unmute before speaking
                                        if bot:
                                           bot.unmute_microphone()
                                           time.sleep(0.5)

                                        # 2. Play Audio
                                        bot.recorder.play_audio(file_path)

                                        # 3. Mute after speakingß
                                        if bot:
                                            time.sleep(0.5)
                                            bot.mute_microphone()

                                        # Send signal to clear AI context
                                        redis_client.rpush("conversation_analysis_queue", json.dumps({
                                            "meeting_id": meeting_id,
                                            "text": "CLEAR_BUFFER_SIGNAL",
                                            "speaker": "System"
                                        }))
                                else:
                                    print(f"DEBUG: Meeting ID mismatch. Ignoring.")
                        except Exception as e:
                            print(f"Playback Error: {e}")
                        
                        # 3. Perform Bot Maintenance (Move mouse, check kicked status)
                        if bot:
                            bot.perform_maintenance()
                        
                        time.sleep(0.5)
                        
                except Exception as e:
                    print(f"❌ Error during meeting execution: {e}")
                finally:
                    if bot:
                        bot.leave_meeting()
                    # Clean up stop key
                    redis_client.delete(f"stop_meeting_{meeting_id}")
                    print("🔄 Bot finished. Waiting for next request...")

        except KeyboardInterrupt:
            print("\n🛑 Stopping Bot Service...")
            sys.exit(0)
        except Exception as e:
            print(f"⚠️ Error in main loop: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
