import sys
import pdfplumber
import spacy
import re
import json
import logging
from typing import Dict
from pathlib import Path
from gemini_service import GeminiService
from dotenv import load_dotenv
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

class PDFExtractor:
    def __init__(self):
        try:
            self.nlp = spacy.load("en_core_web_sm")
            self.gemini_service = GeminiService()
        except OSError:
            logger.error("Spacy model not found. Installing...")
            import subprocess
            subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
            self.nlp = spacy.load("en_core_web_sm")
            self.gemini_service = GeminiService()

    def parse_label_field(self, text: str, label: str) -> str:
        """Extract field value based on label."""
        patterns = [
            f"{label}\\s*:\\s*(.*)",
            f"{label}\\s*-\\s*(.*)",
            f"{label}\\s*=\\s*(.*)",
            f"{label}\\s+(.*)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).split('\n')[0].strip()
        return ""

    def extract_phone_number(self, text: str) -> str:
        """Extract phone number using various formats."""
        patterns = [
            r"(\+?\d[\d\s\-\(\)]{7,}\d)",  # International format
            r"\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}",  # US format
            r"\d{10,}",  # Simple consecutive digits
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        return ""

    def extract_email(self, text: str) -> str:
        """Extract email address."""
        pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        match = re.search(pattern, text)
        return match.group(0) if match else ""

    def extract_dates(self, text: str) -> Dict[str, str]:
        """Extract dates (birth date, joining date, etc.)."""
        date_patterns = {
            r"(?i)birth\s*(?:date|day)?[\s:]+([A-Za-z0-9\s,]+)": "birthDate",
            r"(?i)(?:joining|start)\s*date[\s:]+([A-Za-z0-9\s,]+)": "joiningDate",
            r"(?i)(?:graduation|completion)\s*date[\s:]+([A-Za-z0-9\s,]+)": "graduationDate"
        }
        
        dates = {}
        for pattern, key in date_patterns.items():
            match = re.search(pattern, text)
            if match:
                dates[key] = match.group(1).strip()
        return dates

    def extract_sections(self, text: str) -> Dict[str, str]:
        """Extract main sections from the resume."""
        sections = {
            'objective': '',
            'education': '',
            'experience': '',
            'skills': '',
            'projects': '',
            'certifications': ''
        }
        
        # Split text into lines and process
        lines = text.split('\n')
        current_section = ''
        section_text = []
        
        # Common section headers and their variations
        section_headers = {
            'objective': ['objective', 'summary', 'profile', 'about'],
            'education': ['education', 'academic', 'qualification'],
            'experience': ['experience', 'employment', 'work history'],
            'skills': ['technical skills', 'skills', 'technologies', 'competencies'],
            'projects': ['projects', 'project work', 'academic projects'],
            'certifications': ['certifications', 'certificates', 'credentials']
        }
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            lower_line = line.lower()
            
            # Check if this line is a section header
            found_section = False
            for section, headers in section_headers.items():
                if any(header in lower_line for header in headers):
                    if current_section:
                        sections[current_section] = '\n'.join(section_text)
                    current_section = section
                    section_text = []
                    found_section = True
                    break
            
            if not found_section and current_section:
                section_text.append(line)
        
        # Add the last section
        if current_section and section_text:
            sections[current_section] = '\n'.join(section_text)
        
        return sections

    def extract_experience(self, text: str) -> list:
        """Extract work experience details."""
        experiences = []
        
        # First try to find the experience section
        experience_section = re.search(r"(?i)(?:EXPERIENCE|EMPLOYMENT|WORK HISTORY).*?\n(.*?)(?=\n(?:PROJECTS|EDUCATION|SKILLS|CERTIFICATIONS)|$)", text, re.DOTALL)
        if not experience_section:
            return []

        experience_text = experience_section.group(1)
        
        # Split into individual experiences
        exp_blocks = re.split(r'\n(?=[A-Z][^a-z]*?(?:20\d{2}|19\d{2}))', experience_text)
        
        for block in exp_blocks:
            if not block.strip():
                continue
            
            # Try to extract company and position
            company_match = re.search(r'^([^•\n]+)', block)
            if not company_match:
                continue
            
            company_line = company_match.group(1).strip()
            
            # Try to extract position and company
            position = ""
            company = company_line
            if " at " in company_line:
                position, company = company_line.split(" at ", 1)
            elif " - " in company_line:
                position, company = company_line.split(" - ", 1)
            elif "|" in company_line:
                position, company = company_line.split("|", 1)
            
            # Extract duration
            duration_match = re.search(r'(?:20\d{2}|19\d{2})\s*[-–]\s*(?:20\d{2}|19\d{2}|Present)', block)
            duration = duration_match.group(0) if duration_match else ""
            
            # Extract achievements
            achievements = []
            for line in block.split('\n'):
                line = line.strip()
                if line.startswith('•') or line.startswith('-'):
                    achievement = line.lstrip('•- ').strip()
                    if achievement:
                        achievements.append(achievement)
            
            experiences.append({
                "company": company.strip(),
                "position": position.strip(),
                "duration": duration.strip(),
                "achievements": achievements
            })
        
        return experiences

    def extract_projects(self, text: str) -> list:
        """Extract project details."""
        projects = []
        
        # Find the projects section
        projects_section = re.search(r"(?i)(?:PROJECTS|PROJECT WORK).*?\n(.*?)(?=\n(?:EDUCATION|SKILLS|EXPERIENCE|CERTIFICATIONS)|$)", text, re.DOTALL)
        if not projects_section:
            return projects

        projects_text = projects_section.group(1)
        
        # Split into individual projects
        project_patterns = [
            r"(?m)^\s*[A-Z][^•\n]*?(?=\n|$)(?:\n[^•\n]*?(?=\n|$))*(?:\n\s*•.*?(?=\n[A-Z]|$))*",
            r"(?m)^\s*•\s*[^\n]+(?:\n\s*[^•\n]+)*"
        ]
        
        for pattern in project_patterns:
            matches = re.finditer(pattern, projects_text, re.MULTILINE | re.DOTALL)
            for match in matches:
                project = match.group(0).strip()
                if project and len(project) > 10:
                    projects.append(project)
            if projects:
                break
        
        return projects

    def extract_technical_skills(self, text: str) -> Dict[str, list]:
        """Extract technical skills from text."""
        skills_dict = {}
        
        # Common section headers for technical skills
        section_headers = [
            r"(?i)TECHNICAL\s+SKILLS?",
            r"(?i)TECHNICAL\s+EXPERTISE",
            r"(?i)TECHNICAL\s+PROFICIENCIES",
            r"(?i)TECHNOLOGIES",
            r"(?i)SKILLS\s+AND\s+TECHNOLOGIES"
        ]
        
        # Find the technical skills section
        skills_section = None
        for header in section_headers:
            match = re.search(f"{header}.*?\\n(.*?)(?=\\n\\s*[A-Z][A-Z\\s]+:|$)", text, re.DOTALL | re.MULTILINE)
            if match:
                skills_section = match.group(1)
                break

        if not skills_section:
            return {}

        # Clean up the text
        skills_text = skills_section.strip()
        
        # Try to find categorized skills first (e.g., "Languages: Python, Java")
        categories = re.finditer(r"(?m)^([^:•]+):\s*([^\n]+)(?:\n|$)", skills_text)
        has_categories = False
        
        for match in categories:
            has_categories = True
            category = match.group(1).strip()
            # Split skills by common separators and clean up
            skills = [
                skill.strip() 
                for skill in re.split(r'[,|•|●|\(\)]', match.group(2))
                if skill.strip() and not skill.strip().startswith('(')
            ]
            if skills:
                skills_dict[category] = skills
        
        # If no categories found, try to split by bullet points or lines
        if not has_categories:
            all_skills = []
            for line in skills_text.split('\n'):
                line = line.strip()
                if line and not line.endswith(':'):
                    # Remove bullet points and split by commas
                    line = re.sub(r'^[•●\-]\s*', '', line)
                    skills = [
                        skill.strip() 
                        for skill in re.split(r'[,|•|●|\(\)]', line)
                        if skill.strip() and not skill.strip().startswith('(')
                    ]
                    all_skills.extend(skills)
            
            if all_skills:
                skills_dict["Technical Skills"] = list(set(all_skills))
        
        return skills_dict

    def extract_certifications(self, text: str) -> list:
        """Extract certifications."""
        certifications = []
        
        # Find the certifications section
        cert_section = re.search(r"(?i)(?:CERTIFICATIONS|CERTIFICATES).*?\n(.*?)(?=\n(?:PROJECTS|EDUCATION|EXPERIENCE|SKILLS)|$)", text, re.DOTALL)
        if not cert_section:
            return certifications

        cert_text = cert_section.group(1)
        
        # Split by bullet points or new lines
        for cert in re.split(r'(?:\n(?=•|\-)|\n\n)', cert_text):
            cert = cert.strip()
            if cert and not cert.startswith(('•', '-')):
                certifications.append(cert)
        
        return certifications

    def extract_education(self, text: str) -> Dict[str, str]:
        """Extract education details."""
        education = {}
        
        # Look for degree and university
        degree_match = re.search(r"(?i)(?:B\.Tech|Bachelor|Master|M\.Tech|PhD)[\s\w]+(?=\s|$)", text)
        if degree_match:
            education['degree'] = degree_match.group(0).strip()

        university_match = re.search(r"(?i)(?:University|Institute|College)[\s\w]+(?=\s|$)", text)
        if university_match:
            education['university'] = university_match.group(0).strip()

        # Look for CGPA
        cgpa_match = re.search(r"(?i)(?:CGPA|GPA)[:\s]+(\d+\.?\d*)", text)
        if cgpa_match:
            education['cgpa'] = cgpa_match.group(1)

        return education

    def generate_summary(self, sections: Dict[str, str]) -> str:
        """Generate a summary from the resume sections."""
        summary = []
        
        if sections['objective']:
            summary.append(sections['objective'].strip())
        
        if sections['experience']:
            exp_summary = f"Has experience in {sections['experience'].split('\n')[0].strip()}"
            summary.append(exp_summary)
        
        if sections['skills']:
            skills = self.extract_technical_skills(sections['skills'])
            if skills:
                skills_summary = f"Skilled in {', '.join(skills[:5])}"
                if len(skills) > 5:
                    skills_summary += " and more"
                summary.append(skills_summary)
        
        return " ".join(summary)

    def extract_data_from_pdf(self, pdf_path: str) -> Dict[str, any]:
        """Extract structured data from PDF."""
        try:
            if not Path(pdf_path).exists():
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")

            # Extract text from PDF
            text_data = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text_data += page.extract_text() + "\n"

            try:
                # Use Gemini API to analyze the resume
                extracted_data = self.gemini_service.analyze_resume(text_data)

                # Generate resume summary
                summary = self.gemini_service.generate_resume_summary(extracted_data)
                extracted_data["summary"] = summary

                # Calculate ATS score
                ats_analysis = self.gemini_service.calculate_ats_score(extracted_data)
                extracted_data["ats_analysis"] = ats_analysis

                # Score technical skills
                if "skills" in extracted_data:
                    skills_analysis = self.gemini_service.score_technical_skills(extracted_data["skills"])
                    extracted_data["skills_analysis"] = skills_analysis

                # Ensure all values are JSON serializable
                return json.loads(json.dumps(extracted_data, default=str))

            except Exception as e:
                logger.error(f"Error processing data: {str(e)}")
                return {
                    "error": f"Error processing data: {str(e)}",
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
                    "skills": {},
                    "projects": [],
                    "certifications": [],
                    "summary": "",
                    "ats_analysis": {
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
                    },
                    "skills_analysis": {
                        "overall_score": 0,
                        "category_scores": {},
                        "recommendations": []
                    }
                }

        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            return {
                "error": f"Error processing PDF: {str(e)}"
            }

    def parse_name(self, text: str) -> str:
        """Extract name from the resume."""
        # Usually the name is at the top of the resume
        first_line = text.split('\n')[0].strip()
        if first_line and len(first_line.split()) <= 4:  # Most names are 1-4 words
            return first_line
        return ""

    def parse_location(self, text: str) -> str:
        """Extract location from the resume."""
        # Look for common location patterns
        location_patterns = [
            r"(?i)Location[\s:]+([^\n]+)",
            r"(?i)Address[\s:]+([^\n]+)",
            r"(?i)(?:City|State)[\s:]+([^\n]+)",
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return ""

def main():
    if len(sys.argv) != 2:
        logger.error("Usage: python extractor.py <pdf_path>")
        sys.exit(1)

    try:
        extractor = PDFExtractor()
        data = extractor.extract_data_from_pdf(sys.argv[1])
        print(json.dumps(data))
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()