import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import '@testing-library/jest-dom';
import Login from './Login';

// Mock API
const mockLoginUser = jest.fn();
jest.mock('../services/api', () => ({
  loginUser: (...args) => mockLoginUser(...args),
}));

// Mock AuthContext
const mockLogin = jest.fn();
jest.mock('../utils/AuthContext', () => ({
  useAuth: () => ({ login: mockLogin }),
}));

// Mock navigate
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

beforeEach(() => {
  jest.clearAllMocks();
});

const renderLogin = () =>
  render(
    <MemoryRouter>
      <Login />
    </MemoryRouter>
  );

describe('Login', () => {
  it('renders email and password fields', () => {
    renderLogin();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it('renders login and register buttons', () => {
    renderLogin();
    expect(screen.getByRole('button', { name: /^login$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /register/i })).toBeInTheDocument();
  });

  it('submits credentials and calls login on success', async () => {
    mockLoginUser.mockResolvedValue({ data: { success: true } });

    renderLogin();

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'test@test.com' } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'password123' } });

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /^login$/i }));
    });

    expect(mockLoginUser).toHaveBeenCalledWith({ email: 'test@test.com', password: 'password123' });
    expect(mockLogin).toHaveBeenCalled();
    expect(mockNavigate).toHaveBeenCalledWith('/');
  });

  it('shows error message on login failure', async () => {
    mockLoginUser.mockRejectedValue({
      response: { data: { error: 'Invalid credentials' } },
    });

    renderLogin();

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'bad@test.com' } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'wrong' } });

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /^login$/i }));
    });

    await waitFor(() => {
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
    });

    expect(mockLogin).not.toHaveBeenCalled();
  });

  it('shows fallback error message when no error detail', async () => {
    mockLoginUser.mockRejectedValue(new Error('Network error'));

    renderLogin();

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'a@b.com' } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'x' } });

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /^login$/i }));
    });

    await waitFor(() => {
      expect(screen.getByText('Login failed')).toBeInTheDocument();
    });
  });

  it('navigates to register page on Register click', () => {
    renderLogin();
    fireEvent.click(screen.getByRole('button', { name: /register/i }));
    expect(mockNavigate).toHaveBeenCalledWith('/register');
  });
});
