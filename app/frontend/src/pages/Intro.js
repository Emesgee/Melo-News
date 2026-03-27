// src/pages/Intro.js
import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './Intro.css';

const Intro = () => {
  const navigate = useNavigate();

  useEffect(() => {
    // Redirect to Home page after 5 seconds
    const timer = setTimeout(() => {
      navigate('/');
    }, 5000);

    // Cleanup the timer if the component unmounts
    return () => clearTimeout(timer);
  }, [navigate]);

  const handleSkip = () => {
    navigate('/');
  };

  return (
    <div className="intro-container">
      <h1>Welcome to MeloNews</h1>
      <p>"Where every beat meets the story".</p>
      <button className="intro-skip-btn" onClick={handleSkip}>
        Continue to app
      </button>
    </div>
  );
};

export default Intro;
