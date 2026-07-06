import React from 'react';

// Shared reader-facing trust atoms (Stage E). Show the *basis* of trust, never
// a binary "verified": event status, concrete corroboration (distinct vs
// anonymous, shown separately), reporter standing, signature tamper-evidence,
// and a confidence BAND labelled as an automated estimate.

const PILL = {
  padding: '2px 8px', borderRadius: 999, fontSize: 11, fontWeight: 600,
  whiteSpace: 'nowrap', display: 'inline-block',
};

const EVENT_STATUS = {
  CORROBORATED: { bg: 'var(--status-corroborated)', label: 'Corroborated' },
  DISPUTED:     { bg: 'var(--status-disputed)', label: 'Disputed' },
  DEVELOPING:   { bg: 'var(--status-developing)', label: 'Developing' },
  CLOSED:       { bg: 'var(--status-closed)', label: 'Closed' },
};
const BAND_LABEL = { LOW: 'Low', MEDIUM: 'Medium', HIGH: 'High' };

export const EventStatusBadge = ({ status }) => {
  const s = EVENT_STATUS[status] || EVENT_STATUS.DEVELOPING;
  // DISPUTED carries a leading ⚠ so the warning is a PRESENT, loud signal, not
  // merely the absence of a corroboration ✓ (a skimmer misses what isn't there —
  // red-team finding).
  const label = status === 'DISPUTED' ? `⚠ ${s.label}` : s.label;
  return <span style={{ ...PILL, background: s.bg, color: '#fff' }} title="Event status">{label}</span>;
};

export const ConfidenceBadge = ({ band }) => {
  if (!band) return null;
  return (
    <span style={{ ...PILL, background: 'var(--bg-secondary)', color: 'var(--text-secondary)', border: '1px solid var(--border-color)' }}
          title="An automated estimate of report quality — secondary to, and weaker than, human corroboration">
      auto-estimate: {BAND_LABEL[band] || band}
    </span>
  );
};

// Leads with INDEPENDENT sources: reshares of the same media (one clip reposted
// under many keys) collapse to a single origin, so this is the falsifiable
// number (ADR-0019/UC8), not the raw account count. When more accounts posted
// than there are independent sources, the gap is surfaced honestly — a detected
// reshare — rather than hidden. supporting = anonymous reports (context only),
// always shown separately. `independent` falls back to `counted` for older
// payloads that don't carry it.
export const CorroborationCount = ({ counted = 0, independent = null, supporting = 0, status = null }) => {
  const ind = independent == null ? counted : independent;
  const reshared = Math.max(0, (counted || 0) - ind);
  // On a DISPUTED event the sources CONFLICT — so the count must not wear the
  // affirmative green ✓, which a skimmer reads as "verified/good" and which then
  // cancels the dispute warning (red-team finding). Show the same number in a
  // neutral tone, explicitly not an endorsement.
  const disputed = status === 'DISPUTED';
  return (
    <>
      {ind > 0 && (
        <span style={disputed
                ? { ...PILL, background: 'var(--bg-secondary)', color: 'var(--text-secondary)', border: '1px solid var(--border-color)' }
                : { ...PILL, background: '#dcfce7', color: '#14532d' }}
              title={disputed
                ? 'Independent sources whose accounts conflict — a count, not an endorsement'
                : "Independent sources — reshares of the same media count once, one actor's many keys count once"}>
          {disputed ? '' : '✓ '}{ind} independent source{ind === 1 ? '' : 's'}
        </span>
      )}
      {reshared > 0 && (
        <span style={{ ...PILL, background: '#fef3c7', color: '#92400e' }}
              title={`${counted} accounts posted, but ${reshared} reposted the same media — counted once, not as independent corroboration`}>
          ⤿ {counted} accounts · {reshared} reshared
        </span>
      )}
      {supporting > 0 && (
        <span style={{ ...PILL, background: '#e5e7eb', color: '#6b7280' }}
              title="Anonymous reports — supporting context, not counted toward corroboration">
          +{supporting} anonymous
        </span>
      )}
    </>
  );
};

export const ReporterChip = ({ reporter }) => {
  if (!reporter) return null;
  if (reporter.is_anonymous) {
    return (
      <span style={{ ...PILL, background: '#e5e7eb', color: '#6b7280' }} title="No account attached — unverifiable">
        anonymous · unverifiable
      </span>
    );
  }
  // Put the EARNED, falsifiable fact on the visible face — "N of M reports
  // corroborated" — not a conferred authority word. ("Established reporter" read
  // as an unearned masthead-style claim; its justification was tooltip-only, i.e.
  // invisible on mobile — round-2 red-team finding.) The raw k-xxxx code moves
  // OFF the face (it reads as a bot serial number) into the tooltip, where it
  // still supports recognising a repeat reporter. New reporters say so plainly.
  const corr = reporter.corroborated_count ?? 0;
  const total = reporter.reports_count ?? 0;
  const idNote = `Pseudonymous, identity protected${reporter.handle ? ` — ${reporter.handle}` : ''}`;
  return (
    <>
      {total > 0 ? (
        <span style={{ ...PILL, background: '#374151', color: '#fff' }}
              title={`${idNote} · trust rung ${reporter.rung}`}>
          {corr} of {total} report{total === 1 ? '' : 's'} corroborated
        </span>
      ) : (
        <span style={{ ...PILL, background: '#e5e7eb', color: '#6b7280' }}
              title={`${idNote} · no reports corroborated yet`}>
          New reporter · no track record yet
        </span>
      )}
      {reporter.is_signed && (
        <span style={{ ...PILL, background: '#065f46', color: '#fff' }}
              title="Cryptographically signed on the reporter's device — proves the report is really theirs and untampered. Not an endorsement by Melo.">
          🔏 signed
        </span>
      )}
    </>
  );
};

// Report-level trust block (map popup / report views). `data` is a serialized
// Story: { event: {status, corroboration_count}, reporter, confidence_band }.
export const TrustBlock = ({ data }) => {
  if (!data) return null;
  const ev = data.event;
  return (
    <div className="popup-trust" style={{ display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'center', margin: '8px 0' }}>
      {ev && <EventStatusBadge status={ev.status} />}
      {ev && <CorroborationCount counted={ev.corroboration_count} status={ev.status} />}
      <ReporterChip reporter={data.reporter} />
    </div>
  );
};
