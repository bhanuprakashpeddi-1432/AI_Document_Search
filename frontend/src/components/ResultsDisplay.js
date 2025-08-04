import React, { useState } from 'react';
import './ResultsDisplay.css';

const ResultsDisplay = ({ results, onNewSearch }) => {
  const [expandedSources, setExpandedSources] = useState({});

  if (!results) {
    return null;
  }

  const toggleSourceExpansion = (questionIndex) => {
    setExpandedSources(prev => ({
      ...prev,
      [questionIndex]: !prev[questionIndex]
    }));
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  const formatProcessingTime = (time) => {
    if (time < 1) {
      return `${Math.round(time * 1000)}ms`;
    }
    return `${time.toFixed(2)}s`;
  };

  return (
    <div className="results-container">
      <div className="results-header">
        <div className="results-title">
          <h2>Analysis Results</h2>
          <div className="results-meta">
            <span className="processing-time">
              ⚡ Processed in {formatProcessingTime(results.processing_time)}
            </span>
            <span className="document-info">
              📄 Document ID: {results.document_hash?.substring(0, 8)}...
            </span>
          </div>
        </div>
        <button onClick={onNewSearch} className="btn-new-search">
          New Search
        </button>
      </div>

      <div className="results-content">
        {results.answers.map((answer, index) => (
          <div key={index} className="result-item">
            <div className="question-section">
              <div className="question-header">
                <h3>Question {index + 1}</h3>
                <button
                  onClick={() => copyToClipboard(answer)}
                  className="copy-btn"
                  title="Copy answer"
                >
                  📋
                </button>
              </div>
              <div className="question-text">
                {/* Assuming we have access to original questions - if not, remove this */}
                {results.originalQuestions?.[index] || `Question ${index + 1}`}
              </div>
            </div>

            <div className="answer-section">
              <div className="answer-content">
                {answer}
              </div>
            </div>

            {results.sources && results.sources[index] && results.sources[index].length > 0 && (
              <div className="sources-section">
                <div className="sources-header">
                  <button
                    onClick={() => toggleSourceExpansion(index)}
                    className="sources-toggle"
                  >
                    <span>📚 Sources ({results.sources[index].length})</span>
                    <span className={`toggle-icon ${expandedSources[index] ? 'expanded' : ''}`}>
                      ▼
                    </span>
                  </button>
                </div>

                {expandedSources[index] && (
                  <div className="sources-content">
                    {results.sources[index].map((source, sourceIndex) => (
                      <div key={sourceIndex} className="source-chunk">
                        <div className="source-header">
                          <span className="source-info">
                            {source.page_number && (
                              <span className="page-number">Page {source.page_number}</span>
                            )}
                            {source.score && (
                              <span className="confidence-score">
                                Confidence: {(source.score * 100).toFixed(1)}%
                              </span>
                            )}
                          </span>
                          <button
                            onClick={() => copyToClipboard(source.text)}
                            className="copy-btn-small"
                            title="Copy source text"
                          >
                            📋
                          </button>
                        </div>
                        <div className="source-text">
                          {source.text}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="results-footer">
        <div className="footer-info">
          <p>
            ✨ Powered by advanced AI with hybrid vector search and GPT-4 reasoning
          </p>
          <p>
            🔒 All data is processed securely and not stored permanently
          </p>
        </div>
      </div>
    </div>
  );
};

export default ResultsDisplay;
