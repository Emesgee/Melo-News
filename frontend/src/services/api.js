//api.js

import axios from 'axios';

// Set API URL based on environment
const API_URL = 'http://172.25.84.144:5000';  // Temporary hardcoded URL
console.log("API URL is set to:", API_URL);

// Setting up an Axios instance with the base URL
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type':'application/json'
  },
  withCredentials: true
});

export const setAuthToken = () => {
  const token = localStorage.getItem('token');  // Retrieve the token from storage
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common['Authorization'];
  }
};

// User Registration
export const registerUser = async (userData) => {
  return api.post('/auth/register', userData);
};

// User Login
export const loginUser = async (credentials) => {
  return api.post('/auth/login', credentials);
};

//Get Profile Data
export const ProfilData = async (userData) => {
  return api.get('/api/profile')
};
 

// Fetch Available File Types
export const fetchFileTypes = async () => {
  return api.get('/api/file-types');
};

export const testApiUrl = async () => {
  try {
    const response = await api.get('/api/test');
    console.log("API Test Successful:", response.data);
  } catch (error) {
    console.error("API Test Failed:", error);
  }
};
