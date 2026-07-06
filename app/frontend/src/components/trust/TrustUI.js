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
  return <span style={{ ...PILL, background: s.bg, color: '#fff' }} title="Event status">{s.label}</span>;
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
  // Lead with a plain-language standing, not the raw "rung N" jargon (ambiguous
  // scale) or the code-like handle first (which reads as a bot/spam serial number
  // — red-team finding). The pseudonym is kept, but as a SECONDARY, explained tag
  // so continuity survives without the code being the reporter's face. The rung
  // number and track record move to the tooltip.
  const fresh = (reporter.rung ?? 1) <= 1;
  const standing = fresh ? 'New reporter' : 'Established reporter';
  return (
    <>
      <span style={{ ...PILL, background: fresh ? '#e5e7eb' : '#374151', color: fresh ? '#6b7280' : '#fff' }}
            title={`Pseudonymous, identity protected · trust rung ${reporter.rung} · ${reporter.corroborated_count}/${reporter.reports_count} prior reports corroborated`}>
        {standing}
      </span>
      {reporter.handle && (
        <span style={{ ...PILL, background: 'transparent', color: 'var(--text-secondary)', border: '1px solid var(--border-color)', fontFamily: 'var(--font-mono, monospace)', fontWeight: 500 }}
              title="A stable pseudonym — lets you recognise the same reporter across reports without revealing who they are">
          {reporter.handle}
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
      <ConfidenceBadge band={data.confidence_band} />
    </div>
  );
};
