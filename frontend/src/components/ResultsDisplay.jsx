import React, { useState } from 'react';
import { FaDownload, FaCopy, FaCheck, FaChevronDown, FaChevronUp } from 'react-icons/fa';

const ResultsDisplay = ({ results, onDownloadTranscript, onDownloadSummary }) => {
  const [copiedTranscript, setCopiedTranscript] = useState(false);
  const [copiedSummary, setCopiedSummary] = useState(false);
  const [showSegments, setShowSegments] = useState(false);

  const copyToClipboard = async (text, setCopied) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  const formatTime = (seconds) => {
    if (!seconds && seconds !== 0) return 'N/A';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const { transcript, summary, metadata, segments } = results;

  return (
    <div className="results-display">
      {/* Metadata */}
      {metadata && (
        <div className="metadata">
          <div className="metadata-item">
            <span className="label">Language:</span>
            <span className="value">{metadata.language || 'Unknown'}</span>
          </div>
          {metadata.duration && (
            <div className="metadata-item">
              <span className="label">Duration:</span>
              <span className="value">{formatTime(metadata.duration)}</span>
            </div>
          )}
        </div>
      )}

      {/* Summary Section */}
      <div className="result-section">
        <div className="section-header">
          <h3>📌 Summary</h3>
          <div className="action-buttons">
            <button
              onClick={() => copyToClipboard(summary, setCopiedSummary)}
              className="action-btn"
              title="Copy summary"
            >
              {copiedSummary ? <FaCheck /> : <FaCopy />}
            </button>
            <button
              onClick={() => onDownloadSummary(summary)}
              className="action-btn"
              title="Download summary"
            >
              <FaDownload />
            </button>
          </div>
        </div>
        <div className="content-box">
          <p className="summary-text">{summary}</p>
        </div>
      </div>

      {/* Transcript Section */}
      <div className="result-section">
        <div className="section-header">
          <h3>🗣️ Full Transcript</h3>
          <div className="action-buttons">
            <button
              onClick={() => copyToClipboard(transcript, setCopiedTranscript)}
              className="action-btn"
              title="Copy transcript"
            >
              {copiedTranscript ? <FaCheck /> : <FaCopy />}
            </button>
            <button
              onClick={() => onDownloadTranscript(transcript)}
              className="action-btn"
              title="Download transcript"
            >
              <FaDownload />
            </button>
          </div>
        </div>
        <div className="content-box">
          <textarea
            value={transcript}
            readOnly
            className="transcript-text"
            rows={8}
          />
        </div>
      </div>

      {/* Segments Section (Optional) */}
      {segments && segments.length > 0 && (
        <div className="result-section">
          <div className="section-header">
            <h3>⏱️ Timed Segments</h3>
            <button
              onClick={() => setShowSegments(!showSegments)}
              className="action-btn"
              title="Toggle segments view"
            >
              {showSegments ? <FaChevronUp /> : <FaChevronDown />}
            </button>
          </div>
          {showSegments && (
            <div className="content-box">
              <div className="segments-list">
                {segments.map((segment, index) => (
                  <div key={index} className="segment-item">
                    <div className="segment-time">
                      {formatTime(segment.start)} - {formatTime(segment.end)}
                    </div>
                    <div className="segment-text">{segment.text}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ResultsDisplay;