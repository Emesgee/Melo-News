// src/App.js
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

import Home from './pages/Home';
import Register from './pages/Register';
import Login from './pages/Login';
import FileUpload from './pages/UploadForm';
import Intro from './pages/Intro';
import ProfileTest from './pages/Profile';
import Search from './components/search_bar/Search';

const App = () => {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/register" element={<Register />} />
        <Route path="/login" element={<Login />} />
        <Route path="/upload" element={<FileUpload />} />
        <Route path="/intro" element={<Intro />} />
        <Route path="/profile" element={<ProfileTest />} />
        <Route path="/search" element={<Search />} />
      </Routes>
    </Router>
  );
};

export default App;
