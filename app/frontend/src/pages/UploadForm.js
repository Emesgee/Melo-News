import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import Sidebar from '../components/navigationBars/Sidebar';
import './UploadForm.css';
import { api } from '../services/api';
import { useAuth } from '../utils/AuthContext';
import { DRAFT_KEY, MAX_FILE_SIZE, ALLOWED_FILE_TYPES } from '../components/upload/uploadConstants';
import { StepIndicator, GeneralInfoForm, LocationForm, FileUploadForm } from '../components/upload/UploadSubComponents';
import { chunkedUpload } from '../utils/chunkedUpload';
import { enqueue, getAll, remove, updateStatus } from '../utils/offlineQueue';

const CHUNK_THRESHOLD = 5 * 1024 * 1024; // use chunked upload for files > 5 MB

/* ── Main Upload Form ───────────────────────────────────────────────────────────── */

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
  city: 'المدينة',
  cityPlaceholder: 'المدينة التي وقع فيها الحدث',
  country: 'الدولة',
  countryPlaceholder: 'أدخل اسم الدولة',
  useLocation: '📡 استخدم موقعي',
  locating: 'جارٍ التحديد...',
  publish: '🚀 نشر',
  uploading: 'جارٍ الرفع...',
  offlineQueued: 'أنت غير متصل. سيتم رفع القصة تلقائياً عند الاتصال.',
};

const UploadForm = () => {
  const navigate = useNavigate();
  const { isLoggedIn, authLoading } = useAuth();
  const [isSidebarVisible, setIsSidebarVisible] = useState(false);
  const [rtl] = useState(isArabic); // Arabic RTL detection
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
  const [messageType, setMessageType] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [analysisSteps, setAnalysisSteps] = useState([]);
  const [transcription, setTranscription] = useState('');
  const [transcriptLanguage, setTranscriptLanguage] = useState('');
  const [exifData, setExifData] = useState(null);
  const [isLocating, setIsLocating] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [apiReachable, setApiReachable] = useState(true);
  const [geocodeAvailable, setGeocodeAvailable] = useState(true);
  const [aiAnalyzeAvailable, setAiAnalyzeAvailable] = useState(true);
  const [lowBandwidth, setLowBandwidth] = useState(false);
  const [witnessStatement, setWitnessStatement] = useState('');
  const [sourceType, setSourceType] = useState('eyewitness');
  const [isSensitive, setIsSensitive] = useState(false);
  const draftRestoredRef = useRef(false);
  const geocodeTimerRef = useRef(null);

  // ── EXIF safety state ─────────────────────────────────────────────
  const [exifGpsWarning, setExifGpsWarning] = useState(false);   // show warning banner
  const [strippedFile, setStrippedFile] = useState(null);         // file with GPS removed
  const rawFileRef = useRef(null);                                 // original file before strip

  // ── Connectivity & offline queue ──────────────────────────────────
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [queuedCount, setQueuedCount] = useState(0);

  useEffect(() => {
    const up = () => setIsOnline(true);
    const down = () => setIsOnline(false);
    window.addEventListener('online', up);
    window.addEventListener('offline', down);
    return () => { window.removeEventListener('online', up); window.removeEventListener('offline', down); };
  }, []);

  const refreshQueueCount = useCallback(async () => {
    try { const items = await getAll(); setQueuedCount(items.filter((i) => i.status === 'pending').length); }
    catch (_) {}
  }, []);

  useEffect(() => { refreshQueueCount(); }, [refreshQueueCount]);

  // Auto-flush queue when back online
  useEffect(() => {
    if (!isOnline) return;
    (async () => {
      const items = await getAll().catch(() => []);
      const pending = items.filter((i) => i.status === 'pending');
      if (pending.length === 0) return;
      setMessage(`📶 Back online — uploading ${pending.length} queued story${pending.length > 1 ? 's' : ''}…`);
      setMessageType('info');
      for (const item of pending) {
        try {
          await updateStatus(item.id, 'uploading');
          const fileToSend = item.file;
          if (fileToSend.size > CHUNK_THRESHOLD) {
            await chunkedUpload(api, fileToSend, item.metadata, () => {});
          } else {
            const fd = new FormData();
            fd.append('file', fileToSend);
            Object.entries(item.metadata).forEach(([k, v]) => { if (v != null) fd.append(k, v); });
            await api.post('/file_upload/upload', fd);
          }
          await remove(item.id);
        } catch { await updateStatus(item.id, 'failed'); }
      }
      await refreshQueueCount();
      setMessage('✅ Queued stories uploaded successfully.');
      setMessageType('success');
    })();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOnline]);

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

  // Compute current step
  const currentStep = isAnalyzing ? 2 : selectedFile ? 3 : 1;

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
        if (draft.fileTypeId) setFileTypeId(draft.fileTypeId);
        setMessage('📝 Draft restored from your previous session.');
        setMessageType('info');
      }
    } catch (_) { /* ignore corrupt data */ }
    draftRestoredRef.current = true;
  }, []);

  // ── Draft auto-save: persist on change ───────────────────────────
  useEffect(() => {
    if (!draftRestoredRef.current) return;
    const hasDraft = title || tags || subject || city || country || fileTypeId;
    if (hasDraft) {
      try {
        localStorage.setItem(DRAFT_KEY, JSON.stringify({ title, tags, subject, city, country, fileTypeId }));
      } catch (_) { /* storage full, ignore */ }
    }
  }, [title, tags, subject, city, country, fileTypeId]);

  const clearDraft = () => {
    try { localStorage.removeItem(DRAFT_KEY); } catch (_) { /* ignore */ }
  };

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

  // Lightweight backend health probe to catch tunnel/backend-down cases early.
  const checkApiReachability = useCallback(async ({ silent = false } = {}) => {
    try {
      await api.get('/health', { timeout: 5000 });
      setApiReachable(true);
      return true;
    } catch (_) {
      setApiReachable(false);
      if (!silent) {
        setMessage('Cannot reach backend API. Start your backend or ensure SSH tunnel mapping is active for the API target, then try again.');
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
      (error) => {
        setMessage('Unable to retrieve your location.');
        setMessageType('error');
        setIsLocating(false);
      }
    );
  };


  const toggleSidebar = () => setIsSidebarVisible((prev) => !prev);

  useEffect(() => {
    checkApiReachability({ silent: true });
  }, [checkApiReachability]);

  useEffect(() => {
    const fetchFileTypes = async () => {
      try {
        const response = await api.get('/file-types/');
        setFileTypes(response.data);
      } catch (error) {
        setMessage('Failed to load file types. Please refresh the page.');
        setMessageType('error');
      }
    };
    fetchFileTypes();
  }, []);

  useEffect(() => {
    if (geocodeTimerRef.current) clearTimeout(geocodeTimerRef.current);
    if (!geocodeAvailable) {
      return () => { if (geocodeTimerRef.current) clearTimeout(geocodeTimerRef.current); };
    }
    if (city.trim() && country.trim()) {
      geocodeTimerRef.current = setTimeout(async () => {
        try {
          setMessage('Fetching location coordinates...');
          setMessageType('info');

          const response = await api.get('/ai/geocode', {
            params: { q: `${city.trim()}, ${country.trim()}` },
          });

          if (response.data.lat && response.data.lon) {
            setGeocodeAvailable(true);
            setLat(response.data.lat);
            setLon(response.data.lon);
            setMessage('Location found successfully!');
            setMessageType('success');
          } else {
            setMessage('Location not found. Please check the city and country names.');
            setMessageType('error');
          }
        } catch (error) {
          if (error?.response?.status === 503) {
            setGeocodeAvailable(false);
            setMessage('Geocoding service is currently unavailable. You can still continue and submit by entering coordinates manually.');
            setMessageType('info');
          } else {
            setMessage('Error fetching location data. Please try again.');
            setMessageType('error');
          }
        }
      }, 600);
    }
    return () => { if (geocodeTimerRef.current) clearTimeout(geocodeTimerRef.current); };
  }, [city, country, geocodeAvailable]);

  // ── Analyze uploaded media via AI ──────────────────────────────────
  const analyzeMedia = useCallback(async (file) => {
    setIsAnalyzing(true);
    setAnalysisSteps([]);
    setTranscription('');
    setExifData(null);
    setMessage('🔍 Analyzing media with AI... This may take a moment.');
    setMessageType('info');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await api.post('/ai/analyze', formData);

      const data = response.data;
      setAnalysisResult(data);

      if (data.analysis_steps) setAnalysisSteps(data.analysis_steps);

      if (data.title) setTitle(data.title);
      if (data.tags) setTags(data.tags);
      if (data.subject) setSubject(data.subject);
      if (data.city) setCity(data.city);
      if (data.country) setCountry(data.country);

      if (data.transcription) {
        setTranscription(data.transcription);
        setTranscriptLanguage(data.transcript_language || '');
      }

      if (data.exif) {
        setExifData(data.exif);
        if (data.exif.has_gps) {
          setLat(data.exif.lat);
          setLon(data.exif.lon);
        }
      }

      if (data.ai_used === false) {
        setMessage('⚠️ AI service is not configured — please fill in the fields manually.');
        setMessageType('error');
      } else {
        const confidencePct = data.confidence ? (data.confidence * 100).toFixed(0) : '?';
        setMessage(`✅ AI Analysis complete! Confidence: ${confidencePct}% — Review and edit the fields before submitting.`);
        setMessageType('success');
      }
      return data;
    } catch (error) {
      if (error?.response?.status === 400) {
        setAiAnalyzeAvailable(false);
        setMessage(`⚠️ AI analysis request was rejected: ${error.response?.data?.error || error.response?.data?.message || 'Invalid request'}. You can continue by filling fields manually.`);
      } else {
        setAiAnalyzeAvailable(false);
        setMessage(`⚠️ AI analysis unavailable: ${error.response?.data?.error || error.message || 'Service error'}. Please fill form manually.`);
      }
      setMessageType('error');
      return null;
    } finally {
      setIsAnalyzing(false);
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
    rawFileRef.current = file;
    setStrippedFile(null);
    setExifGpsWarning(false);

    const inferredTypeId = findMatchingFileTypeId(file);
    if (inferredTypeId) {
      setFileTypeId(inferredTypeId);
    }
    setMessage(`File "${file.name}" selected successfully!`);
    setMessageType('success');

    // Auto-analyze only when AI endpoint is currently available and not in low-bandwidth mode.
    const canAutoAnalyze = !lowBandwidth && aiAnalyzeAvailable && (
      file.type.startsWith('image/') ||
      file.type.startsWith('video/') ||
      file.type.startsWith('audio/')
    );
    if (canAutoAnalyze) {
      analyzeMedia(file).then((result) => {
        // After analysis, if GPS found in EXIF, show safety warning
        if (result?.exif?.has_gps) {
          setExifGpsWarning(true);
        }
      });
    }
  }, [analyzeMedia, aiAnalyzeAvailable, findMatchingFileTypeId]);

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
    setAnalysisResult(null);
    setAnalysisSteps([]);
    setExifData(null);
    setTranscription('');
    setTranscriptLanguage('');
    setExifGpsWarning(false);
    setStrippedFile(null);
    rawFileRef.current = null;
    const fileInput = document.getElementById('fileInput');
    if (fileInput) fileInput.value = '';
    setMessage('');
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (authLoading || !isLoggedIn) {
      setMessage('You need to log in before publishing uploads.');
      setMessageType('error');
      return;
    }

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

    if (!selectedFileTypeAllowsFile()) {
      const ext = getFileExtension(selectedFile?.name);
      setMessage(`Selected file type does not allow .${ext} files. Choose the matching file type before publishing.`);
      setMessageType('error');
      return;
    }

    const backendUp = await checkApiReachability();
    if (!backendUp) {
      return;
    }

    setIsLoading(true);
    setUploadProgress(0);
    setMessage('Uploading your file... Please wait.');
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
      witness_statement: witnessStatement.trim() || null,
      source_type: sourceType,
      is_sensitive: isSensitive,
    };

    // ── Offline: queue and bail ───────────────────────────────────────
    if (!isOnline) {
      try {
        await enqueue(fileToUpload, metadata);
        await refreshQueueCount();
        setMessage('📵 You\'re offline. Story saved — it will upload automatically when you reconnect.');
        setMessageType('info');
        setSelectedFile(null); setTitle(''); setTags(''); setSubject('');
        setCity(''); setCountry(''); setLat(null); setLon(null); setFileTypeId('');
        setAnalysisResult(null); setAnalysisSteps([]); setExifData(null); setTranscription('');
        setExifGpsWarning(false); setStrippedFile(null); rawFileRef.current = null;
        clearDraft();
        const fileInput = document.getElementById('fileInput');
        if (fileInput) fileInput.value = '';
      } catch {
        setMessage('Failed to save story offline. Please try again.');
        setMessageType('error');
      } finally {
        setIsLoading(false);
      }
      return;
    }

    // ── Online: chunked for large files, direct for small ────────────
    const formData = new FormData();
    formData.append('file', fileToUpload);
    formData.append('file_type_id', fileTypeId);
    formData.append('title', title.trim());
    formData.append('tags', tags.trim());
    formData.append('subject', subject.trim());
    formData.append('city', city.trim());
    formData.append('country', country.trim());
    if (witnessStatement.trim()) formData.append('witness_statement', witnessStatement.trim());
    formData.append('source_type', sourceType);
    formData.append('is_sensitive', isSensitive ? 'true' : 'false');
    if (lat !== null && !isNaN(lat)) formData.append('lat', lat);
    if (lon !== null && !isNaN(lon)) formData.append('lon', lon);

    try {
      if (fileToUpload.size > CHUNK_THRESHOLD) {
        setMessage('📡 Uploading in chunks — safe for slow connections…');
        await chunkedUpload(api, fileToUpload, metadata, (pct) => setUploadProgress(pct));
      } else {
        await api.post('/file_upload/upload', formData, {
          onUploadProgress: (progressEvent) => {
            const pct = progressEvent.total
              ? Math.round((progressEvent.loaded * 100) / progressEvent.total)
              : 0;
            setUploadProgress(pct);
          },
        });
      }

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
      setAnalysisResult(null);
      setAnalysisSteps([]);
      setExifData(null);
      setTranscription('');
      setUploadProgress(0);
      setExifGpsWarning(false);
      setStrippedFile(null);
      rawFileRef.current = null;
      clearDraft();

      const fileInput = document.getElementById('fileInput');
      if (fileInput) fileInput.value = '';

      setTimeout(() => {
        setMessage('✅ Uploaded! Search by title or location to find it on the map.');
        setMessageType('success');
      }, 2000);
    } catch (error) {
      const errorMsg = !error.response
        ? 'Network error: backend is unreachable. Verify local backend or SSH tunnel, then retry.'
        : error.response?.status === 401
          ? 'Your session is not authenticated. Please log in, then try upload again.'
          : (error.response?.data?.message || error.message || 'Network error occurred. Please check your connection and try again.');
      setMessage(errorMsg);
      setMessageType('error');
    } finally {
      setIsLoading(false);
      setUploadProgress(0);
    }
  };

  // Whether to show the details form (progressive disclosure)
  const showDetails = !!selectedFile;

  return (
    <div className="upload-page" dir={rtl ? 'rtl' : 'ltr'} lang={rtl ? 'ar' : undefined}>
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
          <h1>🚀 {rtl ? AR.shareNews : 'Share News'}</h1>
          <p>{rtl ? AR.tagline : 'Fast and simple. Get your news on the map in seconds.'}</p>
        </div>
      </section>

      {/* Main Content */}
      <div className="upload-content">
        {/* Step Indicator */}
        <StepIndicator currentStep={currentStep} />

        {/* Low-bandwidth mode toggle */}
        <div style={{display:'flex', justifyContent:'flex-end', marginBottom:'0.5rem'}}>
          <label style={{display:'flex', alignItems:'center', gap:'0.4rem', fontSize:'0.82rem', cursor:'pointer', opacity:0.75}}>
            <input
              type="checkbox"
              checked={lowBandwidth}
              onChange={e => setLowBandwidth(e.target.checked)}
              style={{accentColor:'#f59e0b'}}
            />
            {rtl ? '🐢 وضع الاتصال البطيء (بدون تحليل AI)' : '🐢 Low bandwidth mode (skip AI analysis)'}
          </label>
        </div>

        {!apiReachable && (
          <div className="message error" style={{ marginTop: '0.75rem' }}>
            Backend API is unreachable. Check local backend startup or SSH tunnel/API port mapping, then retry.
          </div>
        )}

        {/* Offline banner */}
        {!isOnline && (
          <div className="offline-banner">
            <span>📵 You're offline.</span>
            {queuedCount > 0
              ? ` ${queuedCount} story${queuedCount > 1 ? 's' : ''} queued — will upload when reconnected.`
              : ' Stories will be saved locally and uploaded when you reconnect.'}
          </div>
        )}
        {isOnline && queuedCount > 0 && (
          <div className="offline-banner offline-banner--syncing">
            📶 {queuedCount} queued story{queuedCount > 1 ? 's' : ''} pending upload…
          </div>
        )}

        {/* AI Analysis Progress */}
        {isAnalyzing && (
          <div className="ai-analysis-banner">
            <div className="spinner"></div>
            <div className="text">
              <div>🤖 AI is analyzing your media...</div>
              {analysisSteps.length > 0 && (
                <div style={{fontSize: '0.85em', marginTop: 4, opacity: 0.9}}>
                  {analysisSteps.map((step, i) => (
                    <div key={i}>{i < analysisSteps.length - 1 ? '✓' : '⏳'} {step}</div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {analysisResult && !isAnalyzing && analysisResult.ai_used !== false && (
          <div className="ai-analysis-banner" style={{background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)'}}>
            <div className="icon">✨</div>
            <div className="text">
              <div>AI Analysis Complete! Confidence: {analysisResult.confidence ? (analysisResult.confidence * 100).toFixed(0) : '?'}%</div>
              {analysisResult.event_type && (
                <div style={{fontSize: '0.85em', marginTop: 2, opacity: 0.9}}>
                  Event type: {analysisResult.event_type}
                  {analysisResult.content_warnings && ` · ⚠️ ${analysisResult.content_warnings}`}
                </div>
              )}
            </div>
          </div>
        )}

        {analysisResult && !isAnalyzing && analysisResult.ai_used === false && (
          <div className="ai-analysis-banner" style={{background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)'}}>
            <div className="icon">⚠️</div>
            <div className="text">
              <div>AI service not configured</div>
              <div style={{fontSize: '0.85em', marginTop: 2, opacity: 0.9}}>
                Set <code>OPENAI_API_KEY</code> in your environment to enable AI-powered analysis.
                Fill in the fields manually for now.
              </div>
            </div>
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
              {/* Left Column: File Upload (Priority) */}
              <div className="form-column form-column-main">
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

                <div className={`form-details-reveal ${showDetails ? 'visible' : ''}`}>
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

                  {/* Source type + Witness statement */}
                  {showDetails && (
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
                        {rtl ? '⚠️ محتوى حساس — يتطلب مراجعة تحريرية قبل النشر' : '⚠️ Sensitive content — hold for editorial review before publishing'}
                      </label>
                    </div>
                  )}
                </div>
              </div>

              {/* Right Column: Location + AI Results */}
              <div className={`form-column form-column-side ${showDetails ? '' : 'hidden-section'}`}>
                <div className={`form-details-reveal ${showDetails ? 'visible' : ''}`}>
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

                  {/* EXIF Metadata Display */}
                  {exifData && exifData.has_gps && (
                    <div className="form-section" style={{background: 'rgba(16,185,129,0.08)', borderRadius: 8, padding: '10px 14px', marginTop: 8}}>
                      <h3 style={{fontSize: '0.9em', margin: '0 0 6px'}}>📷 Photo Metadata (EXIF)</h3>
                      <div style={{fontSize: '0.82em', lineHeight: 1.6}}>
                        <div>📍 GPS: {exifData.lat?.toFixed(5)}, {exifData.lon?.toFixed(5)}</div>
                        {exifData.timestamp && <div>🕐 Taken: {new Date(exifData.timestamp).toLocaleString()}</div>}
                        {exifData.device && <div>📱 Device: {exifData.device}</div>}
                      </div>
                    </div>
                  )}

                  {/* Transcription Display */}
                  {transcription && (
                    <div className="form-section" style={{marginTop: 8}}>
                      <h3 style={{fontSize: '0.9em', margin: '0 0 6px'}}>
                        🎙️ Audio Transcript {transcriptLanguage && `(${transcriptLanguage})`}
                      </h3>
                      <textarea
                        className="form-textarea"
                        value={transcription}
                        onChange={(e) => setTranscription(e.target.value)}
                        rows="4"
                        style={{fontSize: '0.85em'}}
                        placeholder="AI-generated transcript — edit if needed"
                      />
                    </div>
                  )}

                  {/* Messages (only when details are visible) */}
                  {showDetails && message && (
                    <div className={`message ${messageType}`}>
                      {message}
                    </div>
                  )}

                  {/* Confidence score preview */}
                  {analysisResult && analysisResult.confidence != null && !isAnalyzing && (
                    <div className="form-section" style={{padding:'10px 14px', marginTop:8}}>
                      <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:6}}>
                        <span style={{fontSize:'0.82rem', fontWeight:600}}>🎯 {rtl ? 'درجة المصداقية' : 'Credibility score'}</span>
                        <span style={{fontWeight:700, fontSize:'1rem', color: analysisResult.confidence > 0.6 ? '#10b981' : analysisResult.confidence > 0.35 ? '#f59e0b' : '#ef4444'}}>
                          {Math.round(analysisResult.confidence * 100)}%
                        </span>
                      </div>
                      <div style={{height:6, background:'rgba(255,255,255,0.1)', borderRadius:3, overflow:'hidden'}}>
                        <div style={{
                          height:'100%', borderRadius:3, transition:'width 0.4s',
                          width:`${Math.round(analysisResult.confidence * 100)}%`,
                          background: analysisResult.confidence > 0.6 ? '#10b981' : analysisResult.confidence > 0.35 ? '#f59e0b' : '#ef4444'
                        }}/>
                      </div>
                      <div style={{fontSize:'0.75rem', opacity:0.55, marginTop:4}}>
                        {rtl
                          ? 'تُحسَّن الدرجة بإضافة موقع وتفاصيل أكثر'
                          : 'Score improves with location, media, and more detail'}
                      </div>
                    </div>
                  )}

                  {/* Upload Progress Bar */}
                  {isLoading && (
                    <div className="upload-progress">
                      <div className="upload-progress-bar">
                        <div
                          className="upload-progress-fill"
                          style={{ width: `${uploadProgress}%` }}
                        />
                      </div>
                      <span className="upload-progress-text">{uploadProgress}%</span>
                    </div>
                  )}

                  {/* Form Actions */}
                  <div className="form-actions-side">
                    {!isLoggedIn && !authLoading && (
                      <div className="message error" style={{ marginBottom: '0.75rem' }}>
                        Session expired or not authenticated. Please log in to publish.
                      </div>
                    )}

                    {!isLoggedIn && !authLoading && (
                      <button
                        type="button"
                        className="submit-btn"
                        onClick={() => navigate('/login')}
                        style={{ marginBottom: '0.75rem' }}
                      >
                        Go to Login
                      </button>
                    )}

                    <button
                      type="submit"
                      className={`submit-btn ${isLoading ? 'loading' : ''}`}
                      disabled={isLoading || authLoading || !isLoggedIn}
                      title={!isLoggedIn ? 'Login required to publish' : 'Publish'}
                    >
                      {isLoading ? (
                        <>
                          <div className="spinner"></div>
                          {rtl ? AR.uploading : `Uploading... ${uploadProgress}%`}
                        </>
                      ) : (
                        <>
                          <span>🚀</span>
                          {rtl ? AR.publish : 'Publish'}
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </form>
        </div>

        {/* Message shown when no file selected (outside container) */}
        {!showDetails && message && (
          <div className={`message ${messageType}`} style={{marginTop: '1rem'}}>
            {message}
          </div>
        )}
      </div>
    </div>
  );
};

export default UploadForm;
