import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getEvents } from '../services/api';
import { useSearch } from '../utils/SearchContext';
import { EventStatusBadge, ConfidenceBadge, CorroborationCount } from '../components/trust/TrustUI';

// Public reader surface (List view): reports grouped into Events, the feed
// leading with CORROBORATED and keeping DISPUTED prominent (server-ordered).
// A card opens the shareable /events/:id detail page.

const wrap = { maxWidth: 760, margin: '0 auto', padding: '24px 16px' };
const h1 = { fontSize: 20, margin: '0 0 4px', color: 'var(--primary-color)' };
const muted = { color: 'var(--text-secondary)', fontSize: 13 };
const card = { border: '1px solid var(--border-color)', borderRadius: 'var(--radius-lg)', padding: 16, margin: '14px 0', background: 'var(--bg-primary)', cursor: 'pointer' };
const disputedCard = { borderColor: 'var(--status-disputed)', background: 'rgba(211, 47, 47, 0.08)' };
const title = { fontSize: 17, margin: '8px 0 4px', color: 'var(--text-primary)' };
const meta = { display: 'flex', gap: 14, flexWrap: 'wrap', fontSize: 13, color: 'var(--text-secondary)', margin: '4px 0' };
const disputeNote = { color: 'var(--status-disputed)', fontWeight: 600, fontSize: 13, margin: '6px 0' };
const openLink = { color: 'var(--primary-color)', fontSize: 13, fontWeight: 600 };

const EventsFeed = () => {
  const navigate = useNavigate();
  const { filter } = useSearch();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    (async () => {
      try {
        const res = await getEvents({ q: filter.q, status: filter.status, limit: 100 });
        if (alive) { setEvents(res.data?.events || []); setError(null); }
      } catch (e) {
        if (alive) setError('Could not load events.');
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, [filter.q, filter.status]);

  const open = (id) => navigate(`/events/${id}`);

  if (loading) return <div style={wrap}><p style={muted}>Loading events…</p></div>;
  if (error) return <div style={wrap}><h1 style={h1}>Events</h1><p style={muted}>{error}</p></div>;

  return (
    <div style={wrap}>
      <h1 style={h1}>Events</h1>
      <p style={muted}>
        Reports grouped into incidents. Corroboration counts <strong>independent sources</strong> — the same
        clip reposted under many accounts counts once, never a single source — and a confidence band is an
        automated estimate, secondary to that.
      </p>

      {events.length === 0 && (
        <p style={{ ...muted, marginTop: 20 }}>No corroborated or developing events yet.</p>
      )}

      {events.map((ev) => (
        <article
          key={ev.id}
          style={{ ...card, ...(ev.status === 'DISPUTED' ? disputedCard : {}) }}
          onClick={() => open(ev.id)}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(ev.id); } }}
        >
          <header style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
            <EventStatusBadge status={ev.status} />
            <CorroborationCount counted={ev.corroboration?.counted} independent={ev.corroboration?.independent} supporting={ev.corroboration?.supporting} status={ev.status} />
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

          <span style={openLink}>View reports →</span>
        </article>
      ))}
    </div>
  );
};

export default EventsFeed;
