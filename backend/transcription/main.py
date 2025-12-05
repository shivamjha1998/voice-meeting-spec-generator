import time
from backend.transcription.whisper_client import WhisperClient
from backend.common import database, models

def main():
    print("Starting Transcription Service...")
    whisper_client = WhisperClient()
    
    # In a real scenario, this service would consume audio chunks from a queue (Redis/Kafka)
    # For now, we simulate a loop
    while True:
        time.sleep(10)
        print("Transcription Service Heartbeat")

if __name__ == "__main__":
    main()
