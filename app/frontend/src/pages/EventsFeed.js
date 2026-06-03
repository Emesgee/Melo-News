import React, { useEffect, useState } from 'react';
import { getEvents, getEventDetail } from '../services/api';
import { EventStatusBadge, ConfidenceBadge, CorroborationCount, ReporterChip } from '../components/trust/TrustUI';

// Public reader surface: reports grouped into Events, the feed leading with
// CORROBORATED and keeping DISPUTED prominent (the server orders it). This is
// where a reader judges the *basis* of trust — the comprehension that the whole
// model exists to earn.

const wrap = { maxWidth: 760, margin: '0 auto', padding: '24px 16px' };
const h1 = { fontSize: 22, margin: '0 0 4px' };
const muted = { color: '#6b7280', fontSize: 13 };
const card = { border: '1px solid #e5e7eb', borderRadius: 10, padding: 16, margin: '14px 0', background: '#fff' };
const disputedCard = { borderColor: '#fecaca', background: '#fef2f2' };
const title = { fontSize: 17, margin: '8px 0 4px' };
const meta = { display: 'flex', gap: 14, flexWrap: 'wrap', fontSize: 13, color: '#6b7280', margin: '4px 0' };
const disputeNote = { color: '#b91c1c', fontWeight: 600, fontSize: 13, margin: '6px 0' };
const linkBtn = { background: 'none', border: 'none', color: '#2563eb', cursor: 'pointer', padding: '6px 0', fontSize: 13 };
const memberRow = { display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', padding: '6px 0', borderTop: '1px solid #f3f4f6' };

const EventsFeed = () => {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(null);
  const [detail, setDetail] = useState(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const res = await getEvents({ limit: 100 });
        if (alive) setEvents(res.data?.events || []);
      } catch (e) {
        if (alive) setError('Could not load events.');
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, []);

  const toggleDetail = async (id) => {
    if (expanded === id) { setExpanded(null); setDetail(null); return; }
    setExpanded(id);
    setDetail(null);
    try {
      const res = await getEventDetail(id);
      setDetail(res.data);
    } catch (e) {
      setDetail({ error: true });
    }
  };

  if (loading) return <div style={wrap}><p style={muted}>Loading events…</p></div>;
  if (error) return <div style={wrap}><h1 style={h1}>Events</h1><p style={muted}>{error}</p></div>;

  return (
    <div style={wrap}>
      <h1 style={h1}>Events</h1>
      <p style={muted}>
        Reports grouped into incidents. Corroboration counts <strong>distinct reporters</strong> — never a single source —
        and a confidence band is an automated estimate, secondary to that.
      </p>

      {events.length === 0 && (
        <p style={{ ...muted, marginTop: 20 }}>No corroborated or developing events yet.</p>
      )}

      {events.map((ev) => (
        <article key={ev.id} style={{ ...card, ...(ev.status === 'DISPUTED' ? disputedCard : {}) }}>
          <header style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
            <EventStatusBadge status={ev.status} />
            <CorroborationCount counted={ev.corroboration?.counted} supporting={ev.corroboration?.supporting} />
            <ConfidenceBadge band={ev.confidence_band} />
            {ev.is_overridden && <span style={muted} title="Status set by a moderator">moderator-set</span>}
          </header>

          <h2 style={title}>{ev.title || <em>Untitled incident</em>}</h2>

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

          <button style={linkBtn} onClick={() => toggleDetail(ev.id)}>
            {expanded === ev.id ? 'Hide reports' : `Show reports`}
          </button>

          {expanded === ev.id && detail && (
            <div style={{ marginTop: 8 }}>
              {detail.error ? (
                <p style={muted}>Could not load reports.</p>
              ) : (
                (detail.members || []).map((m) => (
                  <div key={m.id} style={memberRow}>
                    <ReporterChip reporter={m.provenance?.reporter} />
                    <span style={{ color: '#374151', fontSize: 14 }}>{m.body || m.title}</span>
                  </div>
                ))
              )}
            </div>
          )}
        </article>
      ))}
    </div>
  );
};

export default EventsFeed;
