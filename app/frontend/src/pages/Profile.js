import React, { useEffect, useState } from 'react';
import { ProfileData, setAuthToken, api } from '../services/api'; // Note: Function name corrected from ProfileData to ProfilData

const Profile = () => {
  const [profile, setProfile] = useState(null);

  useEffect(() => {
    // Log JWT token from localStorage
    const token = localStorage.getItem('token');
    console.log("JWT Token in localStorage:", token);  // Should print the token if it exists

    // Set the token in Axios headers
    setAuthToken();  // Ensure Authorization header is set

    // Log Axios Authorization header
    console.log("Axios Authorization Header:", api.defaults.headers.common['Authorization']);  // Should be 'Bearer <token>'

    const fetchProfile = async () => {
      try {
        const response = await ProfileData(); // Fetch profile data
        setProfile(response.data); // Set the profile state with fetched data
        console.log("Profile Data:", response.data); // Log the fetched profile data
      } catch (error) {
        console.error("Failed to fetch profile:", error.response ? error.response.data : error.message);
      }
    };

    fetchProfile(); // Call the function to fetch profile data
  }, []);

  return (
    <div>
      <h1>Profile Data</h1>
      {/* Display the profile data or a loading message */}
      {profile ? <pre>{JSON.stringify(profile, null, 2)}</pre> : <p>Loading...</p>}
    </div>
  );
};

export default Profile;
