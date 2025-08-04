import React, { useState } from 'react';
import axios from 'axios';
import SearchForm from './components/SearchForm';
import ResultsDisplay from './components/ResultsDisplay';
import './App.css';

const App = () => {
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [originalQuestions, setOriginalQuestions] = useState([]);

  // API configuration
  const API_BASE_URL = process.env.REACT_APP_API_URL || '';
  const API_TOKEN = process.env.REACT_APP_API_TOKEN || 'hackrx-default-token';

  const handleSearch = async (searchData) => {
    setLoading(true);
    setError(null);
    setResults(null);
    setOriginalQuestions(searchData.questions);

    try {
      const response = await axios.post(
        `${API_BASE_URL}/hackrx/run`,
        searchData,
        {
          headers: {
            'Authorization': `Bearer ${API_TOKEN}`,
            'Content-Type': 'application/json'
          },
          timeout: 120000 // 2 minute timeout
        }
      );

      // Add original questions to results for display
      const resultsWithQuestions = {
        ...response.data,
        originalQuestions: searchData.questions
      };

      setResults(resultsWithQuestions);
    } catch (err) {
      console.error('API Error:', err);
      
      let errorMessage = 'An unexpected error occurred. Please try again.';
      
      if (err.response) {
        // Server responded with error status
        switch (err.response.status) {
          case 400:
            errorMessage = err.response.data?.detail || 'Invalid request. Please check your input.';
            break;
          case 401:
            errorMessage = 'Authentication failed. Please check your API token.';
            break;
          case 403:
            errorMessage = 'Access denied. Please check your permissions.';
            break;
          case 429:
            errorMessage = 'Too many requests. Please wait a moment and try again.';
            break;
          case 500:
            errorMessage = 'Server error. Please try again later.';
            break;
          default:
            errorMessage = `Server error (${err.response.status}). Please try again.`;
        }
      } else if (err.request) {
        // Network error
        errorMessage = 'Network error. Please check your connection and try again.';
      } else if (err.code === 'ECONNABORTED') {
        // Timeout error
        errorMessage = 'Request timeout. The document may be too large or complex. Please try again.';
      }
      
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleNewSearch = () => {
    setResults(null);
    setError(null);
    setOriginalQuestions([]);
  };

  return (
    <div className="app">
      <div className="app-background">
        <div className="background-pattern"></div>
      </div>
      
      <header className="app-header">
        <div className="header-content">
          <h1>HackRX Intelligence</h1>
          <p>Advanced Document Analysis & Question Answering System</p>
        </div>
      </header>

      <main className="app-main">
        {!results && !loading && (
          <SearchForm onSubmit={handleSearch} loading={loading} />
        )}

        {error && (
          <div className="error-container">
            <div className="error-content">
              <div className="error-icon">⚠️</div>
              <h3>Something went wrong</h3>
              <p>{error}</p>
              <button onClick={handleNewSearch} className="btn-retry">
                Try Again
              </button>
            </div>
          </div>
        )}

        {results && !loading && (
          <ResultsDisplay results={results} onNewSearch={handleNewSearch} />
        )}
      </main>

      <footer className="app-footer">
        <div className="footer-content">
          <p>
            Built with ❤️ for HackRX Challenge | 
            Powered by FastAPI, React, GPT-4, and Pinecone
          </p>
          <div className="tech-stack">
            <span className="tech-badge">FastAPI</span>
            <span className="tech-badge">React</span>
            <span className="tech-badge">GPT-4</span>
            <span className="tech-badge">Pinecone</span>
            <span className="tech-badge">PostgreSQL</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
