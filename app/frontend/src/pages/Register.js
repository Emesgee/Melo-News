import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { registerUser } from '../services/api';
import './Register.css';

const Register = () => {
  const [username, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [registered, setRegistered] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (password.length < 8) {
      setMessage('Password must be at least 8 characters.');
      setMessageType('error');
      return;
    }

    setIsLoading(true);
    setMessage('');
    try {
      const response = await registerUser({
        username: username.trim(),
        email: email.trim(),
        password,
      });
      setMessage(response.data?.message || 'Registration successful!');
      setMessageType('success');
      setRegistered(true);
    } catch (error) {
      setMessage(error.response?.data?.message || 'Registration failed');
      setMessageType('error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="register-container">
      <h2>Register</h2>
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="username">Name</label>
          <input
            id="username"
            type="text"
            value={username}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </div>
        <div>
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
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
            minLength={8}
          />
          <span className="field-hint">Minimum 8 characters</span>
        </div>
        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Registering\u2026' : 'Register'}
        </button>
      </form>
      {message && <p className={`message message--${messageType}`}>{message}</p>}
      {registered && (
        <button className="register-login-btn" onClick={() => navigate('/login')}>
          Go to Login
        </button>
      )}
    </div>
  );
};

export default Register;
