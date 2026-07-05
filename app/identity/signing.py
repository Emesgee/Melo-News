"""
app/identity/signing.py

Signed-report verification + pseudonym self-registration (Stage C, server half).

A citizen reporter holds an ECDSA P-256 keypair generated inside the Android
Keystore -- hardware-backed and non-extractable (ADR-0013). The public key IS
the pseudonym. Each report is signed on-device, so it's tamper-evident even when
relayed through other devices. The server:

  1. recomputes the canonical signed message from the report fields,
  2. verifies the ECDSA-P256 (SHA-256) signature against the claimed public key,
  3. self-registers a pseudonymous User on the first valid signed report
     (no signup step) and reuses it thereafter.

A report with no signature is the unsigned (web/anonymous) lane and returns
None. A report whose signature does NOT verify is rejected (raises), so a
tampered or forged signature can never be published as "signed".

THE SIGNING CONTRACT (the Android client must produce byte-identical input):

  * public_key -- base64 of the X.509 SubjectPublicKeyInfo (SPKI) DER encoding
    of the P-256 public key, i.e. Android `PublicKey.getEncoded()`.
  * signature  -- base64 of the DER-encoded ECDSA signature over the canonical
    message, from `Signature.getInstance("SHA256withECDSA")`.
  * canonical message -- compact, sorted-key JSON of exactly the signed fields,
    taken verbatim from the payload (missing -> null):

        json.dumps(doc, sort_keys=True, separators=(",",":"), ensure_ascii=False)

  Every signed value is a JSON string or null, EXCEPT `tags`, which is a sorted
  JSON array of strings (ADR-0014/ADR-0015). The client is the SOLE formatter:
  lat/lon are fixed 5-decimal strings, is_sensitive is "true"/"false",
  media_sha256 is a lowercase hex digest (or null when text-only), published_at
  is an ISO-8601 UTC string. The server never re-formats -- it signs/verifies
  whatever the payload holds. A frozen cross-language example set lives in
  `signing_test_vectors.json` (asserted by both server and Android tests).
"""

import base64
import hashlib
import json
import logging

from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_der_public_key

from app.models import db, User

logger = logging.getLogger(__name__)

# Exact fields bound by the signature -- the tamper-evident envelope
# (ADR-0008 scope, ADR-0015 first-cut set). Order here is irrelevant: the
# canonical message is sorted by key. Every value is a string or null except
# `tags` (a sorted array of strings).
_SIGNED_FIELDS = (
    'body', 'city', 'country', 'is_sensitive', 'lat', 'local_id', 'lon',
    'media_sha256', 'public_key', 'published_at', 'severity', 'source_type',
    'subject', 'tags', 'title',
)


def canonical_message(payload):
    """Deterministic bytes the client signs. Compact, sorted-key JSON of the
    signed fields, taken verbatim from the payload (the client is the sole
    formatter -- see the module contract)."""
    doc = {k: payload.get(k) for k in _SIGNED_FIELDS}
    return json.dumps(doc, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False).encode('utf-8')


def _b64decode(value):
    """Tolerant standard/url-safe base64 decode with padding fixup."""
    s = value.strip().replace('-', '+').replace('_', '/')
    s += '=' * (-len(s) % 4)
    return base64.b64decode(s)


def verify_signature(public_key_b64, message, signature_b64):
    """True iff `signature_b64` is a valid ECDSA-P256/SHA-256 signature over
    `message` (bytes) by `public_key_b64`. The public key is base64 of the SPKI
    DER encoding; the signature is base64 of the DER ECDSA signature. Never
    raises on malformed input -> False."""
    try:
        pub = load_der_public_key(_b64decode(public_key_b64))
        if not isinstance(pub, ec.EllipticCurvePublicKey):
            return False
        if not isinstance(pub.curve, ec.SECP256R1):
            return False
        pub.verify(_b64decode(signature_b64), message, ec.ECDSA(hashes.SHA256()))
        return True
    except (InvalidSignature, UnsupportedAlgorithm, ValueError, TypeError):
        return False


def derive_handle(public_key_b64):
    """Stable, non-reversible default handle from the key, e.g. 'k-3f9a1c8e22'.
    Readers can rename later; this just guarantees a unique non-empty handle."""
    digest = hashlib.sha256(public_key_b64.strip().encode('utf-8')).hexdigest()
    return f'k-{digest[:10]}'


def register_or_get_pseudonym(public_key_b64):
    """Return the User anchored to this public key, creating a fresh
    pseudonymous identity (rung 1, no email/password) on first sight."""
    pk = public_key_b64.strip()
    user = User.query.filter_by(public_key=pk).first()
    if user is not None:
        return user
    user = User(
        public_key=pk,
        display_handle=derive_handle(pk),
        identity_type='pseudonymous',
        role='reporter',
        trust_rung=1,
    )
    db.session.add(user)
    db.session.flush()
    logger.info("self-registered pseudonymous identity %s", user.display_handle)
    return user


def resolve_signed_reporter(payload):
    """Inspect a report payload for a signature.

    Returns (User, signature_b64) when a valid signature is present (self-
    registering the pseudonym if needed), or None when the report is unsigned.
    Raises ValueError when a signature is present but does NOT verify -- such a
    report must be rejected, never published as signed.
    """
    public_key = (payload.get('public_key') or '').strip()
    signature = (payload.get('signature') or '').strip()
    if not public_key or not signature:
        return None
    if not verify_signature(public_key, canonical_message(payload), signature):
        raise ValueError('invalid report signature')
    return register_or_get_pseudonym(public_key), signature
