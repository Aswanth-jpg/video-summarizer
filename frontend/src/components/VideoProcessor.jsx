import React, { useState } from 'react';
import { FaPlay, FaDownload, FaCog, FaEye, FaEyeSlash } from 'react-icons/fa';
import LoadingSpinner from './LoadingSpinner';
import ResultsDisplay from './ResultsDisplay';

const VideoProcessor = () => {
  const [url, setUrl] = useState('');
  const [geminiKey, setGeminiKey] = useState('');
  const [showApiKey, setShowApiKey] = useState(false);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState('');
  const [showSettings, setShowSettings] = useState(false);

  const isValidYouTubeUrl = (url) => {
    const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+/;
    return youtubeRegex.test(url);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!url.trim()) {
      setError('Please enter a YouTube URL');
      return;
    }

    if (!isValidYouTubeUrl(url)) {
      setError('Please enter a valid YouTube URL');
      return;
    }

    setLoading(true);
    setError('');
    setResults(null);

    try {
      const response = await fetch('/api/process', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          url: url,
          gemini_api_key: geminiKey || undefined
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to process video');
      }

      const data = await response.json();
      setResults(data);
    } catch (err) {
      setError(err.message || 'An error occurred while processing the video');
    } finally {
      setLoading(false);
    }
  };

  const downloadFile = async (content, filename, endpoint) => {
    try {
      const response = await fetch(`/api/download/${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ [endpoint]: content }),
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    } catch (err) {
      console.error('Download failed:', err);
    }
  };

  return (
    <div className="video-processor">
      <div className="processor-card">
        <form onSubmit={handleSubmit} className="url-form">
          <div className="input-group">
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="Enter YouTube video URL..."
              className="url-input"
              disabled={loading}
            />
            <button
              type="button"
              onClick={() => setShowSettings(!showSettings)}
              className="settings-btn"
              title="API Settings"
            >
              <FaCog />
            </button>
            <button
              type="submit"
              disabled={loading || !url.trim()}
              className="process-btn"
            >
              {loading ? <LoadingSpinner size="small" /> : <FaPlay />}
              {loading ? 'Processing...' : 'Summarize'}
            </button>
          </div>

          {showSettings && (
            <div className="settings-panel">
              <div className="setting-item">
                <label htmlFor="gemini-key">Gemini API Key (Optional)</label>
                <div className="password-input">
                  <input
                    id="gemini-key"
                    type={showApiKey ? 'text' : 'password'}
                    value={geminiKey}
                    onChange={(e) => setGeminiKey(e.target.value)}
                    placeholder="Enter your Gemini API key..."
                    className="api-key-input"
                  />
                  <button
                    type="button"
                    onClick={() => setShowApiKey(!showApiKey)}
                    className="toggle-visibility"
                  >
                    {showApiKey ? <FaEyeSlash /> : <FaEye />}
                  </button>
                </div>
                <small className="help-text">
                  Get your API key from{' '}
                  <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener noreferrer">
                    Google AI Studio
                  </a>
                </small>
              </div>
            </div>
          )}
        </form>

        {error && (
          <div className="error-message">
            <p>{error}</p>
          </div>
        )}

        {loading && (
          <div className="loading-container">
            <LoadingSpinner />
            <div className="loading-steps">
              <p>📥 Downloading audio...</p>
              <p>📝 Transcribing with AI...</p>
              <p>✨ Generating summary...</p>
            </div>
          </div>
        )}

        {results && (
          <ResultsDisplay
            results={results}
            onDownloadTranscript={(transcript) => 
              downloadFile(transcript, 'transcript.txt', 'transcript')
            }
            onDownloadSummary={(summary) => 
              downloadFile(summary, 'summary.txt', 'summary')
            }
          />
        )}
      </div>
    </div>
  );
};

export default VideoProcessor;