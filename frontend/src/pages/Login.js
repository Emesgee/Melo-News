// src/pages/Login.js
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { loginUser, setAuthToken } from '../services/api'; // Import setAuthToken
import './Login.css';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await loginUser({ email, password });
      const token = response.data.access_token;

      // Store the token in localStorage
      localStorage.setItem('token', token);
        

      // Set token for future requests
      setAuthToken(token);

      setMessage('Login successful');
      navigate('/intro'); // Redirect to Intro page
    } catch (error) {
      setMessage(error.response?.data?.message || 'Login failed');
    }
  };

  const handleRegisterRedirect = () => {
    navigate('/register'); // Redirect to Register page
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
        <button type="submit">Login</button>
      </form>

      {message && <p>{message}</p>}
      <p style={{ color: 'grey' }}>Don't have an account?</p>
      <button onClick={handleRegisterRedirect}>Register</button>
    </div>
  );
};

export default Login;
