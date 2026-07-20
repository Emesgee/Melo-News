import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../utils/AuthContext';
import { useToast } from '../utils/ToastContext';
import {
  getModerationQueue,
  verifyUpload,
  rejectUpload,
  getIdentities,
  setUserRung,
  setUserRole,
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

const EVENT_TINT = { CORROBORATED: '#15803d', DISPUTED: '#b91c1c', DEVELOPING: '#a16207', CLOSED: '#4b5563' };
const EVENT_LABEL = { CORROBORATED: 'Corroborated', DISPUTED: 'Disputed', DEVELOPING: 'Developing', CLOSED: 'Closed' };

const ReviewCard = ({ story, onVerify, onReject, busy }) => {
  const loc = story.location || {};
  const sev = story.metrics?.severity || 'LOW';
  const verifStatus = story.workflow?.verification_status || 'PENDING';
  const verifNote = story.workflow?.verification_note;
  const reporter = story.provenance?.reporter || {};
  const isAnonymous = reporter.is_anonymous;
  const ev = story.event;
  const sourceLabel = story.provenance?.source_label || story.provenance?.source_name || 'upload';

  return (
    <article style={cardStyle}>
      <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
        <div style={{ ...statusDot, background: STATUS_TINT[verifStatus] || '#888' }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <header style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', marginBottom: 6 }}>
            <strong style={{ fontSize: 16 }}>{story.title || <em>Untitled</em>}</strong>
            <span style={{ ...pill, background: SEVERITY_TINT[sev], color: '#fff' }}>{sev}</span>
            <span style={{ ...pill, background: '#374151', color: '#fff' }}>{sourceLabel}</span>
            {ev && (
              <span style={{ ...pill, background: EVENT_TINT[ev.status] || '#a16207', color: '#fff' }} title="Event status">
                {EVENT_LABEL[ev.status] || ev.status}
              </span>
            )}
            {ev && ev.corroboration_count > 0 && (
              <span style={{ ...pill, background: '#dcfce7', color: '#14532d' }} title="Distinct corroborating identities">
                ✓ {ev.corroboration_count}
              </span>
            )}
            {isAnonymous ? (
              <span style={{ ...pill, background: '#e5e7eb', color: '#6b7280' }} title="No account attached — unverifiable">anonymous</span>
            ) : (
              <span style={{ ...pill, background: reporter.rung <= 1 ? '#e5e7eb' : '#374151', color: reporter.rung <= 1 ? '#6b7280' : '#fff' }}
                    title={`rung ${reporter.rung} · ${reporter.corroborated_count}/${reporter.reports_count} corroborated`}>
                {(reporter.handle || 'reporter')} · {reporter.rung <= 1 ? 'new' : `rung ${reporter.rung}`}
              </span>
            )}
            {reporter.is_signed && (
              <span style={{ ...pill, background: '#065f46', color: '#fff' }} title="Signed on device — tamper-evident">🔏</span>
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
            {story.metrics?.confidence_band && (
              <span title="Automated estimate — secondary to corroboration">🎯 {story.metrics.confidence_band}</span>
            )}
          </div>

          {(() => {
            // Use the server-bucketed images/videos (serialize_upload), NOT a
            // client-side extension regex: presigned S3 URLs carry query params,
            // so a "$"-anchored extension test misclassifies and hid mp4s behind
            // a bare link. Videos now play inline for review.
            const imgs = story.media?.images || [];
            const vids = story.media?.videos || [];
            if (!imgs.length && !vids.length) return null;
            return (
              <div style={{ marginTop: 10, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {imgs.map((src, k) => (
                  <img key={`i${k}`} src={src} alt="" loading="lazy"
                       style={{ width: 300, maxWidth: '100%', maxHeight: 220, borderRadius: 6, objectFit: 'cover', border: '1px solid var(--border-color)' }} />
                ))}
                {vids.map((src, k) => (
                  <video key={`v${k}`} src={src} controls preload="metadata"
                         style={{ width: 300, maxWidth: '100%', maxHeight: 220, borderRadius: 6, background: '#000', border: '1px solid var(--border-color)' }} />
                ))}
              </div>
            );
          })()}

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

// Steward-only governance panel: set trust rungs and editorial roles.
//
// Why this matters operationally: an Event cannot auto-reach CORROBORATED
// without at least one rung-2+ member (ADR-0005 Sybil backstop), so vouching a
// reporter is what lets a cohort's reports actually corroborate (ADR-0016).
// Rung 1 reports are pre-moderated; rung 2+ auto-publish, subject to the safety
// override — so a promotion is a real editorial decision, not a formality.
const StewardPanel = ({ addToast }) => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState('');
  const [open, setOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const resp = await getIdentities();
      setUsers(resp.data?.users || []);
    } catch (err) {
      setError(err.response?.data?.error || 'Could not load identities.');
      setUsers([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { if (open) load(); }, [open, load]);

  const applyRung = async (u, rung) => {
    setBusyId(u.userid);
    try {
      await setUserRung(u.userid, rung);
      addToast(`${u.handle || u.username || `#${u.userid}`} → rung ${rung}`, 'success');
      await load();
    } catch (err) {
      addToast(err.response?.data?.error || 'Could not set rung.', 'error');
    } finally {
      setBusyId(null);
    }
  };

  const applyRole = async (u, role) => {
    setBusyId(u.userid);
    try {
      await setUserRole(u.userid, role);
      addToast(`${u.handle || u.username || `#${u.userid}`} → ${role}`, 'success');
      await load();
    } catch (err) {
      addToast(err.response?.data?.error || 'Could not set role.', 'error');
    } finally {
      setBusyId(null);
    }
  };

  const cell = { padding: '6px 8px', borderBottom: '1px solid #e5e7eb', fontSize: 13 };
  const chip = { padding: '2px 7px', borderRadius: 999, fontSize: 11, fontWeight: 600 };

  return (
    <section style={{ border: '1px solid #e5e7eb', borderRadius: 8, marginBottom: 20 }}>
      <button
        onClick={() => setOpen((v) => !v)}
        style={{
          width: '100%', textAlign: 'left', padding: '10px 12px', border: 'none',
          background: '#f9fafb', cursor: 'pointer', fontWeight: 600, fontSize: 14,
          borderRadius: 8,
        }}
      >
        {open ? '▾' : '▸'} Steward · identities &amp; trust rungs
      </button>

      {open && (
        <div style={{ padding: 12, overflowX: 'auto' }}>
          {loading && <div style={{ color: '#6b7280' }}>Loading…</div>}
          {error && <div style={{ color: '#b91c1c' }}>{error}</div>}

          {!loading && !error && (
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 620 }}>
              <thead>
                <tr style={{ textAlign: 'left', color: '#6b7280', fontSize: 12 }}>
                  <th style={cell}>Identity</th>
                  <th style={cell}>Track record</th>
                  <th style={cell}>Rung</th>
                  <th style={cell}>Role</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.userid} style={{ opacity: busyId === u.userid ? 0.5 : 1 }}>
                    <td style={cell}>
                      <div style={{ fontWeight: 600 }}>
                        {u.handle || u.username || `#${u.userid}`}
                      </div>
                      <div style={{ color: '#6b7280', fontSize: 11 }}>
                        #{u.userid} · {u.identity_type}
                      </div>
                    </td>
                    <td style={cell}>
                      <span style={{ ...chip, background: '#f3f4f6', color: '#374151' }}>
                        {u.corroborated_count} of {u.reports_count} corroborated
                      </span>
                    </td>
                    <td style={cell}>
                      {[1, 2, 3].map((r) => (
                        <button
                          key={r}
                          disabled={busyId === u.userid || u.trust_rung === r}
                          onClick={() => applyRung(u, r)}
                          title={
                            r === 1 ? 'Rung 1 — reports are pre-moderated'
                              : r === 2 ? 'Rung 2 — auto-publish, and can carry an Event to CORROBORATED'
                                : 'Rung 3 — established'
                          }
                          style={{
                            marginRight: 4, padding: '3px 9px', borderRadius: 4, fontSize: 12,
                            cursor: u.trust_rung === r ? 'default' : 'pointer',
                            border: '1px solid ' + (u.trust_rung === r ? '#111827' : '#d1d5db'),
                            background: u.trust_rung === r ? '#111827' : '#fff',
                            color: u.trust_rung === r ? '#fff' : '#374151',
                          }}
                        >
                          {r}
                        </button>
                      ))}
                    </td>
                    <td style={cell}>
                      <select
                        value={u.role}
                        disabled={busyId === u.userid}
                        onChange={(e) => applyRole(u, e.target.value)}
                        style={{ fontSize: 12, padding: '3px 6px' }}
                      >
                        <option value="reporter">reporter</option>
                        <option value="moderator">moderator</option>
                        <option value="steward">steward</option>
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <p style={{ color: '#6b7280', fontSize: 12, marginTop: 10, marginBottom: 0 }}>
            Rung 1 reports are held for review; rung 2+ auto-publish unless the safety
            override applies (HIGH severity, sensitive, or first media on a new event).
            An Event needs a rung-2+ member before it can reach CORROBORATED.
          </p>
        </div>
      )}
    </section>
  );
};

const Moderation = () => {
  const navigate = useNavigate();
  const { isLoggedIn, isModerator, authLoading, user } = useAuth();
  const { addToast } = useToast();
  const isSteward = user?.role === 'steward';

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

      {isSteward && <StewardPanel addToast={addToast} />}

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
