import axios from 'axios';

// Base API URL, hardcoded for this environment
const API_URL = process.env.REACT_APP_API_URL;
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
  const token = localStorage.getItem('token'); // Retrieve token from localStorage
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common['Authorization'];
  }
};

// Example function to ensure token is applied before making a request
const ensureAuthToken = () => {
  const token = localStorage.getItem('token');
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
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

// Get Profile Data
export const ProfileData = async () => {
  ensureAuthToken(); // Ensure the token is set before making this request
  return api.get('/api/profile');
  params: {
    userData: 'name'
  }
  
};

// Fetch Available File Types
export const fetchFileTypes = async () => {
  ensureAuthToken(); // Ensure token for this authenticated request
  return api.get('/api/file-types');
  
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
