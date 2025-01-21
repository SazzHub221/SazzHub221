import React, { useState, useRef, useEffect } from "react";
import axios from "axios";
import "./App.css";

// Add these SVG icons as components
const UploadIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M12 15V3m0 0L8 7m4-4l4 4M2 17l.621 2.485A2 2 0 004.561 21h14.878a2 2 0 001.94-1.515L22 17" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

const LoadingSpinner = () => (
  <div className="loading-spinner" />
);

// Data categories configuration
const dataCategories = {
  personal: {
    title: "Personal Information",
    fields: ["name", "email", "phone", "location"],
    icon: "👤"
  },
  education: {
    title: "Education",
    fields: ["education"],
    icon: "🎓"
  },
  experience: {
    title: "Work Experience",
    fields: ["experience"],
    icon: "💼"
  },
  projects: {
    title: "Projects",
    fields: ["projects"],
    icon: "🚀"
  },
  skills: {
    title: "Technical Skills",
    fields: ["skills"],
    icon: "💻"
  },
  certifications: {
    title: "Certifications",
    fields: ["certifications"],
    icon: "📜"
  },
  summary: {
    title: "Resume Summary",
    fields: ["summary"],
    icon: "📝"
  },
  atsScore: {
    title: "ATS Analysis",
    fields: ["ats_analysis"],
    icon: "📊"
  },
  skillsScore: {
    title: "Skills Analysis",
    fields: ["skills_analysis"],
    icon: "🎯"
  }
};

// Field name formatting
const formatFieldName = (field) => {
  const name = field.split('.').pop(); // Handle nested fields
  return name
    .replace(/([A-Z])/g, ' $1')
    .replace(/^./, str => str.toUpperCase());
};

function App() {
  const [file, setFile] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const resultsRef = useRef(null);
  const fileInputRef = useRef(null);

  // Add effect for auto-scrolling
  useEffect(() => {
    if (data && resultsRef.current) {
      resultsRef.current.scrollIntoView({ 
        behavior: 'smooth',
        block: 'start'
      });
    }
  }, [data]);

  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];
    if (selectedFile && selectedFile.type === "application/pdf") {
      setFile(selectedFile);
      setError(null);
    } else {
      setError("Please select a valid PDF file");
      setFile(null);
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!file) return;

    setLoading(true);
    setError(null);
    setData(null);

    const formData = new FormData();
    formData.append("pdf", file);

    try {
      const response = await axios.post("http://localhost:3001/api/upload", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });
      setData(response.data);
    } catch (err) {
      setError(err.response?.data?.error || "An error occurred while processing the file");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setData(null);
    setFile(null);
    setLoading(false);
    setError(null);
    // Reset the file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    // Scroll back to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const renderCategoryData = (category, categoryData) => {
    const fields = categoryData.fields.filter(field => data[field]);
    if (fields.length === 0) return null;

    const renderExperience = (exp) => (
      <div className="experience-item">
        <h4>{exp.position} at {exp.company}</h4>
        <p className="duration">{exp.duration}</p>
        <ul className="achievements-list">
          {exp.achievements.map((achievement, i) => (
            <li key={i}>{achievement}</li>
          ))}
        </ul>
      </div>
    );

    const renderProject = (project) => (
      <div className="project-item">
        <h4>{project.name}</h4>
        <p>{project.description}</p>
        <div className="technologies">
          {project.technologies.map((tech, i) => (
            <span key={i} className="tech-tag">{tech}</span>
          ))}
        </div>
      </div>
    );

    const renderAtsAnalysis = (ats) => (
      <div className="ats-analysis">
        <div className="ats-overview">
          <div className="ats-score-main">
            <h4>Overall ATS Score</h4>
            <div className="score-circle large">{ats.ats_score}%</div>
          </div>
          
          <div className="section-scores">
            <h4>Section Scores</h4>
            <div className="score-grid">
              {Object.entries(ats.section_scores).map(([key, score]) => (
                <div key={key} className="section-score">
                  <label>{key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}</label>
                  <div className="score-bar">
                    <div className="score-fill" style={{width: `${score}%`}}></div>
                    <span className="score-value">{score}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="skills-analysis">
          <div className="matching-skills">
            <h4>Matching Skills</h4>
            <div className="skills-tags">
              {ats.matching_skills.map((skill, i) => (
                <span key={i} className="skill-tag matching">{skill}</span>
              ))}
            </div>
          </div>

          <div className="missing-skills">
            <h4>Missing Skills</h4>
            <div className="skills-tags">
              {ats.missing_skills.map((skill, i) => (
                <span key={i} className="skill-tag missing">{skill}</span>
              ))}
            </div>
          </div>
        </div>

        <div className="keyword-analysis">
          <h4>Keyword Analysis</h4>
          <div className="keyword-grid">
            <div className="found-keywords">
              <h5>Found Keywords</h5>
              <div className="keyword-tags">
                {ats.keyword_analysis.found_keywords.map((keyword, i) => (
                  <span key={i} className="keyword-tag found">{keyword}</span>
                ))}
              </div>
            </div>
            <div className="missing-keywords">
              <h5>Missing Keywords</h5>
              <div className="keyword-tags">
                {ats.keyword_analysis.missing_keywords.map((keyword, i) => (
                  <span key={i} className="keyword-tag missing">{keyword}</span>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="improvement-areas">
          <h4>Areas for Improvement</h4>
          {Object.entries(ats.improvement_areas).map(([area, suggestions]) => (
            <div key={area} className="improvement-section">
              <h5>{area.charAt(0).toUpperCase() + area.slice(1)}</h5>
              <ul>
                {Array.isArray(suggestions) ? (
                  suggestions.map((suggestion, i) => (
                    <li key={i}>{
                      typeof suggestion === 'string' 
                        ? suggestion 
                        : suggestion.feedback || suggestion.toString()
                    }</li>
                  ))
                ) : (
                  <li>No suggestions available</li>
                )}
              </ul>
            </div>
          ))}
        </div>

        <div className="suggestions">
          <h4>General Suggestions</h4>
          <ul>
            {Array.isArray(ats.suggestions) ? (
              ats.suggestions.map((suggestion, i) => (
                <li key={i}>{
                  typeof suggestion === 'string' 
                    ? suggestion 
                    : suggestion.feedback || suggestion.toString()
                }</li>
              ))
            ) : (
              <li>No suggestions available</li>
            )}
          </ul>
        </div>
      </div>
    );

    const renderSkillsAnalysis = (analysis) => (
      <div className="skills-analysis">
        <div className="overall-score">
          <h4>Overall Technical Score</h4>
          <div className="score-circle">{analysis.overall_score}%</div>
        </div>
        <div className="category-scores">
          <h4>Category Scores</h4>
          {Object.entries(analysis.category_scores).map(([category, score], i) => (
            <div key={i} className="category-score">
              <span>{category}</span>
              <div className="score-bar">
                <div className="score-fill" style={{width: `${score}%`}}></div>
              </div>
            </div>
          ))}
        </div>
        <div className="recommendations">
          <h4>Recommendations</h4>
          <ul>
            {analysis.recommendations.map((rec, i) => (
              <li key={i}>{rec}</li>
            ))}
          </ul>
        </div>
      </div>
    );

    return (
      <div key={category} className="data-category">
        <h3>
          <span className="category-icon">{categoryData.icon}</span>
          {categoryData.title}
        </h3>
        <div className="category-grid">
          {fields.map(field => {
            const value = data[field];
            
            return (
              <div key={field} className={`data-item ${field}-item`}>
                {field === 'experience' ? (
                  <div className="experience-list">
                    {value.map((exp, i) => renderExperience(exp))}
                  </div>
                ) : field === 'projects' ? (
                  <div className="projects-list">
                    {value.map((project, i) => renderProject(project))}
                  </div>
                ) : field === 'skills' ? (
                  <div className="skills-categories">
                    {Object.entries(value).map(([category, skills]) => (
                      <div key={category} className="skill-category">
                        <h4>{category}</h4>
                        <div className="skills-list">
                          {skills.map((skill, i) => (
                            <span key={i} className="skill-tag">{skill}</span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : field === 'certifications' ? (
                  <div className="certifications-list">
                    {value.map((cert, i) => (
                      <div key={i} className="certification-item">
                        <h4>{cert.name}</h4>
                        <p>{cert.issuer} - {cert.date}</p>
                      </div>
                    ))}
                  </div>
                ) : field === 'education' ? (
                  <div className="education-details">
                    <h4>{value.degree} in {value.major}</h4>
                    <p>{value.university}</p>
                    <p>CGPA: {value.cgpa}</p>
                    <p>Graduation: {value.graduationYear}</p>
                  </div>
                ) : field === 'ats_analysis' ? (
                  renderAtsAnalysis(value)
                ) : field === 'skills_analysis' ? (
                  renderSkillsAnalysis(value)
                ) : (
                  <span>{value}</span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>PDF Data Extractor</h1>
        <p style={{ fontSize: '1rem', opacity: 0.8, marginTop: '8px' }}>
          Extract information from your PDF documents
        </p>
      </header>
      
      <div className="main-container">
        {!data && (
          <form onSubmit={handleSubmit} className="upload-form">
            <div className="file-input-container">
              <input
                type="file"
                onChange={handleFileChange}
                accept=".pdf"
                id="file-input"
                ref={fileInputRef}
              />
              <label htmlFor="file-input" className="file-input-label">
                <UploadIcon />
                {file ? file.name : "Choose PDF file"}
              </label>
            </div>
            
            <button 
              type="submit" 
              disabled={!file || loading}
              className="submit-button"
            >
              {loading ? (
                <>
                  <LoadingSpinner />
                  Processing...
                </>
              ) : (
                'Extract Data'
              )}
            </button>
          </form>
        )}

        {error && (
          <div className="error-message">
            <strong>Error: </strong>{error}
          </div>
        )}

        {data && (
          <div className="results" ref={resultsRef}>
            <h2>Extracted Data</h2>
            <div className="categories-container">
              {Object.entries(dataCategories).map(([category, categoryData]) => 
                renderCategoryData(category, categoryData)
              )}
            </div>
            
            <div className="results-footer">
              <button 
                className="reset-button"
                onClick={handleReset}
              >
                <span className="reset-icon">↺</span>
                Analyze Another Resume
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;