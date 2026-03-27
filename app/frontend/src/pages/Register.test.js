import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import '@testing-library/jest-dom';
import Register from './Register';

// Mock API
const mockRegisterUser = jest.fn();
jest.mock('../services/api', () => ({
  registerUser: (...args) => mockRegisterUser(...args),
}));

const renderRegister = () =>
  render(
    <MemoryRouter>
      <Register />
    </MemoryRouter>
  );

beforeEach(() => {
  jest.clearAllMocks();
});

describe('Register', () => {
  it('renders name, email, and password fields', () => {
    renderRegister();
    expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it('renders a Register submit button', () => {
    renderRegister();
    expect(screen.getByRole('button', { name: /register/i })).toBeInTheDocument();
  });

  it('submits registration data on form submit', async () => {
    mockRegisterUser.mockResolvedValue({ data: { message: 'Registration successful' } });

    renderRegister();

    fireEvent.change(screen.getByLabelText(/name/i), { target: { value: 'John' } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'john@test.com' } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'secret123' } });

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /register/i }));
    });

    expect(mockRegisterUser).toHaveBeenCalledWith({
      username: 'John',
      email: 'john@test.com',
      password: 'secret123',
    });
  });

  it('shows error message on registration failure', async () => {
    mockRegisterUser.mockRejectedValue({
      response: { data: { message: 'Email already exists' } },
    });

    renderRegister();

    fireEvent.change(screen.getByLabelText(/name/i), { target: { value: 'John' } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'dup@test.com' } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'password123' } });

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /register/i }));
    });

    await waitFor(() => {
      expect(screen.getByText('Email already exists')).toBeInTheDocument();
    });
  });

  it('shows fallback error when no message provided', async () => {
    mockRegisterUser.mockRejectedValue(new Error('Network error'));

    renderRegister();

    fireEvent.change(screen.getByLabelText(/name/i), { target: { value: 'X' } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'x@x.com' } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'longpassword' } });

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /register/i }));
    });

    await waitFor(() => {
      expect(screen.getByText('Registration failed')).toBeInTheDocument();
    });
  });

  it('shows validation error for short passwords', async () => {
    renderRegister();

    fireEvent.change(screen.getByLabelText(/name/i), { target: { value: 'John' } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'j@t.com' } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'short' } });

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /register/i }));
    });

    expect(screen.getByText(/at least 8 characters/i)).toBeInTheDocument();
    expect(mockRegisterUser).not.toHaveBeenCalled();
  });
});
