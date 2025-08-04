import React, { useState } from 'react';
import './SearchForm.css';

const SearchForm = ({ onSubmit, loading }) => {
  const [documentUrl, setDocumentUrl] = useState('');
  const [questions, setQuestions] = useState('');
  const [errors, setErrors] = useState({});

  const validateForm = () => {
    const newErrors = {};

    // Validate document URL
    if (!documentUrl.trim()) {
      newErrors.documentUrl = 'Document URL is required';
    } else {
      try {
        new URL(documentUrl);
      } catch {
        newErrors.documentUrl = 'Please enter a valid URL';
      }
    }

    // Validate questions
    if (!questions.trim()) {
      newErrors.questions = 'At least one question is required';
    } else {
      const questionsList = questions.split('\n').filter(q => q.trim());
      if (questionsList.length === 0) {
        newErrors.questions = 'At least one question is required';
      } else if (questionsList.length > 10) {
        newErrors.questions = 'Maximum 10 questions allowed';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    const questionsList = questions
      .split('\n')
      .map(q => q.trim())
      .filter(q => q);

    onSubmit({
      documents: documentUrl.trim(),
      questions: questionsList
    });
  };

  const handleLoadSample = () => {
    setDocumentUrl('https://hackrx.blob.core.windows.net/assets/policy.pdf');
    setQuestions(`What is the grace period for premium payment?
What is the waiting period for cataract surgery?
What are the eligibility criteria for the policy?
What is covered under hospitalization benefits?
Are there any exclusions for pre-existing conditions?`);
    setErrors({});
  };

  return (
    <div className="search-form-container">
      <div className="search-form-header">
        <h2>HackRX Document Query System</h2>
        <p>Upload a document and ask questions to get intelligent answers with source traceability</p>
      </div>

      <form onSubmit={handleSubmit} className="search-form">
        <div className="form-group">
          <label htmlFor="documentUrl">Document URL *</label>
          <input
            type="url"
            id="documentUrl"
            value={documentUrl}
            onChange={(e) => setDocumentUrl(e.target.value)}
            placeholder="https://example.com/document.pdf"
            className={errors.documentUrl ? 'error' : ''}
            disabled={loading}
          />
          {errors.documentUrl && <span className="error-message">{errors.documentUrl}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="questions">
            Questions * 
            <span className="label-hint">(Enter each question on a new line, max 10)</span>
          </label>
          <textarea
            id="questions"
            value={questions}
            onChange={(e) => setQuestions(e.target.value)}
            placeholder="What is the grace period for premium payment?
What is the waiting period for cataract surgery?
What are the eligibility criteria?"
            rows="6"
            className={errors.questions ? 'error' : ''}
            disabled={loading}
          />
          {errors.questions && <span className="error-message">{errors.questions}</span>}
          <div className="question-count">
            {questions.split('\n').filter(q => q.trim()).length} / 10 questions
          </div>
        </div>

        <div className="form-actions">
          <button
            type="button"
            onClick={handleLoadSample}
            className="btn-secondary"
            disabled={loading}
          >
            Load Sample Data
          </button>
          
          <button
            type="submit"
            className="btn-primary"
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="spinner"></span>
                Processing...
              </>
            ) : (
              'Analyze Document'
            )}
          </button>
        </div>
      </form>

      {loading && (
        <div className="processing-status">
          <div className="status-item">
            <span className="status-icon">📄</span>
            <span>Processing document...</span>
          </div>
          <div className="status-item">
            <span className="status-icon">🔍</span>
            <span>Analyzing questions...</span>
          </div>
          <div className="status-item">
            <span className="status-icon">🧠</span>
            <span>Generating answers...</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default SearchForm;
