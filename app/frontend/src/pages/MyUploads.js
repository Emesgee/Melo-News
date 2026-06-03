import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { GeneralInfoForm, LocationForm } from '../components/upload/UploadSubComponents';
import { getMyUploads, editUpload, deleteUpload } from '../services/api';
import { SEVERITY_CONFIG } from '../constants/severity';
import { useToast } from '../utils/ToastContext';
import { useAuth } from '../utils/AuthContext';
import './MyUploads.css';

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
  const { addToast } = useToast();
  const { user } = useAuth();
  const [uploads, setUploads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editTarget, setEditTarget] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const fetchUploads = useCallback(async () => {
    try {
      const res = await getMyUploads();
      setUploads(res.data);
    } catch (err) {
      addToast('Failed to load your reports.', 'error');
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  useEffect(() => { fetchUploads(); }, [fetchUploads]);

  const handleSave = async (id, data) => {
    const res = await editUpload(id, data);
    setUploads((prev) => prev.map((u) => (u.id === id ? res.data : u)));
    addToast('Report updated.', 'success');
  };

  const handleDelete = async (id) => {
    try {
      await deleteUpload(id);
      setUploads((prev) => prev.filter((u) => u.id !== id));
      addToast('Report deleted.', 'success');
    } catch {
      addToast('Delete failed. Try again.', 'error');
    } finally {
      setDeleteTarget(null);
    }
  };

  return (
    <div className="my-uploads-page">
      <section className="upload-header">
        <div className="upload-header-content">
          <h1>📰 Your reports</h1>
          {user && (
            <p className="reporter-standing">
              <strong>{user.display_handle || user.username || 'you'}</strong>
              {' · '}{user.identity_type === 'pseudonymous' ? 'pseudonymous' : 'registered'}
              {' · rung '}{user.trust_rung ?? 1}
              {' · '}{user.corroborated_count ?? 0}/{user.reports_count ?? 0} reports corroborated
            </p>
          )}
        </div>
      </section>

      <div className="my-uploads-content">
        {loading && <div className="uploads-loading">Loading your reports…</div>}

        {!loading && uploads.length === 0 && (
          <div className="uploads-empty">
            <p>You haven't reported anything yet.</p>
            <button className="btn-primary" onClick={() => navigate('/upload')}>Submit your first report</button>
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
    </div>
  );
};

export default MyUploads;
