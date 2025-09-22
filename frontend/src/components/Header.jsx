import React from 'react';
import { FaYoutube, FaRobot } from 'react-icons/fa';

const Header = () => {
  return (
    <header className="header">
      <div className="header-content">
        <div className="logo">
          <FaYoutube className="youtube-icon" />
          <h1>YouTube Summarizer</h1>
          <FaRobot className="ai-icon" />
        </div>
        <p className="subtitle">
          Transform YouTube videos into concise summaries using AI-powered transcription and analysis
        </p>
      </div>
    </header>
  );
};

export default Header;