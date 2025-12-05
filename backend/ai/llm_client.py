import os
import time

class LLMClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

    def generate_question(self, context: str) -> str:
        print("Generating question based on context...")
        return "Could you clarify the timeline for the frontend implementation?"

    def summarize_meeting(self, transcript: str) -> str:
        print("Summarizing meeting transcript...")
        time.sleep(2)
        return """
        **Meeting Summary**
        - Discussed project requirements.
        - Agreed on microservices architecture.
        - Action Item: Setup Docker Compose.
        """

    def generate_specification(self, summary: str) -> str:
        print("Generating specification from summary...")
        time.sleep(2)
        return """
        # Project Specification
        ## Overview
        ...
        ## Requirements
        ...
        """

    def extract_tasks(self, specification: str) -> list:
        print("Extracting tasks from specification...")
        return [
            {"title": "Setup Docker", "description": "Configure docker-compose.yml"},
            {"title": "Initialize Git", "description": "Run git init"}
        ]
