import React, { useEffect, useState } from 'react';
import { getProfileData } from '../services/api';
import './Profile.css';

const PROFILE_FIELDS = [
  { key: 'username', label: 'Name' },
  { key: 'name', label: 'Name' },
  { key: 'email', label: 'Email' },
  { key: 'role', label: 'Role' },
  { key: 'created_at', label: 'Member since' },
  { key: 'createdAt', label: 'Member since' },
];

const formatValue = (key, value) => {
  if (value == null) return '—';
  if (key === 'created_at' || key === 'createdAt') {
    try { return new Date(value).toLocaleDateString(); } catch { return String(value); }
  }
  return String(value);
};

const Profile = () => {
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const response = await getProfileData();
        setProfile(response.data);
      } catch {
        setError(true);
      }
    };

    fetchProfile();
  }, []);

  if (error) {
    return (
      <div className="profile-container">
        <h1>Profile</h1>
        <p className="profile-error">Failed to load profile. Please try again later.</p>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="profile-container">
        <h1>Profile</h1>
        <p>Loading...</p>
      </div>
    );
  }

  // Render known fields first, then any extra fields from the API
  const rendered = new Set();
  const rows = PROFILE_FIELDS
    .filter((f) => profile[f.key] !== undefined && !rendered.has(f.label))
    .map((f) => {
      rendered.add(f.label);
      return { label: f.label, value: formatValue(f.key, profile[f.key]) };
    });

  // Add any remaining fields not covered by PROFILE_FIELDS
  Object.entries(profile).forEach(([key, value]) => {
    const alreadyShown = PROFILE_FIELDS.some((f) => f.key === key && rendered.has(f.label));
    if (!alreadyShown && typeof value !== 'object') {
      rows.push({ label: key, value: formatValue(key, value) });
    }
  });

  return (
    <div className="profile-container">
      <h1>Profile</h1>
      <div className="profile-card">
        {rows.map((row) => (
          <div key={row.label} className="profile-row">
            <span className="profile-label">{row.label}</span>
            <span className="profile-value">{row.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Profile;
