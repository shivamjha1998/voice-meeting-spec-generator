import os
from huggingface_hub import InferenceClient

class LLMClient:
    def __init__(self):
        # Prefer HUGGING_FACE_KEY, fallback to OPENAI_API_KEY (if user reused it), or warn.
        self.api_key = os.getenv("HUGGING_FACE_KEY")
        if not self.api_key:
            print("⚠️ WARNING: HUGGING_FACE_KEY is not set.")
        
        self.client = InferenceClient(token=self.api_key)
        # Using Llama 3.2 3B as it is widely supported on serverless
        self.model = "meta-llama/Llama-3.2-3B-Instruct"

    def summarize_meeting(self, transcript: str) -> str:
        """Summarizes the raw transcript into key points."""
        system_prompt = "You are a Technical Project Manager. Summarize the following meeting transcript into clear bullet points, focusing on requirements, decisions, and action items."
        
        try:
            response = self.client.chat_completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcript}
                ],
                max_tokens=2000
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"HF Error (Summarize): {e}")
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
            response = self.client.chat_completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": summary}
                ],
                max_tokens=3000
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"HF Error (Spec Gen): {e}")
            return "# Error\nCould not generate specification."

    def extract_tasks(self, spec_content: str) -> str:
        """
        Extracts tasks from the specification content as a JSON string.
        Expected format: {"tasks": [{"title": "...", "description": "..."}]}
        """
        system_prompt = """
        You are a Technical Project Manager. Given a Project Specification, extract actionable tasks.
        Return ONLY a raw JSON object (no markdown formatting, no backticks).
        Format:
        {
            "tasks": [
                {
                    "title": "Short title of the task",
                    "description": "Detailed description suitable for a GitHub Issue body"
                }
            ]
        }
        """
        
        try:
            response = self.client.chat_completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": spec_content}
                ],
                max_tokens=2000
            )
            content = response.choices[0].message.content
            # Clean up potential markdown code blocks if the model captures them
            content = content.replace("```json", "").replace("```", "").strip()
            return content
        except Exception as e:
            print(f"HF Error (Task Extraction): {e}")
            return '{"tasks": []}'
