import React, { useState, useEffect } from 'react';
import Sidebar from '../components/navigation_bars/Sidebar';
import './UploadForm.css';
import axios from 'axios';

const GeneralInfoForm = ({ title, setTitle, tags, setTags, subject, setSubject }) => (
  <div className="general-info-form">
    <h3>General Information</h3>
    <div>
      <label>Title:</label>
      <input type="text" placeholder='Headline' value={title} onChange={(e) => setTitle(e.target.value)} required />
    </div>
    <div>
      <label>Tags:</label>
      <input type="text" placeholder='Enter tags' value={tags} onChange={(e) => setTags(e.target.value)} />
    </div>
    <div>
      <label>Subject:</label>
      <input type="text" placeholder='Topic summary' value={subject} onChange={(e) => setSubject(e.target.value)} />
    </div>
  </div>
);

const LocationForm = ({ city, setCity, country, setCountry }) => (
  <div className="location-form">
    <h3>Location Information</h3>
    <div>
      <label>City:</label>
      <input type="text" placeholder='Type the city' value={city} onChange={(e) => setCity(e.target.value)} />
    </div>
    <div>
      <label>Country:</label>
      <input type="text" placeholder='Type the country' value={country} onChange={(e) => setCountry(e.target.value)} />
    </div>
  </div>
);

const FileUploadForm = ({ fileTypes, fileTypeId, setFileTypeId, handleFileChange }) => (
  <div className="file-upload-form">
    <h3>File Upload</h3>
    <div>
      <label>File Type:</label>
      <select value={fileTypeId} onChange={(e) => setFileTypeId(e.target.value)} required>
        <option value="" disabled>Select a file type</option>
        {fileTypes.map((type) => (
          <option key={type.id} value={type.id}>{type.type_name}</option>
        ))}
      </select>
    </div>
    <div>
      <label>File:</label>
      <input type="file" onChange={handleFileChange} required />
    </div>
  </div>
);

const FileUpload = () => {
  const [isSidebarVisible, setIsSidebarVisible] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [title, setTitle] = useState('');
  const [tags, setTags] = useState('');
  const [subject, setSubject] = useState('');
  const [city, setCity] = useState('');
  const [country, setCountry] = useState('');
  const [lat, setLat] = useState(null);
  const [lon, setLon] = useState(null);
  const [fileTypeId, setFileTypeId] = useState('');
  const [fileTypes, setFileTypes] = useState([]);
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const MAX_FILE_SIZE = 60 * 1024 * 1024;
  const ALLOWED_FILE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'video/mp4', 'video/mpeg', 'video/ogg',
    'audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/mp4', 'audio/x-m4a', 'application/pdf', 'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-powerpoint', 
    'application/vnd.openxmlformats-officedocument.presentationml.presentation'];

  const API_URL = 'http://127.0.0.1:5000';
  const GEODATA_API_URL = 'https://api.opencagedata.com/geocode/v1/json';
  const GEODATA_API_KEY = 'YOUR_GEODATA_API_KEY'; // Replace with your actual API key

  const toggleSidebar = () => setIsSidebarVisible((prev) => !prev);

  useEffect(() => {
    const fetchFileTypes = async () => {
      try {
        const response = await axios.get(`${API_URL}/api/file-types`);
        setFileTypes(response.data);
      } catch (error) {
        setMessage('Error fetching file types');
      }
    };
    fetchFileTypes();
  }, []);

  useEffect(() => {
    if (city.trim() && country.trim()) {
      const fetchGeolocation = async () => {
        try {
          const response = await axios.get(GEODATA_API_URL, {
            params: { q: `${city.trim()}, ${country.trim()}`, key: GEODATA_API_KEY },
          });
          if (response.data.results?.length > 0) {
            const { lat, lng } = response.data.results[0].geometry;
            setLat(lat);
            setLon(lng);
          } else {
            setMessage('Location not found.');
          }
        } catch (error) {
          setMessage('Error fetching location data.');
        }
      };
      fetchGeolocation();
    }
  }, [city, country]);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) {
      setMessage('No file selected. Please choose a file.');
      return;
    }
    if (!ALLOWED_FILE_TYPES.includes(file.type)) {
      setMessage('Invalid file type. Please choose a supported file.');
      setSelectedFile(null);
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      setMessage('File is too large. Maximum size allowed is 60MB.');
      setSelectedFile(null);
      return;
    }
    setSelectedFile(file);
    setMessage('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!fileTypeId || !selectedFile) {
      setMessage('Please select a file and file type.');
      return;
    }
    setIsLoading(true);

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("file_type_id", fileTypeId);
    formData.append("title", title || '');
    formData.append("tags", tags || '');
    formData.append("subject", subject || '');
    formData.append("city", city || '');
    formData.append("country", country || '');
    formData.append("lat", lat ? lat.toString() : '');
    formData.append("lon", lon ? lon.toString() : '');

    try {
      const token = localStorage.getItem('token');
      if (!token) {
        setMessage('User not authenticated. Please log in.');
        setIsLoading(false);
        return;
      }

      const response = await fetch(`${API_URL}/api/file_upload/upload`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`, // Explicitly attach token here
        },
        body: formData,
      });

      const responseData = await response.json();

      if (response.ok) {
        setMessage('File uploaded successfully!');
      } else {
        console.error('Upload error:', responseData);
        setMessage(responseData.message || 'Failed to upload file.');
      }
    } catch (error) {
      console.error("Error during upload:", error);
      setMessage('An error occurred while uploading the file.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app-container">
      <Sidebar isSidebarVisible={isSidebarVisible} toggleSidebar={toggleSidebar} />
      <div className={`upload-container ${isSidebarVisible ? 'sidebar-active' : ''}`}>
        <h2>File Upload</h2>
        <form onSubmit={handleSubmit}>
          <FileUploadForm fileTypes={fileTypes} fileTypeId={fileTypeId} setFileTypeId={setFileTypeId} handleFileChange={handleFileChange} />
          <GeneralInfoForm title={title} setTitle={setTitle} tags={tags} setTags={setTags} subject={subject} setSubject={setSubject} />
          <LocationForm city={city} setCity={setCity} country={country} setCountry={setCountry} />
          <button type="submit" disabled={isLoading}>
            {isLoading ? 'Uploading...' : 'Upload'}
          </button>
        </form>
        {message && <p>{message}</p>}
        {lat && lon && <p>Latitude: {lat}, Longitude: {lon}</p>}
      </div>
    </div>
  );
};

export default FileUpload;
