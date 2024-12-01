// src/components/PrivateRoute.js
import React from 'react';
import { Navigate } from 'react-router-dom';

const PrivateRoute = ({ component }) => {
  const isAuthenticated = !!localStorage.getItem('token');
  return isAuthenticated ? component : <Navigate to="/login" />;
};

export default PrivateRoute;
