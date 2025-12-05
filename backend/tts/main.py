import time
from backend.tts.google_tts import GoogleTTSClient

def main():
    print("Starting TTS Service...")
    tts_client = GoogleTTSClient()
    
    # In a real scenario, this service would consume text from a queue
    while True:
        time.sleep(10)
        print("TTS Service Heartbeat")

if __name__ == "__main__":
    main()
