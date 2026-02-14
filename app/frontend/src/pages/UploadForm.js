import React, { useState, useEffect } from 'react';
import Sidebar from '../components/navigation_bars/Sidebar';
import './UploadForm.css';
import axios from 'axios';
import { api } from '../services/api';

const GeneralInfoForm = ({ title, setTitle, tags, setTags, subject, setSubject }) => (
  <div className="form-section">
    <h3>📝 General Information</h3>
    <div className="form-group">
      <label className="form-label">Title *</label>
      <input
        type="text"
        className="form-input"
        placeholder="Enter a compelling headline for your news story"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        required
      />
    </div>
    <div className="form-group">
      <label className="form-label">Tags</label>
      <input
        type="text"
        className="form-input"
        placeholder="Enter relevant tags (comma separated)"
        value={tags}
        onChange={(e) => setTags(e.target.value)}
      />
    </div>
    <div className="form-group">
      <label className="form-label">Subject/Summary</label>
      <textarea
        className="form-textarea"
        placeholder="Provide a brief summary or description of the news content"
        value={subject}
        onChange={(e) => setSubject(e.target.value)}
        rows="3"
      />
    </div>
  </div>
);

const LocationForm = ({ city, setCity, country, setCountry, lat, lon, onUseMyLocation, isLocating }) => (
  <div className="form-section">
    <h3>📍 Location Information</h3>
    <div className="form-group">
      <label className="form-label">City</label>
      <input
        type="text"
        className="form-input"
        placeholder="Enter the city where the news occurred"
        value={city}
        onChange={(e) => setCity(e.target.value)}
      />
    </div>
    <div className="form-group">
      <label className="form-label">Country</label>
      <input
        type="text"
        className="form-input"
        placeholder="Enter the country"
        value={country}
        onChange={(e) => setCountry(e.target.value)}
      />
    </div>
    <button type="button" className="location-btn" onClick={onUseMyLocation} disabled={isLocating} style={{marginTop:8}}>
      {isLocating ? 'Locating...' : '📡 Use My Location'}
    </button>
    {lat && lon && (
      <div className="location-info">
        📍 Coordinates: {lat.toFixed(6)}, {lon.toFixed(6)}
      </div>
    )}
  </div>
);

const FileUploadForm = ({ fileTypes, fileTypeId, setFileTypeId, selectedFile, handleFileChange }) => (
  <div className="form-section file-upload-section">
    <div className="file-upload-icon">📎</div>
    <h3>File Upload</h3>
    <p>Select and upload your news media file</p>

    <div className="form-group">
      <label className="form-label">File Type *</label>
      <select
        className="form-select"
        value={fileTypeId}
        onChange={(e) => setFileTypeId(e.target.value)}
        required
      >
        <option value="" disabled>
          Choose file type
        </option>
        {fileTypes.map((type) => (
          <option key={type.id} value={type.id}>
            {type.type_name}
          </option>
        ))}
      </select>
    </div>

    <div className="form-group">
      <label className="form-label">File *</label>
      <div className="file-input-wrapper">
        <input
          id="fileInput"
          type="file"
          className="file-input"
          onChange={handleFileChange}
          accept="image/*,video/*,audio/*,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx"
          required
        />
        <label htmlFor="fileInput" className="file-input-label">
          <span>📁</span>
          {selectedFile ? selectedFile.name : 'Choose File'}
        </label>
      </div>
      {selectedFile && (
        <div className="file-info">
          <strong>Selected:</strong> {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
        </div>
      )}
    </div>
  </div>
);

const UploadForm = () => {
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
  const [messageType, setMessageType] = useState(''); // 'success', 'error', 'info'
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [isLocating, setIsLocating] = useState(false);
  // Handler for "Use My Location" button
  const handleUseMyLocation = () => {
    if (!navigator.geolocation) {
      setMessage('Geolocation is not supported by your browser.');
      setMessageType('error');
      return;
    }
    setIsLocating(true);
    setMessage('Getting your current location...');
    setMessageType('info');
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords;
        setLat(latitude);
        setLon(longitude);
        setMessage('Location detected!');
        setMessageType('success');
        // Optionally, reverse geocode to get city/country
        try {
          const response = await axios.get(GEODATA_API_URL, {
            params: { q: `${latitude},${longitude}`, key: GEODATA_API_KEY },
          });
          if (response.data.results?.length > 0) {
            const comp = response.data.results[0].components;
            if (comp.city || comp.town || comp.village) setCity(comp.city || comp.town || comp.village);
            if (comp.country) setCountry(comp.country);
          }
        } catch (e) {
          // Ignore reverse geocode errors
        }
        setIsLocating(false);
      },
      (error) => {
        setMessage('Unable to retrieve your location.');
        setMessageType('error');
        setIsLocating(false);
      }
    );
  };

  const MAX_FILE_SIZE = 60 * 1024 * 1024; // 60MB
  const ALLOWED_FILE_TYPES = [
    'image/jpeg','image/jpg', 'image/png', 'image/gif', 'image/webp',
    'video/mp4', 'video/avi', 'video/mov', 'video/mpeg', 'video/ogg', 'video/webm',
    'audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/mp4', 'audio/x-m4a',
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
  ];

  const GEODATA_API_URL = 'https://api.opencagedata.com/geocode/v1/json';
  const GEODATA_API_KEY = '0bc1962b58b7482ebe0507debae9a885';

  const toggleSidebar = () => setIsSidebarVisible((prev) => !prev);

  useEffect(() => {
    const fetchFileTypes = async () => {
      try {
        const response = await api.get('/file-types');
        setFileTypes(response.data);
      } catch (error) {
        setMessage('Failed to load file types. Please refresh the page.');
        setMessageType('error');
      }
    };
    fetchFileTypes();
  }, []);

  useEffect(() => {
    if (city.trim() && country.trim()) {
      const fetchGeolocation = async () => {
        try {
          setMessage('Fetching location coordinates...');
          setMessageType('info');

          const response = await axios.get(GEODATA_API_URL, {
            params: { q: `${city.trim()}, ${country.trim()}`, key: GEODATA_API_KEY },
          });

          if (response.data.results?.length > 0) {
            const { lat: latitude, lng: longitude } = response.data.results[0].geometry;
            setLat(latitude);
            setLon(longitude);
            setMessage('Location found successfully!');
            setMessageType('success');
          } else {
            setMessage('Location not found. Please check the city and country names.');
            setMessageType('error');
          }
        } catch (error) {
          setMessage('Error fetching location data. Please try again.');
          setMessageType('error');
        }
      };
      fetchGeolocation();
    }
  }, [city, country]);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) {
      setMessage('No file selected. Please choose a file.');
      setMessageType('error');
      return;
    }

    if (!ALLOWED_FILE_TYPES.includes(file.type)) {
      setMessage('Invalid file type. Please choose a supported file format.');
      setMessageType('error');
      setSelectedFile(null);
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      setMessage('File is too large. Maximum size allowed is 60MB.');
      setMessageType('error');
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
    setMessage(`File "${file.name}" selected successfully!`);
    setMessageType('success');
    
    // Auto-analyze if image or video
    if (file.type.startsWith('image/') || file.type.startsWith('video/')) {
      analyzeMedia(file);
    }
  };

  const analyzeMedia = async (file) => {
    setIsAnalyzing(true);
    setMessage('🔍 Analyzing media with AI... This may take a moment.');
    setMessageType('info');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await api.post('/ai/analyze', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      const data = response.data;
      setAnalysisResult(data);
      
      // Auto-fill form fields
      if (data.title) setTitle(data.title);
      if (data.tags) setTags(data.tags);
      if (data.subject) setSubject(data.subject);
      if (data.city) setCity(data.city);
      if (data.country) setCountry(data.country);
      
      setMessage(`✅ AI Analysis complete! Confidence: ${(data.confidence * 100).toFixed(0)}% - Review and edit the fields before submitting.`);
      setMessageType('success');
    } catch (error) {
      setMessage(`⚠️ AI analysis unavailable: ${error.response?.data?.error || error.message || 'Service error'}. Please fill form manually.`);
      setMessageType('error');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!fileTypeId || !selectedFile) {
      setMessage('Please select a file and file type.');
      setMessageType('error');
      return;
    }

    if (!title.trim()) {
      setMessage('Please provide a title for your news story.');
      setMessageType('error');
      return;
    }

    setIsLoading(true);
    setMessage('Uploading your file... Please wait.');
    setMessageType('info');

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('file_type_id', fileTypeId);
    formData.append('title', title.trim());
    formData.append('tags', tags.trim());
    formData.append('subject', subject.trim());
    formData.append('city', city.trim());
    formData.append('country', country.trim());
    formData.append('lat', lat !== null && !isNaN(lat) ? lat : null);
    formData.append('lon', lon !== null && !isNaN(lon) ? lon : null);

    try {
      const token = localStorage.getItem('token');
      if (!token) {
        setMessage('You are not authenticated. Please log in again.');
        setMessageType('error');
        setIsLoading(false);
        return;
      }

      const response = await api.post('/file_upload/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          Authorization: `Bearer ${token}`,
        },
      });

      setMessage('🎉 File uploaded successfully! Your news story is now live on the map.');
      setMessageType('success');

      // Reset form
      setSelectedFile(null);
      setTitle('');
      setTags('');
      setSubject('');
      setCity('');
      setCountry('');
      setLat(null);
      setLon(null);
      setFileTypeId('');

        // Reset file input
        const fileInput = document.getElementById('fileInput');
        if (fileInput) fileInput.value = '';

        // Optional: Auto-trigger a refresh to get the latest data
        // You can dispatch an event or call a callback to refresh search results
        // For now, just notify the user to search for it
        setTimeout(() => {
          setMessage('✅ Uploaded! Search by title or location to find it on the map.');
          setMessageType('success');
        }, 2000);
    } catch (error) {
      console.error('Error during upload:', error);
      const errorMsg = error.response?.data?.message || error.message || 'Network error occurred. Please check your connection and try again.';
      setMessage(errorMsg);
      setMessageType('error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="upload-page">
      {/* Burger Menu */}
      <button className={`burger-menu ${isSidebarVisible ? 'active' : ''}`} onClick={toggleSidebar} aria-label="Toggle sidebar">
        <div className="burger-line"></div>
        <div className="burger-line"></div>
        <div className="burger-line"></div>
      </button>

      {/* Navigation */}
      <Sidebar isSidebarVisible={isSidebarVisible} toggleSidebar={toggleSidebar} />

      {/* Quick Upload Header */}
      <section className="upload-header">
        <div className="upload-header-content">
          <h1>🚀 Share News</h1>
          <p>Fast and simple. Get your news on the map in seconds.</p>
        </div>
      </section>

      {/* Main Content */}
      <div className="upload-content">
        {/* AI Analysis Banner */}
        {isAnalyzing && (
          <div className="ai-analysis-banner">
            <div className="spinner"></div>
            <div className="text">
              🤖 AI is analyzing your media... Extracting title, tags, and location.
            </div>
          </div>
        )}
        
        {analysisResult && !isAnalyzing && (
          <div className="ai-analysis-banner" style={{background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)'}}>
            <div className="icon">✨</div>
            <div className="text">
              AI Analysis Complete! Confidence: {(analysisResult.confidence * 100).toFixed(0)}% - Review and edit the fields below.
            </div>
          </div>
        )}
        
        <div className="upload-container">
          <form className="upload-form-content" onSubmit={handleSubmit}>
            <div className="form-columns">
              {/* Left Column: File Upload (Priority) */}
              <div className="form-column form-column-main">
                <FileUploadForm
                  fileTypes={fileTypes}
                  fileTypeId={fileTypeId}
                  setFileTypeId={setFileTypeId}
                  selectedFile={selectedFile}
                  handleFileChange={handleFileChange}
                />

                <GeneralInfoForm
                  title={title}
                  setTitle={setTitle}
                  tags={tags}
                  setTags={setTags}
                  subject={subject}
                  setSubject={setSubject}
                />
              </div>

              {/* Right Column: Location Info */}
              <div className="form-column form-column-side">
                <LocationForm
                  city={city}
                  setCity={setCity}
                  country={country}
                  setCountry={setCountry}
                  lat={lat}
                  lon={lon}
                  onUseMyLocation={handleUseMyLocation}
                  isLocating={isLocating}
                />

                {/* Messages */}
                {message && (
                  <div className={`message ${messageType}`}>
                    {message}
                  </div>
                )}

                {/* Form Actions */}
                <div className="form-actions-side">
                  <button type="submit" className={`submit-btn ${isLoading ? 'loading' : ''}`} disabled={isLoading}>
                    {isLoading ? (
                      <>
                        <div className="spinner"></div>
                        Uploading...
                      </>
                    ) : (
                      <>
                        <span>�</span>
                        Publish
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default UploadForm;