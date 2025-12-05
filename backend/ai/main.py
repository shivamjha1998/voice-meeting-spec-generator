import time
from backend.ai.llm_client import LLMClient

def main():
    print("Starting AI Processing Service...")
    llm_client = LLMClient()
    
    # In a real scenario, this service would listen for events (e.g., meeting ended)
    while True:
        time.sleep(10)
        print("AI Service Heartbeat")

if __name__ == "__main__":
    main()
