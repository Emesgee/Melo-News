import React, { useState, useEffect } from 'react';

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
export const GeneralInfoForm = ({ title, setTitle, tags, setTags, subject, setSubject, rtl = false, labels = {} }) => (
  <div className="form-section" dir={rtl ? 'rtl' : undefined}>
    <h3>📝 {rtl ? 'معلومات عامة' : 'General Information'}</h3>
    <div className="form-group">
      <label className="form-label">{labels.title || 'Title *'}</label>
      <input
        type="text"
        className="form-input"
        placeholder={labels.titlePlaceholder || 'Enter a compelling headline for your news story'}
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        required
        dir={rtl ? 'rtl' : undefined}
      />
    </div>
    <div className="form-group">
      <label className="form-label">{labels.tags || 'Tags'}</label>
      <input
        type="text"
        className="form-input"
        placeholder={labels.tagsPlaceholder || 'Enter relevant tags (comma separated)'}
        value={tags}
        onChange={(e) => setTags(e.target.value)}
        dir={rtl ? 'rtl' : undefined}
      />
    </div>
    <div className="form-group">
      <label className="form-label">{labels.subject || 'Subject/Summary'}</label>
      <textarea
        className="form-textarea"
        placeholder={labels.subjectPlaceholder || 'Provide a brief summary or description of the news content'}
        value={subject}
        onChange={(e) => setSubject(e.target.value)}
        rows="3"
        dir={rtl ? 'rtl' : undefined}
      />
    </div>
  </div>
);

/* ── Location Form ──────────────────────────────────────────────────── */
export const LocationForm = ({ city, setCity, country, setCountry, lat, lon, onUseMyLocation, isLocating, rtl = false, labels = {} }) => (
  <div className="form-section" dir={rtl ? 'rtl' : undefined}>
    <h3>📍 {rtl ? 'معلومات الموقع' : 'Location Information'}</h3>
    <div className="form-group">
      <label className="form-label">{labels.city || 'City'}</label>
      <input
        type="text"
        className="form-input"
        placeholder={labels.cityPlaceholder || 'Enter the city where the news occurred'}
        value={city}
        onChange={(e) => setCity(e.target.value)}
        dir={rtl ? 'rtl' : undefined}
      />
    </div>
    <div className="form-group">
      <label className="form-label">{labels.country || 'Country'}</label>
      <input
        type="text"
        className="form-input"
        placeholder={labels.countryPlaceholder || 'Enter the country'}
        value={country}
        onChange={(e) => setCountry(e.target.value)}
        dir={rtl ? 'rtl' : undefined}
      />
    </div>
    <button type="button" className="location-btn" onClick={onUseMyLocation} disabled={isLocating} style={{marginTop:8}}>
      {isLocating ? (labels.locating || 'Locating...') : (labels.useLocation || '📡 Use My Location')}
    </button>
    {lat && lon && (
      <div className="location-info">
        📍 {rtl ? 'الإحداثيات' : 'Coordinates'}: {lat.toFixed(6)}, {lon.toFixed(6)}
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
              accept="image/*,video/*,audio/*,.csv,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx"
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
