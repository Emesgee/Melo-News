import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import Sidebar from '../components/navigationBars/Sidebar';
import { GeneralInfoForm, LocationForm } from '../components/upload/UploadSubComponents';
import { getMyUploads, editUpload, deleteUpload } from '../services/api';
import { SEVERITY_CONFIG } from '../constants/severity';
import { useToast } from '../utils/ToastContext';
import './MyUploads.css';

const STATUS_LABEL = {
  PENDING: { label: 'Pending', color: '#f59e0b' },
  PROCESSING: { label: 'Analyzing…', color: '#3b82f6' },
  COMPLETED: { label: 'Analyzed', color: '#10b981' },
  FAILED: { label: 'Failed', color: '#ef4444' },
};

/* ── Edit Modal ─────────────────────────────────────────────────────── */
const EditModal = ({ upload, onSave, onClose }) => {
  const [title, setTitle] = useState(upload.title || '');
  const [tags, setTags] = useState(upload.tags || '');
  const [subject, setSubject] = useState(upload.subject || '');
  const [city, setCity] = useState(upload.city || '');
  const [country, setCountry] = useState(upload.country || '');
  const [lat, setLat] = useState(upload.lat || null);
  const [lon, setLon] = useState(upload.lon || null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

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
            onUseMyLocation={() => {}}
            isLocating={false}
          />
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
  const [uploads, setUploads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editTarget, setEditTarget] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
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

  const handleSave = async (id, data) => {
    const res = await editUpload(id, data);
    setUploads((prev) => prev.map((u) => (u.id === id ? res.data : u)));
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
        <button className="btn-primary" onClick={() => navigate('/upload')}>+ New Story</button>
      </section>

      <div className="my-uploads-content">
        {loading && <div className="uploads-loading">Loading your stories…</div>}

        {!loading && uploads.length === 0 && (
          <div className="uploads-empty">
            <p>You haven't uploaded any stories yet.</p>
            <button className="btn-primary" onClick={() => navigate('/upload')}>Upload your first story</button>
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
