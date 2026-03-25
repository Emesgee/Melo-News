import React, { useState, useEffect } from 'react';

/* ── Step Indicator ─────────────────────────────────────────────────── */
export const StepIndicator = ({ currentStep }) => {
  const steps = [
    { num: 1, label: 'Upload' },
    { num: 2, label: 'AI Analysis' },
    { num: 3, label: 'Review & Publish' },
  ];
  return (
    <div className="step-indicator">
      {steps.map((s, i) => (
        <React.Fragment key={s.num}>
          <div className={`step-item ${currentStep >= s.num ? 'active' : ''} ${currentStep > s.num ? 'completed' : ''}`}>
            <div className="step-circle">
              {currentStep > s.num ? '✓' : s.num}
            </div>
            <span className="step-label">{s.label}</span>
          </div>
          {i < steps.length - 1 && (
            <div className={`step-line ${currentStep > s.num ? 'active' : ''}`} />
          )}
        </React.Fragment>
      ))}
    </div>
  );
};

/* ── Media Preview ──────────────────────────────────────────────────── */
export const MediaPreview = ({ file, onRemove }) => {
  const [previewUrl, setPreviewUrl] = useState(null);

  useEffect(() => {
    if (!file) { setPreviewUrl(null); return; }
    if (file.type.startsWith('image/') || file.type.startsWith('video/')) {
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
      return () => URL.revokeObjectURL(url);
    }
  }, [file]);

  if (!file) return null;

  const isImage = file.type.startsWith('image/');
  const isVideo = file.type.startsWith('video/');
  const isAudio = file.type.startsWith('audio/');

  return (
    <div className="media-preview">
      {isImage && previewUrl && (
        <img src={previewUrl} alt="Preview" className="media-preview-img" />
      )}
      {isVideo && previewUrl && (
        <div className="media-preview-video-wrap">
          <video src={previewUrl} className="media-preview-video" muted />
          <div className="media-preview-play">▶</div>
        </div>
      )}
      {isAudio && (
        <div className="media-preview-icon">🎵</div>
      )}
      {!isImage && !isVideo && !isAudio && (
        <div className="media-preview-icon">📄</div>
      )}
      <div className="media-preview-info">
        <span className="media-preview-name">{file.name}</span>
        <span className="media-preview-size">{(file.size / 1024 / 1024).toFixed(2)} MB</span>
      </div>
      <button type="button" className="media-preview-remove" onClick={onRemove} aria-label="Remove file">✕</button>
    </div>
  );
};

/* ── General Info Form ──────────────────────────────────────────────── */
export const GeneralInfoForm = ({ title, setTitle, tags, setTags, subject, setSubject }) => (
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

/* ── Location Form ──────────────────────────────────────────────────── */
export const LocationForm = ({ city, setCity, country, setCountry, lat, lon, onUseMyLocation, isLocating }) => (
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

/* ── File Upload Form (with drag-and-drop + preview) ────────────────── */
export const FileUploadForm = ({ fileTypes, fileTypeId, setFileTypeId, selectedFile, handleFileChange, handleDrop, handleRemoveFile, isDragging, setIsDragging }) => (
  <div
    className={`form-section file-upload-section ${isDragging ? 'drag-over' : ''} ${selectedFile ? 'has-file' : ''}`}
    onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
    onDragLeave={(e) => { e.preventDefault(); setIsDragging(false); }}
    onDrop={handleDrop}
  >
    {!selectedFile ? (
      <>
        <div className="file-upload-icon">{isDragging ? '📥' : '📎'}</div>
        <h3>{isDragging ? 'Drop your file here' : 'File Upload'}</h3>
        <p>{isDragging ? 'Release to upload' : 'Drag & drop or click to select your news media file'}</p>

        <div className="form-group">
          <label className="form-label">File Type *</label>
          <select
            className="form-select"
            value={fileTypeId}
            onChange={(e) => setFileTypeId(e.target.value)}
            required
          >
            <option value="" disabled>Choose file type</option>
            {fileTypes.map((type) => (
              <option key={type.id} value={type.id}>{type.type_name}</option>
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
              Choose File
            </label>
          </div>
        </div>

        <div className="file-size-hint">Supported: Images, Videos, Audio, Documents · Max 60MB</div>
      </>
    ) : (
      <>
        <MediaPreview file={selectedFile} onRemove={handleRemoveFile} />
        <div className="form-group" style={{marginTop: '1rem'}}>
          <label className="form-label">File Type *</label>
          <select
            className="form-select"
            value={fileTypeId}
            onChange={(e) => setFileTypeId(e.target.value)}
            required
          >
            <option value="" disabled>Choose file type</option>
            {fileTypes.map((type) => (
              <option key={type.id} value={type.id}>{type.type_name}</option>
            ))}
          </select>
        </div>
      </>
    )}
  </div>
);
