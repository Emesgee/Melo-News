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

  const passwordChecks = [
    { test: password.length >= 8, label: 'at least 8 characters' },
    { test: /[a-z]/.test(password), label: 'one lowercase letter' },
    { test: /[A-Z]/.test(password), label: 'one uppercase letter' },
    { test: /\d/.test(password), label: 'one number' },
    { test: /[@$!%*?&]/.test(password), label: 'one special character (@$!%*?&)' },
  ];

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!username.trim()) {
      setMessage('Name is required.');
      setMessageType('error');
      return;
    }

    const failedPasswordRule = passwordChecks.find((rule) => !rule.test);
    if (failedPasswordRule) {
      setMessage(`Password must include ${failedPasswordRule.label}.`);
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
      setMessage(error.response?.data?.error || error.response?.data?.message || 'Registration failed');
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
          <span className="field-hint">8+ chars, uppercase, lowercase, number, and @$!%*?&</span>
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
