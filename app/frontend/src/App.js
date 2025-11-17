// src/App.js
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useNavigate } from 'react-router-dom';

import Home from './pages/Home';
import Register from './pages/Register';
import Login from './pages/Login';
import FileUpload from './pages/UploadForm';
import Intro from './pages/Intro';
import ProfileTest from './pages/Profile';
import Search from './components/search_bar/Search';
import PrivateRoute from './components/PrivateRoute';
import './App.css';
import { dedupeStories } from './utils/storyUtils';

const App = () => {
  return (
    <Router>
      <AppContent />
    </Router>
  );
};

const AppContent = () => {
  const [searchResults, setSearchResults] = React.useState([]);
  const [sidebarOpen, setSidebarOpen] = React.useState(false);
  const [isLoggedIn, setIsLoggedIn] = React.useState(!!localStorage.getItem('token'));
  const navigate = useNavigate();

  const handleTopbarSearchResult = React.useCallback((results = []) => {
    setSearchResults(dedupeStories(Array.isArray(results) ? results : []));
  }, []);

  // Check login status on mount and when token changes
  React.useEffect(() => {
    const checkLoginStatus = () => {
      setIsLoggedIn(!!localStorage.getItem('token'));
    };

    window.addEventListener('storage', checkLoginStatus);
    return () => window.removeEventListener('storage', checkLoginStatus);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('token');
    setIsLoggedIn(false);
    navigate('/login');
  };

  const handleUploadClick = () => {
    if (!isLoggedIn) {
      navigate('/login');
    } else {
      navigate('/upload');
    }
  };

  return (
    <div className="app-shell">
        {/* Fixed Top Bar with Search and Menu */}
        <header className="topbar-fixed">
          <button 
            className="menu-button" 
            onClick={() => setSidebarOpen(!sidebarOpen)}
            aria-label="Toggle menu"
            title="Menu"
          >
            <span></span>
            <span></span>
            <span></span>
          </button>
          
          {/* Right side action buttons - MOVED BEFORE SEARCH */}
          <div className="topbar-actions" style={{position: 'absolute', right: '1rem'}}>
            <button 
              className="topbar-action-btn upload-btn"
              onClick={handleUploadClick}
              title="Upload news"
              aria-label="Upload"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </button>
            
            <button 
              className={`topbar-action-btn auth-btn ${isLoggedIn ? 'logout' : 'login'}`}
              onClick={isLoggedIn ? handleLogout : () => navigate('/login')}
              title={isLoggedIn ? 'Logout' : 'Login'}
              aria-label={isLoggedIn ? 'Logout' : 'Login'}
            >
              {isLoggedIn ? (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                  <polyline points="16 17 21 12 16 7" />
                  <line x1="21" y1="12" x2="9" y2="12" />
                </svg>
              ) : (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M15 3H9a2 2 0 0 0-2 2v4" />
                  <path d="M9 21h6a2 2 0 0 0 2-2v-4" />
                  <polyline points="8 12 3 12 3 7" />
                  <polyline points="16 12 21 12 21 17" />
                </svg>
              )}
            </button>
          </div>

          <Search onSearchResult={handleTopbarSearchResult} showAsTopbar={true} />

          <nav className={`topbar-nav ${sidebarOpen ? 'open' : ''}`}>
            <Link to="/" className="nav-link">Home</Link>
            <Link to="/upload" className="nav-link">Upload</Link>
            <Link to={isLoggedIn ? '#' : '/login'} className="nav-link" onClick={isLoggedIn ? handleLogout : undefined}>
              {isLoggedIn ? 'Logout' : 'Login'}
            </Link>
          </nav>
        </header>

        {/* Main content */}
        <main className="main">
          <Routes>
            <Route path="/" element={<Home searchResults={searchResults} onSearchResult={handleTopbarSearchResult} />} />
            <Route path="/register" element={<Register />} />
            <Route path="/login" element={<Login onLoginSuccess={() => setIsLoggedIn(true)} />} />
            <Route path="/intro" element={<Intro />} />
            <Route path="/search" element={<Search onSearchResult={handleTopbarSearchResult} />} />

            <Route element={<PrivateRoute />}>
              <Route path="/profile" element={<ProfileTest />} />
              <Route path="/upload" element={<FileUpload />} />
            </Route>
          </Routes>
        </main>
      </div>
    );
  };

  export default App;
