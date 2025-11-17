// filepath: [api.js](http://_vscodecontentref_/13)
import axios from 'axios';

// Base API URL, hardcoded for this environment
//const API_URL = process.env.REACT_APP_API_URL || "http://10.107.224.62:8000";
//const API_URL = process.env.REACT_APP_API_URL || 'http://192.168.77.62:8000';
const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

console.log('API_URL:', API_URL);

// Axios instance with base URL and default headers
export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: true
});

// Set Authorization token from localStorage if available
export const setAuthToken = () => {
  const token = localStorage.getItem('token');
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common['Authorization'];
  }
};

// Ensure Authorization token is applied
const ensureAuthToken = () => {
  const token = localStorage.getItem('token');
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  }
};

// User Registration
export const registerUser = async (userData) => {
  try {
    return await api.post('/auth/register', userData);
  } catch (error) {
    console.error("Registration Failed:", error);
    throw error;
  }
};

// User Login
export const loginUser = async (credentials) => {
  try {
    return await api.post('/auth/login', credentials);
  } catch (error) {
    console.error("Login Failed:", error);
    throw error;
  }
};

// Get Profile Data
export const ProfileData = async () => {
  ensureAuthToken();
  try {
    return await api.get('/api/profile', {
      params: {
        userData: 'name'
      }
    });
  } catch (error) {
    console.error("Failed to Fetch Profile Data:", error);
    throw error;
  }
};

// Fetch Available File Types
export const fetchFileTypes = async () => {
  ensureAuthToken();
  try {
    return await api.get('/api/file-types');
  } catch (error) {
    console.error("Failed to Fetch File Types:", error);
    throw error;
  }
};

// Test API URL for connectivity
export const testApiUrl = async () => {
  try {
    const response = await api.get('/api/test');
    console.log("API Test Successful:", response.data);
  } catch (error) {
    console.error("API Test Failed:", error);
  }
};