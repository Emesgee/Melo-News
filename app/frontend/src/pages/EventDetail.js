import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getEventDetail } from '../services/api';
import { EventStatusBadge, ConfidenceBadge, CorroborationCount, ReporterChip } from '../components/trust/TrustUI';

// Shareable, deep-linkable detail for one Event — the trust artifact a reader
// can send to someone else. Opened from a map pin or a List card.

const wrap = { maxWidth: 720, margin: '0 auto', padding: '24px 16px' };
const back = { display: 'inline-block', color: '#2563eb', textDecoration: 'none', fontSize: 14, marginBottom: 12 };
const muted = { color: '#6b7280', fontSize: 13 };
const card = { border: '1px solid #e5e7eb', borderRadius: 10, padding: 18, background: '#fff' };
const disputed = { borderColor: '#fecaca', background: '#fef2f2' };
const row = { display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' };
const title = { fontSize: 20, margin: '10px 0 4px' };
const meta = { display: 'flex', gap: 14, flexWrap: 'wrap', fontSize: 13, color: '#6b7280', margin: '4px 0 8px' };
const disputeNote = { color: '#b91c1c', fontWeight: 600, fontSize: 13, margin: '6px 0' };
const h2 = { fontSize: 14, color: '#374151', margin: '16px 0 4px' };
const memberRow = { display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', padding: '8px 0', borderTop: '1px solid #f3f4f6' };

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
          <CorroborationCount counted={ev.corroboration?.counted} supporting={ev.corroboration?.supporting} />
          <ConfidenceBadge band={ev.confidence_band} />
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
        {(ev.members || []).map((m) => (
          <div key={m.id} style={memberRow}>
            <ReporterChip reporter={m.provenance?.reporter} />
            <span style={{ color: '#374151', fontSize: 14 }}>{m.body || m.title}</span>
          </div>
        ))}
        {(!ev.members || ev.members.length === 0) && (
          <p style={muted}>No published reports yet.</p>
        )}
      </article>
    </div>
  );
};

export default EventDetail;
