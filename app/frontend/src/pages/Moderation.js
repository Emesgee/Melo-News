import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../utils/AuthContext';
import { useToast } from '../utils/ToastContext';
import { useSearch } from '../utils/SearchContext';
import {
  getModerationQueue,
  verifyUpload,
  rejectUpload,
} from '../services/api';

const STATUSES = ['PENDING', 'VERIFIED', 'REJECTED'];

const STATUS_TINT = {
  PENDING: '#f59e0b',
  VERIFIED: '#10b981',
  REJECTED: '#ef4444',
};

const SEVERITY_TINT = {
  HIGH: '#ef4444',
  MEDIUM: '#f59e0b',
  LOW: '#3b82f6',
};

const fmtDate = (iso) =>
  iso
    ? new Date(iso).toLocaleString(undefined, {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : '—';

const ReviewCard = ({ story, onVerify, onReject, busy }) => {
  const loc = story.location || {};
  const sev = story.metrics?.severity || 'LOW';
  const verifStatus = story.workflow?.verification_status || 'PENDING';
  const verifNote = story.workflow?.verification_note;
  const author = story.provenance?.author_user_id;
  const sourceLabel = story.provenance?.source_label || story.provenance?.source_name || 'upload';
  const media = story.media?.primary_url;
  const isImage = media && /\.(jpg|jpeg|png|webp|gif)$/i.test(media);

  return (
    <article style={cardStyle}>
      <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
        <div style={{ ...statusDot, background: STATUS_TINT[verifStatus] || '#888' }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <header style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', marginBottom: 6 }}>
            <strong style={{ fontSize: 16 }}>{story.title || <em>Untitled</em>}</strong>
            <span style={{ ...pill, background: SEVERITY_TINT[sev], color: '#fff' }}>{sev}</span>
            <span style={{ ...pill, background: '#374151', color: '#fff' }}>{sourceLabel}</span>
            {author === null && (
              <span style={{ ...pill, background: '#0ea5e9', color: '#fff' }} title="No account attached">anonymous</span>
            )}
            <span style={{ ...pill, background: '#e5e7eb', color: '#111' }}>{verifStatus}</span>
          </header>

          {story.body && (
            <p style={{ margin: '6px 0', color: '#374151', whiteSpace: 'pre-wrap' }}>
              {story.body}
            </p>
          )}

          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 13, color: '#6b7280' }}>
            {loc.label && <span>📍 {loc.label}</span>}
            {loc.lat != null && loc.lon != null && (
              <span>{loc.lat.toFixed?.(3) ?? loc.lat}, {loc.lon.toFixed?.(3) ?? loc.lon}</span>
            )}
            <span>{fmtDate(story.timestamps?.published_at)}</span>
            {story.metrics?.confidence_score != null && (
              <span>🎯 {Math.round(story.metrics.confidence_score * 100)}%</span>
            )}
          </div>

          {media && (
            <div style={{ marginTop: 10 }}>
              {isImage ? (
                <img
                  src={media}
                  alt=""
                  style={{ maxWidth: '100%', maxHeight: 220, borderRadius: 6, objectFit: 'cover' }}
                />
              ) : (
                <a href={media} target="_blank" rel="noreferrer">View attached media</a>
              )}
            </div>
          )}

          {verifNote && verifStatus !== 'PENDING' && (
            <div style={noteBox}>
              <strong style={{ fontSize: 12, color: '#374151' }}>Moderator note</strong>
              <div style={{ fontSize: 13 }}>{verifNote}</div>
            </div>
          )}

          {verifStatus === 'PENDING' && (
            <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
              <button
                style={{ ...btn, background: '#10b981', color: '#fff' }}
                onClick={() => onVerify(story)}
                disabled={busy}
              >
                ✓ Approve
              </button>
              <button
                style={{ ...btn, background: '#ef4444', color: '#fff' }}
                onClick={() => onReject(story)}
                disabled={busy}
              >
                ✗ Reject
              </button>
            </div>
          )}
        </div>
      </div>
    </article>
  );
};

const Moderation = () => {
  const navigate = useNavigate();
  const { isLoggedIn, isModerator, authLoading } = useAuth();
  const { addToast } = useToast();
  const { clearResults } = useSearch() || {};

  const [status, setStatus] = useState('PENDING');
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState('');

  const load = useCallback(async (which) => {
    setLoading(true);
    setError('');
    try {
      const resp = await getModerationQueue(which);
      setItems(resp.data?.items || []);
      setTotal(resp.data?.paging?.total ?? (resp.data?.items?.length || 0));
    } catch (err) {
      if (err.response?.status === 403) {
        setError('You do not have moderator access.');
      } else {
        setError(err.response?.data?.error || 'Could not load queue.');
      }
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authLoading) return;
    if (!isLoggedIn) {
      navigate('/login');
      return;
    }
    load(status);
  }, [authLoading, isLoggedIn, status, navigate, load]);

  const handleVerify = async (story) => {
    setBusyId(story.source_record_id);
    try {
      await verifyUpload(story.source_record_id);
      addToast('Story approved and now visible on the public feed.', 'success');
      setItems((prev) => prev.filter((s) => s.source_record_id !== story.source_record_id));
      clearResults?.();
    } catch (err) {
      addToast(err.response?.data?.error || 'Approve failed.', 'error');
    } finally {
      setBusyId(null);
    }
  };

  const handleReject = async (story) => {
    const note = window.prompt('Reason for rejection (required — shown to the reporter):');
    if (!note || !note.trim()) return;
    setBusyId(story.source_record_id);
    try {
      await rejectUpload(story.source_record_id, note.trim());
      addToast('Story rejected.', 'success');
      setItems((prev) => prev.filter((s) => s.source_record_id !== story.source_record_id));
    } catch (err) {
      addToast(err.response?.data?.error || 'Reject failed.', 'error');
    } finally {
      setBusyId(null);
    }
  };

  if (authLoading) return null;

  if (!isModerator) {
    return (
      <div style={pageStyle}>
        <h1>Moderation</h1>
        <p style={{ color: '#6b7280' }}>
          This area is reserved for editorial moderators. Your account does not have the
          moderator role.
        </p>
      </div>
    );
  }

  return (
    <div style={pageStyle}>
      <header style={{ display: 'flex', alignItems: 'baseline', gap: 12, marginBottom: 16 }}>
        <h1 style={{ margin: 0 }}>Moderation queue</h1>
        <span style={{ color: '#6b7280', fontSize: 14 }}>
          {items.length} shown {total > items.length ? `of ${total}` : ''}
        </span>
      </header>

      <div style={tabRow}>
        {STATUSES.map((s) => (
          <button
            key={s}
            onClick={() => setStatus(s)}
            style={{
              ...tab,
              background: status === s ? '#111827' : '#f3f4f6',
              color: status === s ? '#fff' : '#111827',
            }}
          >
            {s}
          </button>
        ))}
      </div>

      {loading && <div style={{ padding: 24, color: '#6b7280' }}>Loading…</div>}
      {!loading && error && <div style={errorBox}>{error}</div>}
      {!loading && !error && items.length === 0 && (
        <div style={{ padding: 24, color: '#6b7280' }}>
          No <code>{status}</code> submissions right now.
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {items.map((story) => (
          <ReviewCard
            key={`${story.source_type}-${story.source_record_id}`}
            story={story}
            onVerify={handleVerify}
            onReject={handleReject}
            busy={busyId === story.source_record_id}
          />
        ))}
      </div>
    </div>
  );
};

const pageStyle = {
  maxWidth: 880,
  margin: '0 auto',
  padding: '24px 16px 80px',
};

const tabRow = {
  display: 'flex',
  gap: 8,
  marginBottom: 16,
};

const tab = {
  padding: '6px 14px',
  borderRadius: 999,
  border: '1px solid #e5e7eb',
  cursor: 'pointer',
  fontSize: 13,
};

const cardStyle = {
  background: '#fff',
  border: '1px solid #e5e7eb',
  borderRadius: 8,
  padding: 16,
  boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
};

const statusDot = {
  width: 10,
  height: 10,
  borderRadius: '50%',
  marginTop: 8,
  flexShrink: 0,
};

const pill = {
  display: 'inline-block',
  padding: '2px 8px',
  borderRadius: 999,
  fontSize: 11,
  letterSpacing: 0.5,
  textTransform: 'uppercase',
  fontWeight: 600,
};

const btn = {
  padding: '8px 14px',
  borderRadius: 6,
  border: 'none',
  cursor: 'pointer',
  fontWeight: 600,
};

const noteBox = {
  marginTop: 10,
  padding: '8px 10px',
  background: '#f9fafb',
  border: '1px solid #e5e7eb',
  borderRadius: 6,
};

const errorBox = {
  padding: 16,
  background: '#fef2f2',
  color: '#991b1b',
  border: '1px solid #fecaca',
  borderRadius: 6,
};

export default Moderation;
