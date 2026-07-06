"""
app/events/archive.py

The corroboration graph -- an explicit, deterministic, privacy-preserving
representation of an Event and the provenance relationships between its sources
(ADR-0020 Phase 1, the archive-grade core).

Where serialize_event is a reader view, this is the ARCHIVE view: the structure
you would hand to a court, a researcher, or an accountability partner (Mnemonic/
eyeWitness, UC9). It captures, per verified source, its pseudonymous identity,
provenance tier, media fingerprint, and independence role (independent origin vs
reshare of a shared fingerprint), plus the reshare clusters that are the graph's
non-trivial relational structure. It is:

  * deterministic  -- stable key + node order, so two builds of the same state
                      are byte-identical (canonical JSON, ADR-0014 style);
  * hashable       -- a content hash over the whole graph (integrity / the seed
                      of capture-before-deletion preservation, UC9);
  * privacy-preserving -- never emits raw user_id (deanonymization, ADR-0007).

Pure functions only: no request context, no commit. That keeps the graph usable
from a reader endpoint, an export job, or a future snapshot writer alike.
"""

import hashlib
import json
from collections import Counter
from datetime import timezone

from app.story.serializers import serialize_reporter, confidence_band
from app.events.independence import analyze_independence

# Bump when the emitted shape changes in a way a stored/exported graph must be
# able to distinguish (durability: an old archived graph declares its version).
GRAPH_SCHEMA_VERSION = 1


def _provenance_tier(upload):
    """The source's trust tier. A signed on-device report is tamper-evident
    (ADR-0019 Lane B, the 'verified' premium tier); the unsigned web/anon lane
    is 'unverified'. ('public' will join this enum when Lane A public-post
    ingest lands in the Phase 2 branch.)"""
    return 'verified' if getattr(upload, 'report_signature', None) else 'unverified'


def _iso(dt):
    """Canonical UTC-naive ISO string. Coercing to a single representation is
    what makes the content hash stable: the ORM hands us tz-aware datetimes on
    a fresh write but tz-naive ones after a DB round-trip, and an unnormalized
    mix would change the hash for no substantive reason."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.isoformat()


def _node(upload, fp_counts):
    """One source node. `fp_counts` is a Counter of media fingerprints across the
    event's verified members, used to classify independence."""
    fp = (upload.media_sha256 or '').strip().lower() or None
    if upload.user_id is None:
        # Anonymous members are supporting context, never a counted origin
        # (mirrors recompute_event / serialize_event).
        independence = 'supporting'
    elif fp and fp_counts[fp] > 1:
        independence = 'reshare'      # same bytes under >1 identity -> not independent
    else:
        independence = 'independent'
    return {
        'source_id': upload.id,
        'reporter': serialize_reporter(upload),
        'provenance_tier': _provenance_tier(upload),
        'media_fingerprint': fp,
        'independence': independence,
        'verification_status': upload.verification_status,
        'timestamp': _iso(upload.upload_date),
        'location': {
            'lat': upload.lat,
            'lon': upload.lon,
            'city': upload.city,
            'country': upload.country,
        },
    }


def build_event_graph(event):
    """Return the deterministic, privacy-preserving corroboration graph for
    `event` over its VERIFIED members, with an integrity hash attached.

    Independence and the two corroboration numbers are recomputed here from the
    same rule as events.service (reshares collapse to one origin), so the graph
    is self-consistent with the live Event without depending on stored counters.
    """
    members = [m for m in (getattr(event, 'members', []) or [])
               if m.verification_status == 'VERIFIED']

    fp_counts = Counter(
        (m.media_sha256 or '').strip().lower()
        for m in members
        if m.user_id is not None and (m.media_sha256 or '').strip()
    )

    # Deterministic order: earliest first, id as the stable tiebreaker.
    ordered = sorted(members, key=lambda m: (_iso(m.upload_date) or '', m.id))
    nodes = [_node(m, fp_counts) for m in ordered]

    # Independent origins = distinct fingerprints (each reshare cluster is one)
    # + distinct identities among text-only members. Mirrors
    # events.service._independent_origins.
    origins = set()
    for m in members:
        if m.user_id is None:
            continue
        fp = (m.media_sha256 or '').strip().lower() or None
        origins.add(('media', fp) if fp else ('id', m.user_id))

    reshare_clusters = [
        {'fingerprint': fp, 'size': n}
        for fp, n in sorted(fp_counts.items()) if n > 1
    ]

    graph = {
        'schema_version': GRAPH_SCHEMA_VERSION,
        'event': {
            'id': event.id,
            'status': event.status_override or event.status,
            'is_overridden': event.status_override is not None,
            'title': event.title,
            'summary': event.summary,
            'location': {
                'city': event.city,
                'country': event.country,
                'lat': event.lat,
                'lon': event.lon,
            },
            'severity': event.severity,
            'confidence_band': confidence_band(event.confidence_score),
            # updated_at is deliberately omitted: it is "last touched"
            # bookkeeping, not corroboration substance, and including it would
            # churn the content hash on every incidental write. created_at and
            # closed_at are lifecycle facts and stay.
            'timestamps': {
                'created_at': _iso(event.created_at),
                'closed_at': _iso(event.closed_at),
            },
        },
        'corroboration': {
            'counted': len({m.user_id for m in members if m.user_id is not None}),
            'independent': len(origins),
            'supporting': sum(1 for m in members if m.user_id is None),
            'reshare_clusters': reshare_clusters,
        },
        # Advisory coordination flags (text/timing). NOT reflected in the counts
        # above -- they are surfaced for a moderator/reader to weigh, because for
        # text/timing the same pattern marks genuine corroboration as much as
        # astroturf (see independence.py). Empty == nothing flagged.
        'coordination_flags': analyze_independence(members),
        'nodes': nodes,
    }
    graph['integrity'] = {'graph_sha256': graph_content_hash(graph)}
    return graph


def canonical_graph_bytes(graph):
    """Deterministic bytes for a graph, excluding any attached integrity block
    (ADR-0014 canonical style: compact, sorted keys)."""
    body = {k: v for k, v in graph.items() if k != 'integrity'}
    return json.dumps(body, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False).encode('utf-8')


def graph_content_hash(graph):
    """Lowercase-hex SHA-256 over the canonical graph bytes -- a stable content
    address for integrity checks and preservation (UC9)."""
    return hashlib.sha256(canonical_graph_bytes(graph)).hexdigest()


def snapshot_event(event, reason=None):
    """Persist a durable, content-addressed snapshot of `event`'s corroboration
    graph -- capture-before-deletion (UC9). Append-only and deduplicated: if the
    latest snapshot already has this exact graph hash, nothing material changed
    and the existing row is returned instead of storing a duplicate. Does not
    commit -- the caller owns the transaction (matches events.service)."""
    from app.models import db, EventGraphSnapshot

    graph = build_event_graph(event)
    digest = graph['integrity']['graph_sha256']

    latest = (
        EventGraphSnapshot.query
        .filter_by(event_id=event.id)
        .order_by(EventGraphSnapshot.id.desc())
        .first()
    )
    if latest is not None and latest.graph_sha256 == digest:
        return latest

    snap = EventGraphSnapshot(
        event_id=event.id,
        schema_version=graph['schema_version'],
        graph_sha256=digest,
        graph_json=json.dumps(graph, sort_keys=True, separators=(',', ':'),
                              ensure_ascii=False),
        status=graph['event']['status'],
        reason=reason,
    )
    db.session.add(snap)
    db.session.flush()
    return snap
