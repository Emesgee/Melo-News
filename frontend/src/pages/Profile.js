import React, { useEffect, useState } from 'react';
import { ProfilData, setAuthToken } from '../services/api';

const ProfileTest = () => {
  const [profile, setProfile] = useState(null);

  useEffect(() => {
    setAuthToken();  // Set the token before making API requests

    const fetchProfile = async () => {
      try {
        const response = await ProfilData();
        setProfile(response.data);
        console.log("Profile Data:", response.data);
      } catch (error) {
        console.error("Failed to fetch profile:", error);
      }
    };

    fetchProfile();
  }, []);

  return (
    <div>
      <h1>Profile Data</h1>
      {profile ? <pre>{JSON.stringify(profile, null, 2)}</pre> : <p>Loading...</p>}
    </div>
  );
};

export default ProfileTest;
