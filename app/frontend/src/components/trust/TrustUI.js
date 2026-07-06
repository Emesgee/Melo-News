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
          title="Automated estimate — secondary to human corroboration">
      confidence: {BAND_LABEL[band] || band}
    </span>
  );
};

// counted = distinct corroborating identities (the falsifiable signal);
// supporting = anonymous reports (context only) — shown SEPARATELY, never merged.
export const CorroborationCount = ({ counted = 0, supporting = 0 }) => (
  <>
    {counted > 0 && (
      <span style={{ ...PILL, background: '#dcfce7', color: '#14532d' }}
            title="Distinct corroborating identities (one actor's many keys count once)">
        ✓ {counted} corroborating
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

export const ReporterChip = ({ reporter }) => {
  if (!reporter) return null;
  if (reporter.is_anonymous) {
    return (
      <span style={{ ...PILL, background: '#e5e7eb', color: '#6b7280' }} title="No account attached — unverifiable">
        anonymous · unverifiable
      </span>
    );
  }
  const fresh = (reporter.rung ?? 1) <= 1;
  return (
    <>
      <span style={{ ...PILL, background: fresh ? '#e5e7eb' : '#374151', color: fresh ? '#6b7280' : '#fff' }}
            title={`Trust rung ${reporter.rung} · ${reporter.corroborated_count}/${reporter.reports_count} reports corroborated`}>
        {(reporter.handle || 'reporter')} · {fresh ? 'new reporter' : `rung ${reporter.rung}`}
      </span>
      {reporter.is_signed && (
        <span style={{ ...PILL, background: '#065f46', color: '#fff' }} title="Signed on device — tamper-evident">🔏 signed</span>
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
      {ev && <CorroborationCount counted={ev.corroboration_count} />}
      <ReporterChip reporter={data.reporter} />
      <ConfidenceBadge band={data.confidence_band} />
    </div>
  );
};
