// src/pages/Intro.js
import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './Intro.css';

const Intro = () => {
  const navigate = useNavigate();

  useEffect(() => {
    // Redirect to Home page after 3 seconds
    const timer = setTimeout(() => {
      navigate('/');
    }, 5000);

    // Cleanup the timer if the component unmounts
    return () => clearTimeout(timer);
  }, [navigate]);

  return (
    <div className="intro-container">
      <h1>Welcome to MeloNews</h1>
      <p>“Where every beat meets the story”.</p>
    </div>
  );
};

export default Intro;
