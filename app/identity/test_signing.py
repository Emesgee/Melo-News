"""
Signed-report verification + pseudonym self-registration tests (Stage C, server).

Uses real ECDSA P-256 keypairs (the primitive the Android Keystore provides,
ADR-0013) to prove: valid signatures verify, tampered/forged ones are rejected,
a pseudonym self-registers on first signed report and is reused after, and an
unsigned report is the (None) web/anonymous lane.

The public key is base64 of the SPKI DER encoding (Android
`PublicKey.getEncoded()`); the signature is base64 of the DER ECDSA signature
(`Signature("SHA256withECDSA")`). The canonical-message encoding is pinned by the
shared cross-language vector in signing_test_vectors.json.
"""

import base64
import json
import os

import pytest
from flask import Flask
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from app.models import db, User, FileType
from app.identity.signing import (
    canonical_message, verify_signature, register_or_get_pseudonym,
    resolve_signed_reporter, derive_handle,
)
from app.story.service import ingest_story

_VECTORS = os.path.join(os.path.dirname(__file__), 'signing_test_vectors.json')


@pytest.fixture
def ctx():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    with app.app_context():
        db.create_all()
        yield
        db.session.remove()


def _keypair():
    """Return (private_key, public_key_b64) where the public key is base64 of the
    SPKI DER encoding -- exactly what Android `PublicKey.getEncoded()` yields."""
    sk = ec.generate_private_key(ec.SECP256R1())
    spki = sk.public_key().public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)
    return sk, base64.b64encode(spki).decode()


def _sign(sk, payload):
    sig = sk.sign(canonical_message(payload), ec.ECDSA(hashes.SHA256()))
    return base64.b64encode(sig).decode()


def _payload(public_key_b64, **over):
    p = {
        'title': 'Explosion at market', 'body': 'Loud blast, smoke rising.',
        'city': 'Testoria', 'country': 'Sandboxia',
        'lat': '10.00000', 'lon': '20.00000',
        'severity': 'HIGH', 'is_sensitive': 'false', 'source_type': 'eyewitness',
        'subject': None, 'tags': None, 'media_sha256': None,
        'published_at': None, 'local_id': None,
        'public_key': public_key_b64,
    }
    p.update(over)
    return p


# --- canonical-message contract (cross-language vector) ---------------------

def test_canonical_message_matches_frozen_vectors():
    """The server must reproduce every frozen `canonical` byte-for-byte; the
    Android client asserts the SAME file. A diff here is a contract break."""
    with open(_VECTORS, encoding='utf-8') as fh:
        vectors = json.load(fh)
    for case in vectors['canonical_message']:
        produced = canonical_message(case['payload']).decode('utf-8')
        assert produced == case['canonical'], f"canonical mismatch: {case['name']}"


def test_public_key_b64_fits_user_column():
    """SPKI-DER base64 of a P-256 key must fit User.public_key (VARCHAR 128)."""
    _, pub = _keypair()
    assert len(pub) <= 128


# --- signature verification -------------------------------------------------

def test_valid_signature_verifies():
    sk, pub = _keypair()
    p = _payload(pub)
    assert verify_signature(pub, canonical_message(p), _sign(sk, p)) is True


def test_tampered_message_fails():
    sk, pub = _keypair()
    p = _payload(pub)
    sig = _sign(sk, p)
    p_tampered = _payload(pub, body='Nothing happened, all calm.')
    assert verify_signature(pub, canonical_message(p_tampered), sig) is False


def test_flipped_is_sensitive_fails():
    """is_sensitive is signed (ADR-0008): a relay can't strip the safety flag."""
    sk, pub = _keypair()
    p = _payload(pub, is_sensitive='true')
    sig = _sign(sk, p)
    p_flipped = _payload(pub, is_sensitive='false')
    assert verify_signature(pub, canonical_message(p_flipped), sig) is False


def test_swapped_media_hash_fails():
    """media_sha256 is signed: swapping the photo breaks verification."""
    sk, pub = _keypair()
    p = _payload(pub, media_sha256='a' * 64)
    sig = _sign(sk, p)
    p_swapped = _payload(pub, media_sha256='b' * 64)
    assert verify_signature(pub, canonical_message(p_swapped), sig) is False


def test_wrong_key_fails():
    sk, pub = _keypair()
    _, other_pub = _keypair()
    p = _payload(pub)
    assert verify_signature(other_pub, canonical_message(p), _sign(sk, p)) is False


def test_malformed_input_returns_false_not_raises():
    assert verify_signature('not-base64!!', b'x', 'also-bad') is False
    assert verify_signature('', b'', '') is False


def test_handle_is_stable_and_keylike():
    _, pub = _keypair()
    assert derive_handle(pub) == derive_handle(pub)
    assert derive_handle(pub).startswith('k-')


# --- registration + ingest --------------------------------------------------

def test_pseudonym_self_registers_then_reuses(ctx):
    _, pub = _keypair()
    u1 = register_or_get_pseudonym(pub)
    assert u1.identity_type == 'pseudonymous' and u1.trust_rung == 1
    assert u1.email is None and u1.public_key == pub
    u2 = register_or_get_pseudonym(pub)
    assert u2.userid == u1.userid                       # same key -> same identity
    assert User.query.filter_by(public_key=pub).count() == 1


def test_resolve_unsigned_is_none(ctx):
    assert resolve_signed_reporter({'title': 'x'}) is None


def test_resolve_invalid_signature_raises(ctx):
    sk, pub = _keypair()
    p = _payload(pub)
    p['signature'] = _sign(sk, p)
    p['body'] = 'tampered after signing'                # break the binding
    with pytest.raises(ValueError):
        resolve_signed_reporter(p)


def test_signed_report_ingest_persists_signature_and_message(ctx):
    db.session.add(FileType(type_name='Other', allowed_extensions='*'))
    db.session.flush()
    sk, pub = _keypair()
    p = _payload(pub, is_sensitive='true')
    p['signature'] = _sign(sk, p)

    story = ingest_story(user_id=None, payload=p)        # no JWT user; key is the identity
    rep = story['provenance']['reporter']
    assert rep['is_anonymous'] is False and rep['is_signed'] is True
    assert rep['handle'] == derive_handle(pub)
    assert User.query.filter_by(public_key=pub).count() == 1

    # The exact signed bytes are persisted verbatim (ADR-0014) and the signed
    # safety flag is stored (ADR-0008).
    from app.models import FileUpload
    row = FileUpload.query.filter_by(report_signature=p['signature']).first()
    assert row is not None
    assert row.is_sensitive is True
    assert row.signed_message == canonical_message(p).decode('utf-8')
