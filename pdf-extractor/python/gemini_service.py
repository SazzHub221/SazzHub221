import os

import google.generativeai as genai

import json

import logging

from typing import Dict, Any

from dotenv import load_dotenv

import re



load_dotenv()

logger = logging.getLogger(__name__)



class GeminiService:

    def __init__(self):

        self.api_key = os.getenv("GEMINI_API_KEY")

        if not self.api_key:

            raise ValueError("GEMINI_API_KEY environment variable is not set")

        

        genai.configure(api_key=self.api_key)

        self.model = genai.GenerativeModel('gemini-pro')



    def generate_resume_summary(self, resume_data: Dict[str, Any]) -> str:

        """Generate a concise summary of the resume."""

        try:

            prompt = f"""

            Generate a concise professional summary (2-3 sentences) from this resume data:

            {json.dumps(resume_data, indent=2)}

            

            Focus on:

            1. Years of experience

            2. Key technical skills

            3. Major achievements

            4. Educational background

            

            Return only the summary text, no additional formatting or explanation.

            """



            response = self.model.generate_content(prompt)

            return response.text.strip()

        except Exception as e:

            logger.error(f"Error generating resume summary: {str(e)}")

            return ""



    def calculate_ats_score(self, resume_data: Dict[str, Any]) -> Dict[str, Any]:

        """Calculate ATS compatibility score."""

        try:

            prompt = f"""

            Analyze this resume data and provide a detailed, specific ATS analysis:

            {json.dumps(resume_data, indent=2)}



            Consider these aspects for analysis:

            1. Job-specific keywords and skills

            2. Resume format and structure

            3. Experience descriptions

            4. Education relevance

            5. Project relevance

            6. Industry-specific requirements



            For each skill category in the resume, evaluate against these common requirements:

            - Software Development: Python, Java, JavaScript, React, Node.js, SQL, AWS, Docker, Git

            - Data Science: Python, R, SQL, Machine Learning, TensorFlow, Data Visualization

            - DevOps: AWS, Docker, Kubernetes, CI/CD, Jenkins, Terraform

            - Frontend: React, Angular, Vue.js, HTML5, CSS3, JavaScript

            - Backend: Node.js, Python, Java, SQL, NoSQL, RESTful APIs

            - Cloud: AWS, Azure, GCP, Docker, Kubernetes

            

            Provide highly specific feedback based on the actual content. Return a JSON object with:

            {{

                "ats_score": (calculated score 0-100),

                "section_scores": {{

                    "format_score": (score based on resume structure),

                    "content_score": (score based on content quality),

                    "keyword_score": (score based on keyword presence),

                    "experience_score": (score based on experience descriptions)

                }},

                "matching_skills": [

                    (list of found relevant skills, specific to their experience)

                ],

                "missing_skills": [

                    (list of recommended skills based on their career path)

                ],

                "keyword_analysis": {{

                    "found_keywords": [

                        (industry-specific keywords found in the resume)

                    ],

                    "missing_keywords": [

                        (relevant keywords missing based on their field)

                    ]

                }},

                "suggestions": [

                    (specific, actionable suggestions based on actual content)

                ],

                "improvement_areas": {{

                    "format": [

                        (specific format improvements needed)

                    ],

                    "content": [

                        (specific content improvements needed)

                    ],

                    "keywords": [

                        (specific keyword improvements needed)

                    ],

                    "experience": [

                        (specific experience description improvements needed)

                    ]

                }}

            }}



            Important:

            1. Analyze their actual career path and provide relevant suggestions

            2. Don't suggest skills that don't match their career direction

            3. Be specific about improvements needed in their actual experience descriptions

            4. Provide actionable feedback based on their current content

            5. Consider their education and project background

            6. Focus on their industry-specific requirements

            7. Don't use generic suggestions - make them specific to this resume



            Return only the raw JSON object, no additional text or formatting.

            """



            response = self.model.generate_content(prompt)

            response_text = response.text.strip()

            

            try:

                # Clean and parse the response

                cleaned_json = self.clean_json_response(response_text)

                result = json.loads(cleaned_json)
                

                # Ensure all arrays are properly formatted

                if "suggestions" in result:

                    result["suggestions"] = [

                        str(s) if isinstance(s, (str, int, float)) else s.get("feedback", "")

                        for s in (result["suggestions"] if isinstance(result["suggestions"], list) else [])

                    ]

                

                if "improvement_areas" in result:

                    for area, suggestions in result["improvement_areas"].items():

                        if isinstance(suggestions, list):

                            result["improvement_areas"][area] = [

                                str(s) if isinstance(s, (str, int, float)) else s.get("feedback", "")

                                for s in suggestions

                            ]

                        else:

                            result["improvement_areas"][area] = []

                

                # Ensure the result is JSON serializable

                return json.loads(json.dumps(result, default=str))

            except json.JSONDecodeError as e:

                logger.error(f"Invalid JSON in ATS score: {response_text}")

                logger.error(f"JSON error: {str(e)}")

                return {

                    "ats_score": 0,

                    "section_scores": {},

                    "matching_skills": [],

                    "missing_skills": [],

                    "keyword_analysis": {

                        "found_keywords": [],

                        "missing_keywords": []

                    },

                    "suggestions": [],

                    "improvement_areas": {}

                }

        except Exception as e:

            logger.error(f"Error calculating ATS score: {str(e)}")

            return {

                "ats_score": 0,

                "section_scores": {},

                "matching_skills": [],

                "missing_skills": [],

                "keyword_analysis": {

                    "found_keywords": [],

                    "missing_keywords": []

                },

                "suggestions": [],

                "improvement_areas": {}

            }



    def score_technical_skills(self, skills: Dict[str, list]) -> Dict[str, Any]:

        """Score technical skills based on relevance and demand."""

        try:

            prompt = f"""

            Analyze these technical skills and return a JSON object exactly like this example (no markdown or formatting):

            {{

                "overall_score": 85,

                "category_scores": {{

                    "Programming Languages": 90,

                    "Frameworks & Libraries": 80,

                    "Databases": 75,

                    "Tools & Technologies": 85

                }},

                "recommendations": [

                    "Add more cloud technologies",

                    "Include version control systems"

                ]

            }}



            Skills to analyze:

            {json.dumps(skills, indent=2)}

            

            Important: Return only the raw JSON object, no additional text or formatting.

            """



            response = self.model.generate_content(prompt)

            response_text = response.text.strip()

            

            # Clean response text

            response_text = re.sub(r'^```\w*\s*', '', response_text)

            response_text = re.sub(r'\s*```$', '', response_text)

            response_text = re.sub(r'^JSON\s*', '', response_text)

            response_text = re.sub(r'[\u200b\ufeff\u200e]', '', response_text)  # Remove zero-width spaces

            

            try:

                result = json.loads(response_text)

                return {

                    "overall_score": result.get("overall_score", 0),

                    "category_scores": result.get("category_scores", {}),

                    "recommendations": result.get("recommendations", [])

                }

            except json.JSONDecodeError as e:

                logger.error(f"Invalid JSON in technical skills: {response_text}")

                logger.error(f"JSON error: {str(e)}")

                return {

                    "overall_score": 0,

                    "category_scores": {},

                    "recommendations": []

                }

        except Exception as e:

            logger.error(f"Error scoring technical skills: {str(e)}")

            return {

                "overall_score": 0,

                "category_scores": {},

                "recommendations": []

            }



    def clean_json_response(self, response_text: str) -> str:
        """Clean and validate JSON response."""
        try:
            # Remove markdown formatting
            text = response_text.strip()
            text = re.sub(r'^```\w*\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
            text = re.sub(r'^JSON\s*', '', text)
            
            # Remove invisible characters
            text = re.sub(r'[\u200b\ufeff\u200e]', '', text)
            
            # Fix common JSON issues
            text = text.replace('\n', '')
            text = text.replace('\r', '')
            text = text.replace('\\', '\\\\')
            text = text.replace('None', 'null')
            text = text.replace('True', 'true')
            text = text.replace('False', 'false')
            
            # Validate JSON by parsing and re-stringifying
            parsed = json.loads(text)
            return json.dumps(parsed)
        except Exception as e:
            logger.error(f"Error cleaning JSON response: {str(e)}")
            logger.error(f"Original text: {response_text}")
            raise



    def analyze_resume(self, text: str) -> Dict[str, Any]:

        """Analyze resume text using Gemini API."""

        try:

            prompt = f"""

            You are a resume parser. Analyze this resume and return a JSON object.

            Format the response as a clean JSON object without any markdown formatting or code blocks.

            Use this structure:

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



            Resume text to analyze:

            {text}



            Important: Return only the raw JSON object without any markdown formatting, code blocks, or additional text.

            """



            response = self.model.generate_content(prompt)

            

            response_text = response.text.strip()

            

            try:

                # Clean and parse the response

                cleaned_json = self.clean_json_response(response_text)

                result = json.loads(cleaned_json)
                

                # Ensure experience achievements is always a list

                if "experience" in result:

                    for exp in result["experience"]:

                        if "achievements" not in exp:

                            exp["achievements"] = []

                        elif not isinstance(exp["achievements"], list):

                            exp["achievements"] = [exp["achievements"]]

                

                # Ensure the result is JSON serializable

                return json.loads(json.dumps(result, default=str))

            except Exception as e:

                logger.error(f"Invalid JSON response: {response_text}")

                logger.error(f"JSON error: {str(e)}")

                # Return default structure

                return {

                    "name": "",

                    "email": "",

                    "phone": "",

                    "location": "",

                    "education": {

                        "degree": "",

                        "university": "",

                        "major": "",

                        "cgpa": "",

                        "graduationYear": ""

                    },

                    "experience": [],

                    "skills": {

                        "Programming Languages": [],

                        "Frameworks & Libraries": [],

                        "Databases": [],

                        "Tools & Technologies": [],

                        "Other Skills": []

                    },

                    "projects": [],

                    "certifications": []

                }



        except Exception as e:

            logger.error(f"Error in Gemini API call: {str(e)}")

            logger.error(f"Full response: {response.text if 'response' in locals() else 'No response'}")

            raise 
