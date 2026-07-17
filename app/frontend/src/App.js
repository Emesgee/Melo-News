import React, { Suspense, useEffect, useRef } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useNavigate, useLocation } from 'react-router-dom';

import Home from './pages/Home';
import Search from './components/searchBar/Search';
import PrivateRoute from './components/PrivateRoute';
import ErrorBoundary from './components/ErrorBoundary';
import Toast from './components/Toast';
import LoadingScreen from './components/LoadingScreen';
import { DarkModeProvider, useDarkMode } from './utils/DarkModeContext';
import { AuthProvider, useAuth } from './utils/AuthContext';
import { ToastProvider, useToast } from './utils/ToastContext';
import { SearchProvider } from './utils/SearchContext';
import { setupInterceptors } from './services/apiInterceptors';
import './App.css';

// Lazy-loaded routes. The web is the reader + moderation surface; reporting is
// the Android app's job (ADR-0001/0007), so there is no web upload route —
// /report is a static "get the app" notice instead.
const Register = React.lazy(() => import('./pages/Register'));
const Login = React.lazy(() => import('./pages/Login'));
const GetTheApp = React.lazy(() => import('./pages/GetTheApp'));
const Moderation = React.lazy(() => import('./pages/Moderation'));
const EventsFeed = React.lazy(() => import('./pages/EventsFeed'));
const EventDetail = React.lazy(() => import('./pages/EventDetail'));

function App({ isLoggedIn: isLoggedInProp }) {
  return (
    <ErrorBoundary>
      <ToastProvider>
        <AuthProvider initialLoggedIn={isLoggedInProp}>
          <SearchProvider>
            <DarkModeProvider>
              <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
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
  const [searchOpen, setSearchOpen] = React.useState(false);
  const [accountOpen, setAccountOpen] = React.useState(false);
  const accountRef = useRef(null);
  const { isDark, toggle: toggleDark } = useDarkMode();
  const { isLoggedIn, isModerator, authLoading, logout } = useAuth();
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

  // Close the account menu on outside click or route change
  useEffect(() => {
    if (!accountOpen) return undefined;
    const onClick = (e) => {
      if (accountRef.current && !accountRef.current.contains(e.target)) setAccountOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [accountOpen]);

  useEffect(() => { setAccountOpen(false); }, [location.pathname]);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const handleReportClick = () => {
    // The web has no upload lane — point would-be reporters at the app.
    navigate('/report');
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

      {/* Fixed top bar */}
      <header className="topbar-fixed">
        {/* Brand → the one reader screen */}
        <Link to="/" className="topbar-brand" aria-label="Melo News — home">
          <span className="brand-mark">M</span>
          <span className="brand-name">Melo News</span>
        </Link>

        {/* Primary views (becomes a single Map/List toggle once the views merge) */}
        <nav className="topbar-views" aria-label="Primary views">
          <Link to="/" className={`view-link${location.pathname === '/' ? ' active' : ''}`}>Map</Link>
          <Link to="/events" className={`view-link${location.pathname === '/events' ? ' active' : ''}`}>Events</Link>
        </nav>

        <span className="topbar-spacer" />

        {/* Search */}
        <button
          className="search-icon-btn"
          onClick={() => setSearchOpen((o) => !o)}
          aria-label="Toggle search"
          title="Search"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.35-4.35" />
          </svg>
        </button>
        <div className="search-topbar-container" style={{ display: searchOpen ? 'flex' : 'none' }}>
          <Search />
        </div>

        {/* Right-side actions */}
        <div className="topbar-actions">
          {/* Report → static "get the app" notice (web has no upload lane) */}
          <button
            className="topbar-action-btn submit-btn"
            onClick={handleReportClick}
            title="How to report"
            aria-label="How to report"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <span className="submit-label">Report</span>
          </button>

          {/* Dark mode toggle (kept persistent) */}
          <button
            className="topbar-action-btn dark-btn"
            onClick={toggleDark}
            title={isDark ? 'Light mode' : 'Dark mode'}
            aria-label="Toggle dark mode"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              {isDark
                ? <circle cx="12" cy="12" r="5" />
                : <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />}
            </svg>
          </button>

          {/* Account */}
          {isLoggedIn ? (
            <div className="account-menu" ref={accountRef}>
              <button
                className="topbar-action-btn account-btn"
                onClick={() => setAccountOpen((o) => !o)}
                aria-haspopup="true"
                aria-expanded={accountOpen}
                title="Account"
                aria-label="Account menu"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
              </button>
              {accountOpen && (
                <div className="account-dropdown" role="menu">
                  {isModerator && (
                    <button role="menuitem" onClick={() => { setAccountOpen(false); navigate('/moderation'); }}>
                      Moderation
                    </button>
                  )}
                  <button role="menuitem" className="account-logout" onClick={() => { setAccountOpen(false); handleLogout(); }}>
                    Log out
                  </button>
                </div>
              )}
            </div>
          ) : (
            <button
              className="topbar-action-btn auth-btn login"
              onClick={() => navigate('/login')}
              title="Log in"
              aria-label="Log in"
            >
              Log in
            </button>
          )}
        </div>
      </header>

      {/* Main content */}
      <main id="main-content" className="main" ref={mainRef} tabIndex={-1}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/register" element={<Suspense fallback={null}><Register /></Suspense>} />
          <Route path="/login" element={<Suspense fallback={null}><Login /></Suspense>} />
          <Route path="/events" element={<Suspense fallback={null}><EventsFeed /></Suspense>} />
          <Route path="/events/:id" element={<Suspense fallback={null}><EventDetail /></Suspense>} />
          <Route path="/report" element={<Suspense fallback={null}><GetTheApp /></Suspense>} />

          <Route element={<PrivateRoute />}>
            <Route path="/moderation" element={<Suspense fallback={null}><Moderation /></Suspense>} />
          </Route>
        </Routes>
      </main>
    </div>
  );
};

export default App;