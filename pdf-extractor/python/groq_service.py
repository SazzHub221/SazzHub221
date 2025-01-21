import os
from typing import Dict, Any
import groq
import json
import logging
from dotenv import load_dotenv
import re

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

class GroqService:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        logger.debug(f"GROQ_API_KEY loaded: {self.api_key[:10]}...")  # Only log first 10 chars for security
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set")
        
        # Verify API key format
        if not self.api_key.startswith('gsk_'):
            raise ValueError("Invalid GROQ_API_KEY format. It should start with 'gsk_'")
        
        self.client = groq.Groq(
            api_key=self.api_key,
            base_url="https://api.groq.com/openai/v1"  # Explicitly set the base URL
        )

    def analyze_resume(self, text: str) -> Dict[str, Any]:
        """Analyze resume text using Groq API."""
        try:
            prompt = f"""
            Analyze the following resume and extract key information in a structured format.
            Return the data in this exact JSON format:
            {{
                "name": "",
                "email": "",
                "phone": "",
                "location": "",
                "education": {{
                    "degree": "",
                    "university": "",
                    "major": "",
                    "cgpa": "",
                    "graduationYear": ""
                }},
                "experience": [
                    {{
                        "company": "",
                        "position": "",
                        "duration": "",
                        "achievements": []
                    }}
                ],
                "skills": {{
                    "Programming Languages": [],
                    "Frameworks & Libraries": [],
                    "Databases": [],
                    "Tools & Technologies": [],
                    "Other Skills": []
                }},
                "projects": [
                    {{
                        "name": "",
                        "description": "",
                        "technologies": [],
                        "achievements": []
                    }}
                ],
                "certifications": [
                    {{
                        "name": "",
                        "issuer": "",
                        "date": ""
                    }}
                ]
            }}

            Resume text:
            {text}

            Instructions:
            1. Extract all information accurately
            2. Format experience with company, position, duration, and achievements
            3. Categorize technical skills appropriately
            4. Include all projects with their technologies
            5. Keep dates in consistent format
            6. Ensure all arrays are properly populated
            7. If a section is not found, leave its fields empty but maintain the structure
            """

            response = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert resume analyzer. Extract and structure information accurately."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model="mixtral-8x7b-32768",
                temperature=0.1,
                max_tokens=4000
            )

            result = json.loads(response.choices[0].message.content)
            
            # Ensure experience achievements is always a list
            if "experience" in result:
                for exp in result["experience"]:
                    if "achievements" not in exp:
                        exp["achievements"] = []
                    elif not isinstance(exp["achievements"], list):
                        exp["achievements"] = [exp["achievements"]]

            return result

        except Exception as e:
            logger.error(f"Error in Groq API call: {str(e)}")
            raise

    def enhance_extraction(self, initial_extract: Dict[str, Any], text: str) -> Dict[str, Any]:
        """Enhance the initial extraction with Groq's analysis."""
        try:
            prompt = f"""
            Review and enhance the following resume extraction.
            
            Original extraction:
            {json.dumps(initial_extract, indent=2)}

            Original text:
            {text}

            Please:
            1. Verify the extracted information
            2. Add any missing details
            3. Categorize technical skills more accurately
            4. Extract key achievements from experience
            5. Identify technologies used in projects

            Maintain the same JSON structure but enhance the content.
            """

            response = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert resume analyzer. Enhance and verify extracted information."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model="mixtral-8x7b-32768",
                temperature=0.1,
                max_tokens=4000
            )

            enhanced_data = json.loads(response.choices[0].message.content)
            return enhanced_data

        except Exception as e:
            logger.error(f"Error in Groq enhancement: {str(e)}")
            return initial_extract 