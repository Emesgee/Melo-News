import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import '@testing-library/jest-dom';
import PrivateRoute from './PrivateRoute';

// Mock AuthContext
const mockUseAuth = jest.fn();
jest.mock('../utils/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

const renderWithRouter = (initialRoute = '/protected') => {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <Routes>
        <Route element={<PrivateRoute />}>
          <Route path="/protected" element={<div>Protected Content</div>} />
        </Route>
        <Route path="/login" element={<div>Login Page</div>} />
      </Routes>
    </MemoryRouter>
  );
};

describe('PrivateRoute', () => {
  it('shows nothing while auth is loading', () => {
    mockUseAuth.mockReturnValue({ isLoggedIn: false, authLoading: true });
    const { container } = renderWithRouter();
    expect(container.textContent).toBe('');
  });

  it('renders protected content when authenticated', async () => {
    mockUseAuth.mockReturnValue({ isLoggedIn: true, authLoading: false });
    renderWithRouter();
    await waitFor(() => {
      expect(screen.getByText('Protected Content')).toBeInTheDocument();
    });
  });

  it('redirects to /login when not authenticated', async () => {
    mockUseAuth.mockReturnValue({ isLoggedIn: false, authLoading: false });
    renderWithRouter();
    await waitFor(() => {
      expect(screen.getByText('Login Page')).toBeInTheDocument();
    });
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });
});
