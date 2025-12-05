import os
from openai import OpenAI

class LLMClient:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key)

    def summarize_meeting(self, transcript: str) -> str:
        """Summarizes the raw transcript into key points."""
        system_prompt = "You are a Technical Project Manager. Summarize the following meeting transcript into clear bullet points, focusing on requirements, decisions, and action items."
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o", # or gpt-3.5-turbo
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcript}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"LLM Error (Summarize): {e}")
            return "Error generating summary."

    def generate_specification(self, summary: str) -> str:
        """Converts the summary into a Markdown Specification."""
        system_prompt = """
        You are a Senior Software Architect. Based on the provided meeting summary, write a detailed Project Specification in Markdown format.
        Include these sections: 
        1. Project Overview
        2. Functional Requirements
        3. Technical Constraints
        4. Action Items
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": summary}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"LLM Error (Spec Gen): {e}")
            return "# Error\nCould not generate specification."
