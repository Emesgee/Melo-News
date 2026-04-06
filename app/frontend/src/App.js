import React, { Suspense, useEffect, useRef } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useNavigate, useLocation } from 'react-router-dom';

import Home from './pages/Home';
import Search from './components/searchBar/Search';
import PrivateRoute from './components/PrivateRoute';
import ErrorBoundary from './components/ErrorBoundary';
import Toast from './components/Toast';
import MapArea from './components/leafletMap/MapArea';
import MeloSummary from './components/leafletMap/MeloSummary';
import LoadingScreen from './components/LoadingScreen';
import { DarkModeProvider, useDarkMode } from './utils/DarkModeContext';
import { AuthProvider, useAuth } from './utils/AuthContext';
import { ToastProvider, useToast } from './utils/ToastContext';
import { SearchProvider, useSearch } from './utils/SearchContext';
import { setupInterceptors } from './services/apiInterceptors';
import './App.css';

// Lazy-loaded routes
const Register = React.lazy(() => import('./pages/Register'));
const Login = React.lazy(() => import('./pages/Login'));
const FileUpload = React.lazy(() => import('./pages/UploadForm'));
const Intro = React.lazy(() => import('./pages/Intro'));
const ProfileTest = React.lazy(() => import('./pages/Profile'));
const AdminDashboard = React.lazy(() => import('./pages/AdminDashboard'));

function App({ isLoggedIn: isLoggedInProp }) {
  return (
    <ErrorBoundary>
      <ToastProvider>
        <AuthProvider initialLoggedIn={isLoggedInProp}>
          <SearchProvider>
            <DarkModeProvider>
              <Router>
                <AppContent />
                <Toast />
              </Router>
            </DarkModeProvider>
          </SearchProvider>
        </AuthProvider>
      </ToastProvider>
    </ErrorBoundary>
  );
}

const AppContent = () => {
  const { addToast } = useToast();
  const interceptorsSetup = useRef(false);
  const [sidebarOpen, setSidebarOpen] = React.useState(false);
  const [showMeloSummary, setShowMeloSummary] = React.useState(false);
  const [searchOpen, setSearchOpen] = React.useState(false);
  const { isDark, toggle: toggleDark } = useDarkMode();
  const { isLoggedIn, authLoading, logout } = useAuth();
  const { searchResults } = useSearch();
  const navigate = useNavigate();
  const location = useLocation();
  const mainRef = useRef(null);

  // Setup API interceptors once (toast + retry + auth expiry)
  useEffect(() => {
    if (interceptorsSetup.current) return;
    interceptorsSetup.current = true;
    setupInterceptors(addToast, () => {
      logout();
      navigate('/login');
    });
  }, [addToast, logout, navigate]);

  // Focus management: move focus to main content on route change
  useEffect(() => {
    mainRef.current?.focus({ preventScroll: true });
  }, [location.pathname]);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const handleUploadClick = () => {
    if (!isLoggedIn) {
      navigate('/login');
    } else {
      navigate('/upload');
    }
  };

  if (authLoading) {
    return <LoadingScreen />;
  }

  return (
    <div className={`app-shell ${isDark ? 'dark-mode' : ''}`}>
      {/* Skip-nav link for keyboard accessibility */}
      <a href="#main-content" className="skip-nav">
        Skip to main content
      </a>

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

        <button 
          className="search-icon-btn"
          onClick={() => setSearchOpen(!searchOpen)}
          aria-label="Toggle search"
          title="Search"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.35-4.35" />
          </svg>
        </button>

        {/* Search bar - positioned between menu and action buttons */}
        <div className="search-topbar-container" style={{ display: searchOpen ? 'flex' : 'none', flex: 1, minWidth: 0 }}>
          <Search showAsTopbar={true} />
        </div>
        
        {/* Right side action buttons */}
        <div className="topbar-actions">
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

          {/* Dark mode toggle */}
          <button
            className="topbar-action-btn dark-btn"
            onClick={toggleDark}
            title={isDark ? 'Light Mode' : 'Dark Mode'}
            aria-label="Toggle Dark Mode"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              {isDark
                ? <circle cx="12" cy="12" r="5" />
                : <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
              }
            </svg>
          </button>

          <button 
            className="topbar-action-btn summary-btn"
            onClick={() => setShowMeloSummary(true)}
            title="Generate Melo Summary"
            aria-label="Generate Melo Summary"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M4 3h16a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z" />
              <line x1="16" y1="2" x2="16" y2="6" />
              <line x1="8" y1="2" x2="8" y2="6" />
              <line x1="3" y1="10" x2="21" y2="10" />
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

        <nav className={`topbar-nav ${sidebarOpen ? 'open' : ''}`}>
          <Link to="/" className="nav-link">Home</Link>
          <Link to="/upload" className="nav-link">Upload</Link>
          <Link to={isLoggedIn ? '#' : '/login'} className="nav-link" onClick={isLoggedIn ? handleLogout : undefined}>
            {isLoggedIn ? 'Logout' : 'Login'}
          </Link>
        </nav>
      </header>

      {/* Main content */}
      <main id="main-content" className="main" ref={mainRef} tabIndex={-1}>
        {/* Melo Summary Modal */}
        {showMeloSummary && (
          <div className="melo-summary-overlay">
            <MeloSummary 
              onClose={() => setShowMeloSummary(false)}
              initialOpen={true}
            />
          </div>
        )}

        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/register" element={<Suspense fallback={null}><Register /></Suspense>} />
          <Route path="/login" element={<Suspense fallback={null}><Login /></Suspense>} />
          <Route path="/search" element={<Search />} />
          <Route path="/map" element={<MapArea />} />

          <Route element={<PrivateRoute />}>
            <Route path="/intro" element={<Suspense fallback={null}><Intro /></Suspense>} />
            <Route path="/profile" element={<Suspense fallback={null}><ProfileTest /></Suspense>} />
            <Route path="/upload" element={<Suspense fallback={null}><FileUpload /></Suspense>} />
            <Route path="/admin" element={<Suspense fallback={null}><AdminDashboard /></Suspense>} />
          </Route>
        </Routes>
      </main>
    </div>
  );
};

export default App;