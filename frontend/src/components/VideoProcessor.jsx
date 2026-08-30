import React, { useState } from 'react';
import { FaPlay } from 'react-icons/fa';
import LoadingSpinner from './LoadingSpinner';
import ResultsDisplay from './ResultsDisplay';

const VideoProcessor = () => {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState('');

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
          url: url
        }),
      });

      if (!response.ok) {
        let message = 'Failed to process video';
        try {
          const errorData = await response.json();
          message = errorData.detail || message;
        } catch {
          const text = await response.text();
          message = text || message;
        }
        throw new Error(message.replace(/\x1b\[[0-?]*[ -/]*[@-~]/g, ''));
      }

      const data = await response.json();
      setResults(data);
    } catch (err) {
      setError(err.message || 'An error occurred while processing the video');
    } finally {
      setLoading(false);
    }
  };

  const downloadFile = (content, filename) => {
    const blob = new Blob([content], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
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
              type="submit"
              disabled={loading || !url.trim()}
              className="process-btn"
            >
              {loading ? <LoadingSpinner size="small" /> : <FaPlay />}
              {loading ? 'Processing...' : 'Summarize'}
            </button>
          </div>
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
              downloadFile(transcript, 'transcript.txt')
            }
            onDownloadSummary={(summary) => 
              downloadFile(summary, 'summary.txt')
            }
          />
        )}
      </div>
    </div>
  );
};

export default VideoProcessor;