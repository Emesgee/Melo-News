import React from 'react';
import { render, screen, act, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { AuthProvider, useAuth } from './AuthContext';

// Mock the API module
const mockCheckAuth = jest.fn();
const mockLogoutUser = jest.fn();
jest.mock('../services/api', () => ({
  checkAuth: (...args) => mockCheckAuth(...args),
  logoutUser: (...args) => mockLogoutUser(...args),
}));

// Test component that exposes auth state
const AuthDisplay = () => {
  const { isLoggedIn, authLoading, login, logout } = useAuth();
  return (
    <div>
      <span data-testid="loading">{String(authLoading)}</span>
      <span data-testid="logged-in">{String(isLoggedIn)}</span>
      <button onClick={login}>login</button>
      <button onClick={logout}>logout</button>
    </div>
  );
};

beforeEach(() => {
  jest.clearAllMocks();
});

describe('AuthProvider', () => {
  it('starts loading and resolves to logged in when checkAuth succeeds', async () => {
    mockCheckAuth.mockResolvedValue({ data: { id: 1 } });

    await act(async () => {
      render(
        <AuthProvider>
          <AuthDisplay />
        </AuthProvider>
      );
    });

    await waitFor(() => {
      expect(screen.getByTestId('loading').textContent).toBe('false');
    });
    expect(screen.getByTestId('logged-in').textContent).toBe('true');
  });

  it('resolves to logged out when checkAuth fails', async () => {
    mockCheckAuth.mockRejectedValue(new Error('Unauthorized'));

    await act(async () => {
      render(
        <AuthProvider>
          <AuthDisplay />
        </AuthProvider>
      );
    });

    await waitFor(() => {
      expect(screen.getByTestId('loading').textContent).toBe('false');
    });
    expect(screen.getByTestId('logged-in').textContent).toBe('false');
  });

  it('login() sets isLoggedIn to true', async () => {
    mockCheckAuth.mockRejectedValue(new Error('Unauthorized'));

    await act(async () => {
      render(
        <AuthProvider>
          <AuthDisplay />
        </AuthProvider>
      );
    });

    await waitFor(() => {
      expect(screen.getByTestId('logged-in').textContent).toBe('false');
    });

    await act(async () => {
      screen.getByText('login').click();
    });

    expect(screen.getByTestId('logged-in').textContent).toBe('true');
  });

  it('logout() calls logoutUser and sets isLoggedIn to false', async () => {
    mockCheckAuth.mockResolvedValue({ data: { id: 1 } });
    mockLogoutUser.mockResolvedValue({});

    await act(async () => {
      render(
        <AuthProvider>
          <AuthDisplay />
        </AuthProvider>
      );
    });

    await waitFor(() => {
      expect(screen.getByTestId('logged-in').textContent).toBe('true');
    });

    await act(async () => {
      screen.getByText('logout').click();
    });

    expect(mockLogoutUser).toHaveBeenCalled();
    expect(screen.getByTestId('logged-in').textContent).toBe('false');
  });

  it('accepts initialLoggedIn prop', async () => {
    mockCheckAuth.mockResolvedValue({});

    await act(async () => {
      render(
        <AuthProvider initialLoggedIn={true}>
          <AuthDisplay />
        </AuthProvider>
      );
    });

    // Before checkAuth resolves, it should use initialLoggedIn
    expect(screen.getByTestId('logged-in').textContent).toBe('true');
  });
});
