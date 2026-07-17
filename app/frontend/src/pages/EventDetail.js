import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getEventDetail } from '../services/api';
import { EventStatusBadge, CorroborationCount, ReporterChip } from '../components/trust/TrustUI';

// Shareable, deep-linkable detail for one Event — the trust artifact a reader
// can send to someone else. Opened from a map pin or a List card.

const wrap = { maxWidth: 720, margin: '0 auto', padding: '24px 16px' };
const back = { display: 'inline-block', color: 'var(--primary-color)', textDecoration: 'none', fontSize: 14, marginBottom: 12 };
const muted = { color: 'var(--text-secondary)', fontSize: 13 };
const card = { border: '1px solid var(--border-color)', borderRadius: 'var(--radius-lg)', padding: 18, background: 'var(--bg-primary)' };
const disputed = { borderColor: 'var(--status-disputed)', background: 'rgba(211, 47, 47, 0.08)' };
const row = { display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' };
const title = { fontSize: 20, margin: '10px 0 4px', color: 'var(--text-primary)' };
const meta = { display: 'flex', gap: 14, flexWrap: 'wrap', fontSize: 13, color: 'var(--text-secondary)', margin: '4px 0 8px' };
const disputeNote = { color: 'var(--status-disputed)', fontWeight: 600, fontSize: 13, margin: '6px 0' };
const h2 = { fontSize: 14, color: 'var(--text-secondary)', margin: '16px 0 4px' };
const memberRow = { display: 'flex', flexDirection: 'column', gap: 6, padding: '10px 0', borderTop: '1px solid var(--border-color)' };
const mediaWrap = { display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 2 };
const mediaEl = { width: 320, maxWidth: '100%', maxHeight: 240, objectFit: 'cover', borderRadius: 'var(--radius-sm, 4px)', border: '1px solid var(--border-color)', background: '#000' };

// Arrival time of a report relative to the first in the event — shows the event
// developing (chronology, NOT a trust signal). Based on the reporter's
// self-declared, signed published_at, so it's narrative, not proof.
const arrivalLabel = (ts, firstTs) => {
  if (!ts || !firstTs) return null;
  const secs = (new Date(ts) - new Date(firstTs)) / 1000;
  if (!Number.isFinite(secs) || secs <= 0) return 'earliest';
  const mins = Math.round(secs / 60);
  if (mins < 60) return `+${Math.max(1, mins)} min`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `+${hrs} h`;
  return `+${Math.round(hrs / 24)} d`;
};

const EventDetail = () => {
  const { id } = useParams();
  const [ev, setEv] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(false);
    (async () => {
      try {
        const res = await getEventDetail(id);
        if (alive) setEv(res.data);
      } catch (e) {
        if (alive) setError(true);
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, [id]);

  if (loading) return <div style={wrap}><p style={muted}>Loading…</p></div>;
  if (error || !ev) {
    return (
      <div style={wrap}>
        <Link to="/events" style={back}>← All events</Link>
        <p style={muted}>This event could not be found.</p>
      </div>
    );
  }

  return (
    <div style={wrap}>
      <Link to="/events" style={back}>← All events</Link>
      <article style={{ ...card, ...(ev.status === 'DISPUTED' ? disputed : {}) }}>
        <header style={row}>
          <EventStatusBadge status={ev.status} />
          <CorroborationCount counted={ev.corroboration?.counted} independent={ev.corroboration?.independent} supporting={ev.corroboration?.supporting} status={ev.status} />
          {ev.is_overridden && <span style={muted} title="Status set by a moderator">moderator-set</span>}
        </header>

        <h1 style={title}>{ev.title || <em>Untitled incident</em>}</h1>

        <div style={meta}>
          {ev.location?.city && (
            <span>📍 {ev.location.city}{ev.location.country ? `, ${ev.location.country}` : ''}</span>
          )}
          <span>{ev.member_count} report{ev.member_count === 1 ? '' : 's'}</span>
          {ev.severity && <span>severity: {ev.severity}</span>}
        </div>

        {ev.status === 'DISPUTED' && (
          <p style={disputeNote}>⚠ Accounts of this event conflict — treat with caution.</p>
        )}

        <h2 style={h2}>Reports</h2>
        {(ev.members || []).map((m, i, arr) => {
          const label = arrivalLabel(m.timestamps?.published_at, arr[0]?.timestamps?.published_at);
          return (
            <div key={m.id} style={memberRow}>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                <ReporterChip reporter={m.provenance?.reporter} />
                {label && (
                  <span style={{ color: 'var(--text-secondary)', fontSize: 12 }}
                        title="Time each report arrived, relative to the first — uses the reporter's self-declared, signed time">
                    {label}
                  </span>
                )}
              </div>
              <span style={{ color: 'var(--text-primary)', fontSize: 14 }}>{m.body || m.title}</span>
              {(() => {
                const imgs = m.media?.images || [];
                const vids = m.media?.videos || [];
                if (!imgs.length && !vids.length) return null;
                return (
                  <div style={mediaWrap}>
                    {imgs.map((src, k) => (
                      <img key={`i${k}`} src={src} alt={m.title || 'report media'} loading="lazy" style={mediaEl} />
                    ))}
                    {vids.map((src, k) => (
                      // controls + metadata preload; the presigned S3 URL is short-lived and refreshed each fetch
                      <video key={`v${k}`} src={src} controls preload="metadata" style={mediaEl} />
                    ))}
                  </div>
                );
              })()}
            </div>
          );
        })}
        {(!ev.members || ev.members.length === 0) && (
          <p style={muted}>No published reports yet.</p>
        )}
      </article>
    </div>
  );
};

export default EventDetail;
