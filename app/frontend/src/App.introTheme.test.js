import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import App from './App';

jest.mock('./services/apiInterceptors', () => ({
  setupInterceptors: jest.fn(),
}));

jest.mock('./utils/AuthContext', () => ({
  AuthProvider: ({ children }) => <>{children}</>,
  useAuth: () => ({ isLoggedIn: true, authLoading: false, logout: jest.fn() }),
}));

jest.mock('./utils/ToastContext', () => ({
  ToastProvider: ({ children }) => <>{children}</>,
  useToast: () => ({ addToast: jest.fn() }),
}));

jest.mock('./utils/SearchContext', () => ({
  SearchProvider: ({ children }) => <>{children}</>,
  useSearch: () => ({ searchResults: [] }),
}));

jest.mock('./components/ErrorBoundary', () => ({ children }) => <>{children}</>);
jest.mock('./components/Toast', () => () => null);
jest.mock('./components/searchBar/Search', () => () => null);
jest.mock('./components/leafletMap/MapArea', () => () => <div>Map</div>);
jest.mock('./components/leafletMap/MeloSummary', () => () => <div>Summary</div>);
jest.mock('./components/LoadingScreen', () => () => <div>Loading</div>);
jest.mock('./pages/Home', () => () => <div>Home</div>);

jest.mock('./components/PrivateRoute', () => {
  const { Outlet } = require('react-router-dom');
  return function PrivateRouteMock() {
    return <Outlet />;
  };
});

jest.mock('./pages/Intro', () => () => <div>Intro Page</div>);
jest.mock('./pages/Register', () => () => <div>Register</div>);
jest.mock('./pages/Login', () => () => <div>Login</div>);
jest.mock('./pages/UploadForm', () => () => <div>Upload</div>);
jest.mock('./pages/Profile', () => () => <div>Profile</div>);
jest.mock('./pages/AdminDashboard', () => () => <div>Admin</div>);
jest.mock('./pages/MyUploads', () => () => <div>MyUploads</div>);

describe('App intro theme toggle', () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.localStorage.setItem('melo-dark-mode', 'false');
    window.history.pushState({}, '', '/intro');
  });

  it('shows dark mode toggle on intro and switches document theme', async () => {
    render(<App isLoggedIn={true} />);

    const toggleButton = await screen.findByRole('button', { name: /toggle dark mode/i });
    expect(toggleButton).toBeInTheDocument();

    await waitFor(() => {
      expect(document.documentElement.getAttribute('data-theme')).toBe('light');
    });

    fireEvent.click(toggleButton);

    await waitFor(() => {
      expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
    });

    fireEvent.click(toggleButton);

    await waitFor(() => {
      expect(document.documentElement.getAttribute('data-theme')).toBe('light');
    });
  });
});
