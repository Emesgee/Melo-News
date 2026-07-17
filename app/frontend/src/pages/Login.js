// src/pages/Login.js
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { loginUser, setAccessToken } from '../services/api';
import { useAuth } from '../utils/AuthContext';
import './Login.css';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setMessage('');
    try {
      const response = await loginUser({ email: email.trim(), password });

      // Keep header-token fallback for endpoints expecting Authorization header.
      const accessToken = response?.data?.access_token;
      if (accessToken) {
        setAccessToken(accessToken);
      }

      // Auth cookie is set automatically by the server
      login();

      setMessage('Login successful');
      setMessageType('success');
      navigate('/'); // reader home (map); moderators open the queue from the account menu
    } catch (error) {
      setMessage(error.response?.data?.error || error.response?.data?.message || 'Login failed');
      setMessageType('error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-container">
      <h2>Login</h2>
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="username"
          />
        </div>
        <div>
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </div>
        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Logging in\u2026' : 'Login'}
        </button>
      </form>

      {message && <p className={`message message--${messageType}`}>{message}</p>}
      <p className="login-hint">Forgot your password? Contact your administrator.</p>
      <p className="login-hint">Don&apos;t have an account?</p>
      <button onClick={() => navigate('/register')}>Register</button>
    </div>
  );
};

export default Login;
