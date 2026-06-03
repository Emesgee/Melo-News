import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import './UploadForm.css';
import { api } from '../services/api';
import { useAuth } from '../utils/AuthContext';
import { useToast } from '../utils/ToastContext';
import { DRAFT_KEY, MAX_FILE_SIZE, ALLOWED_FILE_TYPES } from '../components/upload/uploadConstants';
import { GeneralInfoForm, LocationForm, FileUploadForm } from '../components/upload/UploadSubComponents';
import { chunkedUpload } from '../utils/chunkedUpload';
import { SEVERITY_CONFIG } from '../constants/severity';

const CHUNK_THRESHOLD = 5 * 1024 * 1024; // use chunked upload for files > 5 MB

const SEVERITY_LEVELS = ['LOW', 'MEDIUM', 'HIGH'];
const SEVERITY_ANCHORS = {
  LOW: 'Ongoing situation, no immediate harm',
  MEDIUM: 'Notable incident, possible harm or disruption',
  HIGH: 'Active danger, casualties, or time-critical',
};

/* ── Main Report Form ─────────────────────────────────────────────────────── */

// Detect if browser is set to Arabic
const isArabic = () => {
  const lang = (navigator.language || navigator.userLanguage || '').toLowerCase();
  return lang.startsWith('ar');
};

// Arabic label map for form fields
const AR = {
  shareNews: 'شارك خبرك',
  tagline: 'سريع وبسيط. انشر خبرك على الخريطة في ثوانٍ.',
  title: 'العنوان *',
  titlePlaceholder: 'أدخل عنواناً للقصة الإخبارية',
  tags: 'الوسوم',
  tagsPlaceholder: 'أدخل وسوماً ذات صلة (مفصولة بفواصل)',
  subject: 'الموضوع / الملخص',
  subjectPlaceholder: 'أدخل وصفاً موجزاً للمحتوى',
  city: 'المدينة *',
  cityPlaceholder: 'المدينة التي وقع فيها الحدث',
  country: 'الدولة *',
  countryPlaceholder: 'أدخل اسم الدولة',
  useLocation: '📡 استخدم موقعي',
  locating: 'جارٍ التحديد...',
  publish: '🚀 إرسال التقرير',
  uploading: 'جارٍ الإرسال...',
};

const UploadForm = () => {
  const navigate = useNavigate();
  const { isLoggedIn, authLoading } = useAuth();
  const { addToast } = useToast();
  const [rtl] = useState(isArabic); // Arabic RTL detection
  const [selectedFile, setSelectedFile] = useState(null);
  const [title, setTitle] = useState('');
  const [tags, setTags] = useState('');
  const [subject, setSubject] = useState('');
  const [city, setCity] = useState('');
  const [country, setCountry] = useState('');
  const [lat, setLat] = useState(null);
  const [lon, setLon] = useState(null);
  const [severity, setSeverity] = useState('LOW');
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [messageType, setMessageType] = useState('');
  const [isCheckingPhoto, setIsCheckingPhoto] = useState(false);
  const [isLocating, setIsLocating] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [apiReachable, setApiReachable] = useState(true);
  const [geocodeAvailable, setGeocodeAvailable] = useState(true);
  const [autoStripGps, setAutoStripGps] = useState(true);
  const [witnessStatement, setWitnessStatement] = useState('');
  const [sourceType, setSourceType] = useState('eyewitness');
  const [isSensitive, setIsSensitive] = useState(false);
  const draftRestoredRef = useRef(false);
  const geocodeTimerRef = useRef(null);

  // ── EXIF safety state ─────────────────────────────────────────────
  const [exifGpsWarning, setExifGpsWarning] = useState(false);   // show warning banner
  const [strippedFile, setStrippedFile] = useState(null);         // file with GPS removed
  const rawFileRef = useRef(null);                                 // original file before strip

  /**
   * Strip GPS/device EXIF from an image by re-encoding through canvas.
   * Returns a new File with the same name but clean metadata.
   */
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
      img.onerror = () => { URL.revokeObjectURL(url); resolve(file); };
      img.src = url;
    });
  }, []);

  // ── Draft auto-save: restore on mount ────────────────────────────
  useEffect(() => {
    if (draftRestoredRef.current) return;
    try {
      const saved = localStorage.getItem(DRAFT_KEY);
      if (saved) {
        const draft = JSON.parse(saved);
        if (draft.title) setTitle(draft.title);
        if (draft.tags) setTags(draft.tags);
        if (draft.subject) setSubject(draft.subject);
        if (draft.city) setCity(draft.city);
        if (draft.country) setCountry(draft.country);
        if (draft.severity) setSeverity(draft.severity);
        setMessage('📝 Draft restored from your previous session.');
        setMessageType('info');
      }
    } catch (_) { /* ignore corrupt data */ }
    draftRestoredRef.current = true;
  }, []);

  // ── Draft auto-save: persist on change ───────────────────────────
  useEffect(() => {
    if (!draftRestoredRef.current) return;
    const hasDraft = title || tags || subject || city || country;
    if (hasDraft) {
      try {
        localStorage.setItem(DRAFT_KEY, JSON.stringify({ title, tags, subject, city, country, severity }));
      } catch (_) { /* storage full, ignore */ }
    }
  }, [title, tags, subject, city, country, severity]);

  const clearDraft = () => {
    try { localStorage.removeItem(DRAFT_KEY); } catch (_) { /* ignore */ }
  };

  // Lightweight backend health probe to catch tunnel/backend-down cases early.
  const checkApiReachability = useCallback(async ({ silent = false } = {}) => {
    try {
      await api.get('/health', { timeout: 5000 });
      setApiReachable(true);
      return true;
    } catch (_) {
      setApiReachable(false);
      if (!silent) {
        setMessage('Cannot reach backend API. Start your backend or ensure the API tunnel is active, then try again.');
        setMessageType('error');
      }
      return false;
    }
  }, []);

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
        try {
          const response = await api.get('/ai/geocode', {
            params: { q: `${latitude},${longitude}` },
          });
          setGeocodeAvailable(true);
          if (response.data.city) setCity(response.data.city);
          if (response.data.country) setCountry(response.data.country);
        } catch (e) {
          if (e?.response?.status === 503) {
            setGeocodeAvailable(false);
            setMessage('Geocoding service is unavailable. Coordinates were captured, but city/country autofill is disabled for now.');
            setMessageType('info');
          }
        }
        setIsLocating(false);
      },
      () => {
        setMessage('Unable to retrieve your location.');
        setMessageType('error');
        setIsLocating(false);
      }
    );
  };

  useEffect(() => {
    checkApiReachability({ silent: true });
  }, [checkApiReachability]);

  // Geocode city/country → coordinates so the report can be placed on the map
  // without the reporter ever exposing a precise pin.
  useEffect(() => {
    if (geocodeTimerRef.current) clearTimeout(geocodeTimerRef.current);
    if (!geocodeAvailable) {
      return () => { if (geocodeTimerRef.current) clearTimeout(geocodeTimerRef.current); };
    }
    if (city.trim() && country.trim()) {
      geocodeTimerRef.current = setTimeout(async () => {
        try {
          const response = await api.get('/ai/geocode', {
            params: { q: `${city.trim()}, ${country.trim()}` },
          });
          if (response.data.lat && response.data.lon) {
            setGeocodeAvailable(true);
            setLat(response.data.lat);
            setLon(response.data.lon);
          }
        } catch (error) {
          if (error?.response?.status === 503) {
            setGeocodeAvailable(false);
          }
        }
      }, 600);
    }
    return () => { if (geocodeTimerRef.current) clearTimeout(geocodeTimerRef.current); };
  }, [city, country, geocodeAvailable]);

  // ── Check an attached photo for embedded GPS (safety only) ──────────
  // We no longer let the model author the report (title/subject/tags); the
  // only thing we read back is EXIF, so the reporter can strip a location-
  // revealing photo before it leaves their device. (The backend also strips
  // EXIF server-side as a second layer.)
  const checkPhotoForGps = useCallback(async (file) => {
    setIsCheckingPhoto(true);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const response = await api.post('/ai/analyze', formData);
      return response.data?.exif || null;
    } catch (_) {
      return null; // can't check — backend still sanitizes on upload
    } finally {
      setIsCheckingPhoto(false);
    }
  }, []);

  // ── Validate & set file (shared by click + drag-drop) ───────────
  const processFile = useCallback((file) => {
    if (!file) {
      setMessage('No file selected. Please choose a file.');
      setMessageType('error');
      return;
    }

    if (!ALLOWED_FILE_TYPES.includes(file.type)) {
      setMessage('That file type isn’t supported. Choose an image, video, audio or document file.');
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
    rawFileRef.current = file;
    setStrippedFile(null);
    setExifGpsWarning(false);
    setMessage(`File "${file.name}" attached.`);
    setMessageType('success');

    const isMedia =
      file.type.startsWith('image/') ||
      file.type.startsWith('video/') ||
      file.type.startsWith('audio/');
    if (!isMedia) return;

    checkPhotoForGps(file).then((exif) => {
      if (!exif?.has_gps) return;
      if (autoStripGps && file.type.startsWith('image/')) {
        stripExifFromImage(file).then((cleanFile) => {
          setStrippedFile(cleanFile);
          setExifGpsWarning(false);
          setMessage('✅ GPS metadata removed automatically.');
          setMessageType('success');
        });
      } else {
        setExifGpsWarning(true);
      }
    });
  }, [autoStripGps, checkPhotoForGps, stripExifFromImage]);

  const handleFileChange = (e) => {
    processFile(e.target.files[0]);
  };

  // ── Drag-and-drop handler ────────────────────────────────────────
  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    processFile(file);
  }, [processFile]);

  // ── Remove file handler ──────────────────────────────────────────
  const handleRemoveFile = useCallback(() => {
    setSelectedFile(null);
    setExifGpsWarning(false);
    setStrippedFile(null);
    rawFileRef.current = null;
    const fileInput = document.getElementById('fileInput');
    if (fileInput) fileInput.value = '';
    setMessage('');
  }, []);

  const resetForm = () => {
    setSelectedFile(null);
    setTitle(''); setTags(''); setSubject('');
    setCity(''); setCountry(''); setLat(null); setLon(null);
    setSeverity('LOW'); setWitnessStatement(''); setSourceType('eyewitness'); setIsSensitive(false);
    setExifGpsWarning(false); setStrippedFile(null); rawFileRef.current = null;
    setUploadProgress(0);
    const fileInput = document.getElementById('fileInput');
    if (fileInput) fileInput.value = '';
    clearDraft();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (authLoading || !isLoggedIn) {
      setMessage('You need to log in before submitting a report.');
      setMessageType('error');
      return;
    }

    // Required contract: what happened (title) + where (city + country).
    // Media and a precise pin are optional.
    if (!title.trim()) {
      setMessage('Please describe what happened in the title.');
      setMessageType('error');
      return;
    }
    if (!city.trim() || !country.trim()) {
      setMessage('Please add at least a city and country so the report can be placed on the map.');
      setMessageType('error');
      return;
    }

    const backendUp = await checkApiReachability();
    if (!backendUp) return;

    setIsLoading(true);
    setUploadProgress(0);
    setMessage('Submitting your report…');
    setMessageType('info');

    const fileToUpload = strippedFile || selectedFile;
    const metadata = {
      title: title.trim(),
      tags: tags.trim(),
      subject: subject.trim(),
      city: city.trim(),
      country: country.trim(),
      lat: lat !== null && !isNaN(lat) ? lat : null,
      lon: lon !== null && !isNaN(lon) ? lon : null,
      severity,
      witness_statement: witnessStatement.trim() || null,
      source_type: sourceType,
      is_sensitive: isSensitive,
    };

    try {
      let resData;
      if (fileToUpload && fileToUpload.size > CHUNK_THRESHOLD) {
        setMessage('📡 Uploading in chunks — safe for slow connections…');
        resData = await chunkedUpload(api, fileToUpload, metadata, (pct) => setUploadProgress(pct));
      } else {
        const formData = new FormData();
        if (fileToUpload) formData.append('file', fileToUpload);
        formData.append('title', metadata.title);
        formData.append('tags', metadata.tags);
        formData.append('subject', metadata.subject);
        formData.append('city', metadata.city);
        formData.append('country', metadata.country);
        formData.append('severity', severity);
        formData.append('source_type', sourceType);
        formData.append('is_sensitive', isSensitive ? 'true' : 'false');
        if (witnessStatement.trim()) formData.append('witness_statement', witnessStatement.trim());
        if (metadata.lat !== null) formData.append('lat', metadata.lat);
        if (metadata.lon !== null) formData.append('lon', metadata.lon);

        const response = await api.post('/file_upload/upload', formData, {
          onUploadProgress: (progressEvent) => {
            const pct = progressEvent.total
              ? Math.round((progressEvent.loaded * 100) / progressEvent.total)
              : 0;
            setUploadProgress(pct);
          },
        });
        resData = response.data;
      }

      // Honest post-gate state: most reporters are pre-moderated (PENDING),
      // so never claim public visibility the gate hasn't granted.
      const published = resData?.verification_status === 'VERIFIED';
      resetForm();
      if (published) {
        addToast('Report published — it’s now visible on the map.', 'success');
      } else {
        addToast(
          'Report submitted. It’s pending review and will appear publicly once a moderator confirms it — this is what keeps reports on Melo credible.',
          'info'
        );
      }
      navigate('/my-uploads');
    } catch (error) {
      const errorMsg = !error.response
        ? 'Network error: backend is unreachable. Verify the backend or API tunnel, then retry.'
        : error.response?.status === 401
          ? 'Your session is not authenticated. Please log in, then try again.'
          : (error.response?.data?.message || error.message || 'Network error occurred. Please check your connection and try again.');
      setMessage(errorMsg);
      setMessageType('error');
    } finally {
      setIsLoading(false);
      setUploadProgress(0);
    }
  };

  return (
    <div className="upload-page" dir={rtl ? 'rtl' : 'ltr'} lang={rtl ? 'ar' : undefined}>
      {/* Header */}
      <section className="upload-header">
        <div className="upload-header-content">
          <h1>🚀 {rtl ? AR.shareNews : 'Submit a report'}</h1>
          <p>{rtl ? AR.tagline : 'Tell us what happened and where. Photo or video is optional.'}</p>
        </div>
      </section>

      {/* Main Content */}
      <div className="upload-content">

        {autoStripGps && (
          <div className="message info" style={{ marginBottom: '0.6rem' }}>
            🛡️ GPS safety mode is active: photo GPS metadata will be removed automatically when detected.
          </div>
        )}

        {!apiReachable && (
          <div className="message error" style={{ marginTop: '0.75rem' }}>
            Backend API is unreachable. Check the backend or API tunnel, then retry.
          </div>
        )}

        {isCheckingPhoto && (
          <div className="ai-analysis-banner">
            <div className="spinner"></div>
            <div className="text">Checking photo for embedded location…</div>
          </div>
        )}

        {/* EXIF GPS Safety Warning */}
        {exifGpsWarning && (
          <div className="ai-analysis-banner" style={{background: 'linear-gradient(135deg, #dc2626 0%, #b91c1c 100%)'}}>
            <div className="icon">🛡️</div>
            <div className="text">
              <div style={{fontWeight: 700}}>Safety Warning: GPS location found in photo metadata</div>
              <div style={{fontSize: '0.85em', marginTop: 4, opacity: 0.95}}>
                Your photo contains embedded GPS coordinates that could reveal where it was taken.
                In conflict zones, this can be dangerous.
              </div>
              <div style={{display: 'flex', gap: '0.5rem', marginTop: 8, flexWrap: 'wrap'}}>
                <button
                  type="button"
                  style={{background: '#fff', color: '#b91c1c', border: 'none', borderRadius: 6, padding: '4px 12px', fontWeight: 700, cursor: 'pointer', fontSize: '0.82em'}}
                  onClick={async () => {
                    const clean = await stripExifFromImage(rawFileRef.current || selectedFile);
                    setStrippedFile(clean);
                    setExifGpsWarning(false);
                    setMessage('✅ GPS metadata removed. Your photo is safe to upload.');
                    setMessageType('success');
                  }}
                >
                  Remove GPS data before upload
                </button>
                <button
                  type="button"
                  style={{background: 'rgba(255,255,255,0.2)', color: '#fff', border: '1px solid rgba(255,255,255,0.4)', borderRadius: 6, padding: '4px 12px', cursor: 'pointer', fontSize: '0.82em'}}
                  onClick={() => setExifGpsWarning(false)}
                >
                  Keep GPS and continue
                </button>
              </div>
            </div>
          </div>
        )}

        <div className="upload-container">
          <form className="upload-form-content" onSubmit={handleSubmit}>
            <div className="form-columns">
              {/* Left Column: the report (title/where/witness) */}
              <div className="form-column form-column-main">
                <GeneralInfoForm
                  title={title}
                  setTitle={setTitle}
                  tags={tags}
                  setTags={setTags}
                  subject={subject}
                  setSubject={setSubject}
                  rtl={rtl}
                  labels={rtl ? AR : {}}
                />

                {/* Severity */}
                <div className="form-section">
                  <h3>⚠️ {rtl ? 'الخطورة' : 'Severity'}</h3>
                  <div role="group" aria-label="Severity" style={{display: 'flex', gap: 8}}>
                    {SEVERITY_LEVELS.map((lvl) => {
                      const active = severity === lvl;
                      const cfg = SEVERITY_CONFIG[lvl];
                      return (
                        <button
                          type="button"
                          key={lvl}
                          onClick={() => setSeverity(lvl)}
                          aria-pressed={active}
                          style={{
                            flex: 1,
                            textAlign: 'left',
                            padding: '8px 10px',
                            borderRadius: 8,
                            cursor: 'pointer',
                            background: active ? `${cfg.color}1a` : 'transparent',
                            border: `1px solid ${active ? cfg.color : 'rgba(148,163,184,0.4)'}`,
                            color: active ? cfg.color : 'inherit',
                          }}
                        >
                          <div style={{fontWeight: 700, fontSize: '0.85rem'}}>{cfg.emoji} {lvl}</div>
                          <div style={{fontSize: '0.72rem', opacity: 0.85, marginTop: 2}}>{SEVERITY_ANCHORS[lvl]}</div>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Source type + Witness statement */}
                <div className="form-section" dir={rtl ? 'rtl' : undefined}>
                  <h3>🎙️ {rtl ? 'مصدر الشهادة' : 'Source & Witness'}</h3>
                  <div className="form-group">
                    <label className="form-label">{rtl ? 'نوع المصدر' : 'Source type'}</label>
                    <select className="form-select" value={sourceType} onChange={e => setSourceType(e.target.value)}>
                      <option value="eyewitness">{rtl ? '👁️ شاهد عيان' : '👁️ Eyewitness'}</option>
                      <option value="secondhand">{rtl ? '🗣️ رواية ثانوية' : '🗣️ Secondhand account'}</option>
                      <option value="official">{rtl ? '📋 بيان رسمي' : '📋 Official statement'}</option>
                      <option value="unknown">{rtl ? '❓ غير معروف' : '❓ Unknown'}</option>
                    </select>
                  </div>
                  <div className="form-group" style={{marginBottom:0}}>
                    <label className="form-label">{rtl ? 'شهادتك (اختياري)' : 'Your witness statement (optional)'}</label>
                    <textarea
                      className="form-textarea"
                      placeholder={rtl ? 'صِف ما رأيته أو سمعته بكلماتك الخاصة…' : 'Describe what you saw or heard in your own words…'}
                      value={witnessStatement}
                      onChange={e => setWitnessStatement(e.target.value)}
                      rows="3"
                      dir={rtl ? 'rtl' : undefined}
                    />
                  </div>
                  <label style={{display:'flex', alignItems:'center', gap:'0.5rem', marginTop:'0.75rem', fontSize:'0.83rem', cursor:'pointer', color:'#f87171'}}>
                    <input type="checkbox" checked={isSensitive} onChange={e => setIsSensitive(e.target.checked)} style={{accentColor:'#ef4444'}} />
                    {rtl ? '⚠️ محتوى حساس — يتطلب مراجعة تحريرية قبل النشر' : '⚠️ Contains graphic or identifying content — hold for review before publishing'}
                  </label>
                </div>
              </div>

              {/* Right Column: location + optional media */}
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
                  rtl={rtl}
                  labels={rtl ? AR : {}}
                />

                <FileUploadForm
                  selectedFile={selectedFile}
                  handleFileChange={handleFileChange}
                  handleDrop={handleDrop}
                  handleRemoveFile={handleRemoveFile}
                  isDragging={isDragging}
                  setIsDragging={setIsDragging}
                />

                <label style={{display:'flex', alignItems:'center', gap:'0.5rem', marginTop:'0.5rem', fontSize:'0.8rem', cursor:'pointer'}}>
                  <input type="checkbox" checked={autoStripGps} onChange={e => setAutoStripGps(e.target.checked)} />
                  {rtl ? 'إزالة بيانات GPS من الصور تلقائياً' : 'Auto-remove GPS metadata from photos'}
                </label>

                {message && (
                  <div className={`message ${messageType}`}>
                    {message}
                  </div>
                )}

                {/* Upload Progress Bar */}
                {isLoading && (
                  <div className="upload-progress">
                    <div className="upload-progress-bar">
                      <div className="upload-progress-fill" style={{ width: `${uploadProgress}%` }} />
                    </div>
                    <span className="upload-progress-text">{uploadProgress}%</span>
                  </div>
                )}

                {/* Form Actions */}
                <div className="form-actions-side">
                  {!isLoggedIn && !authLoading && (
                    <>
                      <div className="message error" style={{ marginBottom: '0.75rem' }}>
                        Session expired or not authenticated. Please log in to submit.
                      </div>
                      <button
                        type="button"
                        className="submit-btn"
                        onClick={() => navigate('/login')}
                        style={{ marginBottom: '0.75rem' }}
                      >
                        Go to Login
                      </button>
                    </>
                  )}

                  <button
                    type="submit"
                    className={`submit-btn ${isLoading ? 'loading' : ''}`}
                    disabled={isLoading || authLoading || !isLoggedIn}
                    title={!isLoggedIn ? 'Login required to submit' : 'Submit report'}
                  >
                    {isLoading ? (
                      <>
                        <div className="spinner"></div>
                        {rtl ? AR.uploading : `Submitting… ${uploadProgress}%`}
                      </>
                    ) : (
                      <>
                        <span>🚀</span>
                        {rtl ? AR.publish : 'Submit report'}
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
