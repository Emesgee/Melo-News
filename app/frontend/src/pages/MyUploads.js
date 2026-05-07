import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import Sidebar from '../components/navigationBars/Sidebar';
import { StepIndicator, GeneralInfoForm, LocationForm, FileUploadForm } from '../components/upload/UploadSubComponents';
import { getMyUploads, editUpload, deleteUpload, fetchFileTypes, api } from '../services/api';
import { SEVERITY_CONFIG } from '../constants/severity';
import { useToast } from '../utils/ToastContext';
import { chunkedUpload } from '../utils/chunkedUpload';
import { enqueue } from '../utils/offlineQueue';
import { MAX_FILE_SIZE, ALLOWED_FILE_TYPES } from '../components/upload/uploadConstants';
import { getNetworkProfile, getAdaptiveMaxFileSizeBytes, NETWORK_TIERS } from '../utils/connectivityPolicy';
import { useSearch } from '../utils/SearchContext';
import './MyUploads.css';

const CHUNK_THRESHOLD = 5 * 1024 * 1024;

const STATUS_LABEL = {
  PENDING: { label: 'Pending', color: '#f59e0b' },
  PROCESSING: { label: 'Analyzing…', color: '#3b82f6' },
  COMPLETED: { label: 'Analyzed', color: '#10b981' },
  FAILED: { label: 'Failed', color: '#ef4444' },
};

const SEND_STATES = {
  IDLE: 'idle',
  QUEUED: 'queued',
  UPLOADING: 'uploading',
  RETRYING: 'retrying',
  SENT: 'sent',
  FAILED: 'failed',
};

const SEND_STATE_META = {
  [SEND_STATES.IDLE]: { label: 'Ready', tone: 'neutral' },
  [SEND_STATES.QUEUED]: { label: 'Queued', tone: 'info' },
  [SEND_STATES.UPLOADING]: { label: 'Sending…', tone: 'info' },
  [SEND_STATES.RETRYING]: { label: 'Retrying…', tone: 'warn' },
  [SEND_STATES.SENT]: { label: 'Sent', tone: 'success' },
  [SEND_STATES.FAILED]: { label: 'Failed', tone: 'danger' },
};

const resolveCardSendState = (upload) => {
  const raw = String(upload?.send_state || upload?.upload_state || '').toLowerCase();
  if (raw === 'queued') return SEND_STATE_META[SEND_STATES.QUEUED];
  if (raw === 'uploading' || raw === 'sending' || raw === 'processing') return SEND_STATE_META[SEND_STATES.UPLOADING];
  if (raw === 'retrying') return SEND_STATE_META[SEND_STATES.RETRYING];
  if (raw === 'failed' || raw === 'error') return SEND_STATE_META[SEND_STATES.FAILED];
  if (raw === 'sent' || raw === 'uploaded' || raw === 'completed') return SEND_STATE_META[SEND_STATES.SENT];

  const analysisState = String(upload?.analysis_status || '').toUpperCase();
  if (analysisState === 'FAILED') return SEND_STATE_META[SEND_STATES.FAILED];
  if (analysisState === 'PENDING' || analysisState === 'PROCESSING') return SEND_STATE_META[SEND_STATES.UPLOADING];
  if (analysisState === 'COMPLETED') return SEND_STATE_META[SEND_STATES.SENT];
  return SEND_STATE_META[SEND_STATES.IDLE];
};

const CreateStoryModal = ({ initialQuickFile, initialPreferences, onCreated, onClose }) => {
  const { addToast } = useToast();
  const quickFileAppliedRef = useRef(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileTypeId, setFileTypeId] = useState('');
  const [fileTypes, setFileTypes] = useState([]);
  const [title, setTitle] = useState('');
  const [tags, setTags] = useState('');
  const [subject, setSubject] = useState('');
  const [city, setCity] = useState('');
  const [country, setCountry] = useState('');
  const [lat, setLat] = useState(null);
  const [lon, setLon] = useState(null);
  const [isLocating, setIsLocating] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('info');
  const [sendState, setSendState] = useState(SEND_STATES.IDLE);
  const [lowBandwidth, setLowBandwidth] = useState(false);
  const [bandwidthReady, setBandwidthReady] = useState(false);
  const [bandwidthProfile, setBandwidthProfile] = useState(() => getNetworkProfile());
  const [autoStripGps, setAutoStripGps] = useState(Boolean(initialPreferences?.autoStripGps));
  const [strippedFile, setStrippedFile] = useState(null);

  const currentStep = isAnalyzing ? 2 : selectedFile ? 3 : 1;

  useEffect(() => {
    const updateBandwidthMode = () => {
      const profile = getNetworkProfile();
      setBandwidthProfile(profile);
      setLowBandwidth(profile.isLowBandwidth);
      setBandwidthReady(true);
    };

    updateBandwidthMode();

    const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    const handleOnlineStatusChange = () => updateBandwidthMode();

    window.addEventListener('online', handleOnlineStatusChange);
    window.addEventListener('offline', handleOnlineStatusChange);

    if (connection?.addEventListener) {
      connection.addEventListener('change', updateBandwidthMode);
      return () => {
        connection.removeEventListener('change', updateBandwidthMode);
        window.removeEventListener('online', handleOnlineStatusChange);
        window.removeEventListener('offline', handleOnlineStatusChange);
      };
    }

    return () => {
      window.removeEventListener('online', handleOnlineStatusChange);
      window.removeEventListener('offline', handleOnlineStatusChange);
    };
  }, []);

  useEffect(() => {
    const loadFileTypes = async () => {
      try {
        const response = await fetchFileTypes();
        setFileTypes(Array.isArray(response.data) ? response.data : []);
      } catch (_) {
        setMessage('Failed to load file types. Refresh and try again.');
        setMessageType('error');
      }
    };
    loadFileTypes();
  }, []);

  const getFileExtension = useCallback((filename) => {
    const name = String(filename || '');
    const parts = name.split('.');
    return parts.length > 1 ? parts.pop().toLowerCase() : '';
  }, []);

  const findMatchingFileTypeId = useCallback((file) => {
    const ext = getFileExtension(file?.name);
    if (!ext || !Array.isArray(fileTypes)) return '';

    const match = fileTypes.find((type) =>
      String(type.allowed_extensions || '')
        .split(',')
        .map((value) => value.trim().toLowerCase())
        .includes(ext)
    );

    return match ? String(match.id) : '';
  }, [fileTypes, getFileExtension]);

  const selectedFileTypeAllowsFile = useCallback(() => {
    if (!selectedFile || !fileTypeId) return false;
    const ext = getFileExtension(selectedFile.name);
    const type = fileTypes.find((item) => String(item.id) === String(fileTypeId));
    if (!type) return false;

    return String(type.allowed_extensions || '')
      .split(',')
      .map((value) => value.trim().toLowerCase())
      .includes(ext);
  }, [selectedFile, fileTypeId, fileTypes, getFileExtension]);

  const stripExifFromImage = useCallback((file) => {
    return new Promise((resolve) => {
      const img = new Image();
      const url = URL.createObjectURL(file);
      img.onload = () => {
        const canvas = document.createElement('canvas');
        canvas.width = img.naturalWidth;
        canvas.height = img.naturalHeight;
        canvas.getContext('2d').drawImage(img, 0, 0);
        URL.revokeObjectURL(url);
        canvas.toBlob(
          (blob) => {
            const clean = new File([blob], file.name, { type: file.type, lastModified: Date.now() });
            resolve(clean);
          },
          file.type,
          0.92
        );
      };
      img.onerror = () => {
        URL.revokeObjectURL(url);
        resolve(file);
      };
      img.src = url;
    });
  }, []);

  const analyzeMedia = useCallback(async (file) => {
    if (lowBandwidth) {
      setMessage(`AI skipped in ${bandwidthProfile.tier.toUpperCase()} mode for reliability.`);
      setMessageType('info');
      return;
    }

    setIsAnalyzing(true);
    setMessage('Analyzing media with AI...');
    setMessageType('info');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await api.post('/ai/analyze', formData);
      const data = response.data || {};

      if (data.title) setTitle(data.title);
      if (data.tags) setTags(data.tags);
      if (data.subject) setSubject(data.subject);
      if (data.city) setCity(data.city);
      if (data.country) setCountry(data.country);
      if (data.exif?.has_gps && data.exif.lat && data.exif.lon) {
        setLat(data.exif.lat);
        setLon(data.exif.lon);
      }

      if (data.exif?.has_gps && autoStripGps && file.type.startsWith('image/')) {
        const cleanFile = await stripExifFromImage(file);
        setStrippedFile(cleanFile);
        setMessage('AI complete. GPS metadata was removed from image automatically.');
      } else {
        setMessage('AI analysis complete. Review fields before publishing.');
      }
      setMessageType('success');
    } catch (_) {
      setMessage('AI analysis unavailable. Continue by filling fields manually.');
      setMessageType('info');
    } finally {
      setIsAnalyzing(false);
    }
  }, [autoStripGps, bandwidthProfile.tier, lowBandwidth, stripExifFromImage]);

  const processFile = useCallback(async (file) => {
    if (!file) return;

    if (!ALLOWED_FILE_TYPES.includes(file.type)) {
      setMessage('Invalid file type. Please choose a supported format.');
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

    const adaptiveLimitBytes = getAdaptiveMaxFileSizeBytes(file, bandwidthProfile);
    if (file.size > adaptiveLimitBytes) {
      const limitMb = (adaptiveLimitBytes / 1024 / 1024).toFixed(0);
      const tierLabel = bandwidthProfile.tier === NETWORK_TIERS.CRITICAL ? 'critical' : 'constrained';
      setMessage(`Current ${tierLabel} network mode allows this file type up to ${limitMb}MB. Please choose a smaller file.`);
      setMessageType('error');
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
    setStrippedFile(null);
    const inferredTypeId = findMatchingFileTypeId(file);
    if (inferredTypeId) setFileTypeId(inferredTypeId);

    setMessage(`File "${file.name}" selected.`);
    setMessageType('success');

    if (file.type.startsWith('image/') || file.type.startsWith('video/') || file.type.startsWith('audio/')) {
      await analyzeMedia(file);
    }
  }, [analyzeMedia, bandwidthProfile, findMatchingFileTypeId]);

  useEffect(() => {
    if (quickFileAppliedRef.current) return;
    if (!bandwidthReady) return;
    if (!initialQuickFile) return;
    quickFileAppliedRef.current = true;
    processFile(initialQuickFile);
  }, [bandwidthReady, initialQuickFile, processFile]);

  const handleFileChange = (e) => {
    processFile(e.target.files[0]);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    processFile(e.dataTransfer.files[0]);
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    setStrippedFile(null);
    setUploadProgress(0);
    setSendState(SEND_STATES.IDLE);
    setMessage('');
    const input = document.getElementById('fileInput');
    if (input) input.value = '';
  };

  const handleUseMyLocation = () => {
    if (!navigator.geolocation) {
      setMessage('Geolocation is not supported by your browser.');
      setMessageType('error');
      return;
    }
    setIsLocating(true);
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords;
        setLat(latitude);
        setLon(longitude);
        try {
          const response = await api.get('/ai/geocode', {
            params: { q: `${latitude},${longitude}` },
          });
          if (response.data.city) setCity(response.data.city);
          if (response.data.country) setCountry(response.data.country);
          setMessage('Location detected.');
          setMessageType('success');
        } catch (_) {
          setMessage('Coordinates captured, but city/country autofill is unavailable right now.');
          setMessageType('info');
        } finally {
          setIsLocating(false);
        }
      },
      () => {
        setMessage('Unable to retrieve your location.');
        setMessageType('error');
        setIsLocating(false);
      }
    );
  };

  const submitUpload = async ({ isRetry = false } = {}) => {
    if (!selectedFile || !fileTypeId) {
      setMessage('Please select a file and file type.');
      setMessageType('error');
      setSendState(SEND_STATES.FAILED);
      return;
    }

    if (!title.trim()) {
      setMessage('Please provide a title for your story.');
      setMessageType('error');
      setSendState(SEND_STATES.FAILED);
      return;
    }

    if (!selectedFileTypeAllowsFile()) {
      const ext = getFileExtension(selectedFile?.name);
      setMessage(`Selected file type does not allow .${ext} files.`);
      setMessageType('error');
      setSendState(SEND_STATES.FAILED);
      return;
    }

    setIsSubmitting(true);
    setUploadProgress(0);
    setSendState(isRetry ? SEND_STATES.RETRYING : SEND_STATES.UPLOADING);
    setMessage(isRetry ? 'Retrying upload...' : 'Publishing your story...');
    setMessageType('info');

    const fileToUpload = strippedFile || selectedFile;
    const metadata = {
      file_type_id: fileTypeId,
      title: title.trim(),
      tags: tags.trim(),
      subject: subject.trim(),
      city: city.trim(),
      country: country.trim(),
      lat: lat !== null && !isNaN(lat) ? lat : null,
      lon: lon !== null && !isNaN(lon) ? lon : null,
    };

    try {
      if (!navigator.onLine) {
        setSendState(SEND_STATES.QUEUED);
        await enqueue(fileToUpload, metadata);
        addToast('You are offline. Story queued and will upload on reconnect.', 'info');
        await onCreated();
        onClose();
        return;
      }

      if (fileToUpload.size > CHUNK_THRESHOLD) {
        await chunkedUpload(api, fileToUpload, metadata, (pct) => setUploadProgress(pct));
      } else {
        const formData = new FormData();
        formData.append('file', fileToUpload);
        Object.entries(metadata).forEach(([key, value]) => {
          if (value !== null && value !== undefined) formData.append(key, value);
        });

        await api.post('/file_upload/upload', formData, {
          onUploadProgress: (progressEvent) => {
            const pct = progressEvent.total
              ? Math.round((progressEvent.loaded * 100) / progressEvent.total)
              : 0;
            setUploadProgress(pct);
          },
        });
      }

      setSendState(SEND_STATES.SENT);
      setMessage('Story sent successfully.');
      setMessageType('success');
      addToast('Story published successfully.', 'success');
      await onCreated();
      onClose();
    } catch (err) {
      const msg = err.response?.data?.message || 'Upload failed. Please try again.';
      setMessage(msg);
      setMessageType('error');
      setSendState(SEND_STATES.FAILED);
    } finally {
      setIsSubmitting(false);
      setUploadProgress(0);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    await submitUpload({ isRetry: false });
  };

  const handleRetryUpload = async () => {
    await submitUpload({ isRetry: true });
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box modal-box--lg" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Create Story</h2>
          <span
            className={`send-state-chip send-state-chip--${SEND_STATE_META[sendState].tone}`}
            aria-live="polite"
          >
            {SEND_STATE_META[sendState].label}
          </span>
          <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>
        </div>

        <StepIndicator currentStep={currentStep} />

        <form onSubmit={handleSubmit} className="create-story-form">
          <div className="create-toggles">
            <div className={`bandwidth-indicator ${bandwidthProfile.tier === NETWORK_TIERS.CRITICAL ? 'critical' : lowBandwidth ? 'low' : 'normal'}`}>
              <div className="bandwidth-indicator-head">
                <span className="bandwidth-dot" />
                <strong>Mode: {bandwidthProfile.tier.toUpperCase()} (auto)</strong>
              </div>
              <small>
                Critical &lt; {bandwidthProfile.thresholds.criticalBandwidthThresholdMbps} Mbps · Constrained &lt; {bandwidthProfile.thresholds.lowBandwidthThresholdMbps} Mbps · Type: {bandwidthProfile.effectiveType} · Reason: {bandwidthProfile.reason}
                {bandwidthProfile.downlink !== null ? ` · Downlink: ${bandwidthProfile.downlink.toFixed(1)} Mbps` : ''}
              </small>
            </div>
            <label>
              <input
                type="checkbox"
                checked={autoStripGps}
                onChange={(e) => setAutoStripGps(e.target.checked)}
              />
              Auto-remove GPS metadata from images
            </label>
          </div>

          <FileUploadForm
            fileTypes={fileTypes}
            fileTypeId={fileTypeId}
            setFileTypeId={setFileTypeId}
            selectedFile={selectedFile}
            handleFileChange={handleFileChange}
            handleDrop={handleDrop}
            handleRemoveFile={handleRemoveFile}
            isDragging={isDragging}
            setIsDragging={setIsDragging}
          />

          {selectedFile && (
            <>
              <GeneralInfoForm
                title={title}
                setTitle={setTitle}
                tags={tags}
                setTags={setTags}
                subject={subject}
                setSubject={setSubject}
              />
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
            </>
          )}

          {message && (
            <div className={`message ${messageType}`}>
              {message}
              {sendState === SEND_STATES.FAILED && !isSubmitting && (
                <button type="button" className="message-retry-btn" onClick={handleRetryUpload}>
                  Retry now
                </button>
              )}
            </div>
          )}

          {isSubmitting && (
            <div className="create-progress-wrap">
              <div className="create-progress-label">Upload progress: {uploadProgress}%</div>
              <div className="create-progress-track">
                <div className="create-progress-fill" style={{ width: `${uploadProgress}%` }} />
              </div>
            </div>
          )}

          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={isSubmitting}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={isSubmitting}>
              {isSubmitting ? 'Publishing…' : 'Publish Story'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

/* ── Edit Modal ─────────────────────────────────────────────────────── */
const EditModal = ({ upload, onSave, onClose }) => {
  const [title, setTitle] = useState(upload.title || '');
  const [tags, setTags] = useState(upload.tags || '');
  const [subject, setSubject] = useState(upload.subject || '');
  const [city, setCity] = useState(upload.city || '');
  const [country, setCountry] = useState(upload.country || '');
  const [lat, setLat] = useState(upload.lat ?? null);
  const [lon, setLon] = useState(upload.lon ?? null);
  const [isLocating, setIsLocating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleUseMyLocation = () => {
    if (!navigator.geolocation) return;
    setIsLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => { setLat(pos.coords.latitude); setLon(pos.coords.longitude); setIsLocating(false); },
      () => { setIsLocating(false); }
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title.trim()) { setError('Title is required.'); return; }
    setSaving(true);
    setError('');
    try {
      await onSave(upload.id, { title, tags, subject, city, country, lat, lon });
      onClose();
    } catch (err) {
      setError(err.response?.data?.message || 'Save failed. Try again.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Edit Story</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <form onSubmit={handleSubmit}>
          <GeneralInfoForm
            title={title} setTitle={setTitle}
            tags={tags} setTags={setTags}
            subject={subject} setSubject={setSubject}
          />
          <LocationForm
            city={city} setCity={setCity}
            country={country} setCountry={setCountry}
            lat={lat} lon={lon}
            onUseMyLocation={handleUseMyLocation}
            isLocating={isLocating}
          />
          <div className="form-section">
            <div style={{display:'flex', gap:8}}>
              <div className="form-group" style={{flex:1}}>
                <label className="form-label">Latitude</label>
                <input type="number" step="any" className="form-input"
                  placeholder="e.g. 31.5" value={lat ?? ''}
                  onChange={(e) => setLat(e.target.value ? parseFloat(e.target.value) : null)} />
              </div>
              <div className="form-group" style={{flex:1}}>
                <label className="form-label">Longitude</label>
                <input type="number" step="any" className="form-input"
                  placeholder="e.g. 34.5" value={lon ?? ''}
                  onChange={(e) => setLon(e.target.value ? parseFloat(e.target.value) : null)} />
              </div>
            </div>
          </div>
          {error && <div className="modal-error">{error}</div>}
          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? 'Saving…' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

/* ── Delete Confirm ─────────────────────────────────────────────────── */
const DeleteConfirm = ({ upload, onConfirm, onClose }) => (
  <div className="modal-overlay" onClick={onClose}>
    <div className="modal-box modal-box--sm" onClick={(e) => e.stopPropagation()}>
      <h2>Delete Story?</h2>
      <p>"{upload.title || upload.filename}" will be permanently removed from the feed.</p>
      <div className="modal-actions">
        <button className="btn-secondary" onClick={onClose}>Cancel</button>
        <button className="btn-danger" onClick={() => onConfirm(upload.id)}>Delete</button>
      </div>
    </div>
  </div>
);

/* ── Upload Card ────────────────────────────────────────────────────── */
const UploadCard = ({ upload, onEdit, onDelete }) => {
  const sev = SEVERITY_CONFIG[upload.severity] || SEVERITY_CONFIG.LOW;
  const status = STATUS_LABEL[upload.analysis_status] || STATUS_LABEL.PENDING;
  const sendMeta = resolveCardSendState(upload);
  const date = upload.upload_date
    ? new Date(upload.upload_date).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
    : '—';
  const confidence = upload.confidence_score != null
    ? `${Math.round(upload.confidence_score * 100)}%`
    : null;

  return (
    <div className="upload-card" style={{ borderLeftColor: sev.color }}>
      <div className="upload-card-body">
        <div className="upload-card-meta">
          <span className="sev-badge" style={{ background: sev.color }}>{sev.emoji} {upload.severity}</span>
          <span className={`card-send-badge card-send-badge--${sendMeta.tone}`}>{sendMeta.label}</span>
          <span className="status-badge" style={{ color: status.color }}>{status.label}</span>
          {confidence && <span className="conf-badge">🎯 {confidence}</span>}
        </div>
        <h3 className="upload-card-title">{upload.title || <em>Untitled</em>}</h3>
        {upload.subject && <p className="upload-card-subject">{upload.subject}</p>}
        <div className="upload-card-footer">
          {(upload.city || upload.country) && (
            <span className="upload-card-loc">📍 {[upload.city, upload.country].filter(Boolean).join(', ')}</span>
          )}
          <span className="upload-card-date">{date}</span>
        </div>
      </div>
      <div className="upload-card-actions">
        <button className="card-btn card-btn--edit" onClick={() => onEdit(upload)} aria-label="Edit">✏️ Edit</button>
        <button className="card-btn card-btn--delete" onClick={() => onDelete(upload)} aria-label="Delete">🗑️ Delete</button>
      </div>
    </div>
  );
};

/* ── Main Page ──────────────────────────────────────────────────────── */
const MyUploads = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { addToast } = useToast();
  const [uploads, setUploads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editTarget, setEditTarget] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [createSeed, setCreateSeed] = useState(null);
  const [isSidebarVisible, setIsSidebarVisible] = useState(false);

  const fetchUploads = useCallback(async () => {
    try {
      const res = await getMyUploads();
      setUploads(res.data);
    } catch (err) {
      addToast('Failed to load your stories.', 'error');
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  useEffect(() => { fetchUploads(); }, [fetchUploads]);

  useEffect(() => {
    if (!location.state?.openCreate) return;

    setCreateSeed({
      quickFile: location.state?.quickFile || null,
      uploadPreferences: location.state?.uploadPreferences || null,
    });
    setCreateOpen(true);
    navigate(location.pathname, { replace: true, state: null });
  }, [location.pathname, location.state, navigate]);

  const { clearResults } = useSearch();

  const handleSave = async (id, data) => {
    const res = await editUpload(id, data);
    setUploads((prev) => prev.map((u) => (u.id === id ? res.data : u)));
    clearResults(); // invalidate map cache so it reloads updated positions
    addToast('Story updated.', 'success');
  };

  const handleDelete = async (id) => {
    try {
      await deleteUpload(id);
      setUploads((prev) => prev.filter((u) => u.id !== id));
      addToast('Story deleted.', 'success');
    } catch {
      addToast('Delete failed. Try again.', 'error');
    } finally {
      setDeleteTarget(null);
    }
  };

  return (
    <div className="my-uploads-page">
      <button
        className={`burger-menu ${isSidebarVisible ? 'active' : ''}`}
        onClick={() => setIsSidebarVisible((p) => !p)}
        aria-label="Toggle sidebar"
      >
        <div className="burger-line" /><div className="burger-line" /><div className="burger-line" />
      </button>
      <Sidebar isSidebarVisible={isSidebarVisible} toggleSidebar={() => setIsSidebarVisible((p) => !p)} />

      <section className="upload-header">
        <div className="upload-header-content">
          <h1>📰 My Stories</h1>
          <p>Manage and edit your citizen journalism submissions.</p>
        </div>
        <button className="btn-primary" onClick={() => setCreateOpen(true)}>+ New Story</button>
      </section>

      <div className="my-uploads-content">
        {loading && <div className="uploads-loading">Loading your stories…</div>}

        {!loading && uploads.length === 0 && (
          <div className="uploads-empty">
            <p>You haven't uploaded any stories yet.</p>
            <button className="btn-primary" onClick={() => setCreateOpen(true)}>Upload your first story</button>
          </div>
        )}

        <div className="uploads-grid">
          {uploads.map((u) => (
            <UploadCard
              key={u.id}
              upload={u}
              onEdit={setEditTarget}
              onDelete={setDeleteTarget}
            />
          ))}
        </div>
      </div>

      {editTarget && (
        <EditModal
          upload={editTarget}
          onSave={handleSave}
          onClose={() => setEditTarget(null)}
        />
      )}

      {deleteTarget && (
        <DeleteConfirm
          upload={deleteTarget}
          onConfirm={handleDelete}
          onClose={() => setDeleteTarget(null)}
        />
      )}

      {createOpen && (
        <CreateStoryModal
          initialQuickFile={createSeed?.quickFile || null}
          initialPreferences={createSeed?.uploadPreferences || null}
          onCreated={fetchUploads}
          onClose={() => {
            setCreateOpen(false);
            setCreateSeed(null);
          }}
        />
      )}
    </div>
  );
};

export default MyUploads;
