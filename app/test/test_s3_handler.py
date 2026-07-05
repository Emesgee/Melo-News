"""S3 presigned-upload handler + backend dispatcher (ADR-0017).

boto3 signs presigned URLs locally (no network / no live bucket), so we can
assert the URL shape with fake credentials.
"""

import pytest

import config
from modules import s3_handler, object_storage


def _configure_s3(monkeypatch):
    monkeypatch.setattr(config, 'S3_ENDPOINT_URL', 'https://fsn1.your-objectstorage.com', raising=False)
    monkeypatch.setattr(config, 'S3_REGION', 'auto', raising=False)
    monkeypatch.setattr(config, 'S3_BUCKET', 'melo-media', raising=False)
    monkeypatch.setattr(config, 'S3_ACCESS_KEY_ID', 'AKIAEXAMPLE', raising=False)
    monkeypatch.setattr(config, 'S3_SECRET_ACCESS_KEY', 'secretexample', raising=False)
    monkeypatch.setattr(config, 'S3_PUBLIC_BASE_URL', None, raising=False)
    monkeypatch.setattr(config, 'S3_ADDRESSING_STYLE', 'virtual', raising=False)
    s3_handler._client = None  # rebuild lazily with the patched config


def test_presigned_upload_url_shape(monkeypatch):
    _configure_s3(monkeypatch)
    r = s3_handler.generate_presigned_upload_url('field-reports/7/abc.jpg', expiry_minutes=15)
    assert set(r) >= {'upload_url', 'blob_url', 'blob_name', 'expires_at'}
    assert r['blob_name'] == 'field-reports/7/abc.jpg'
    # SigV4 presigned PUT with our key and a 15-min expiry
    assert 'field-reports/7/abc.jpg' in r['upload_url']
    assert 'X-Amz-Signature=' in r['upload_url']
    assert 'X-Amz-Expires=900' in r['upload_url']
    # permanent object URL = presigned URL minus its query string
    assert '?' not in r['blob_url']
    assert r['blob_url'] == r['upload_url'].split('?', 1)[0]


def test_public_base_url_override(monkeypatch):
    _configure_s3(monkeypatch)
    monkeypatch.setattr(config, 'S3_PUBLIC_BASE_URL', 'https://cdn.example.org/media', raising=False)
    r = s3_handler.generate_presigned_upload_url('field-reports/7/abc.jpg')
    assert r['blob_url'] == 'https://cdn.example.org/media/field-reports/7/abc.jpg'


def test_not_configured_raises(monkeypatch):
    monkeypatch.setattr(config, 'S3_ENDPOINT_URL', None, raising=False)
    monkeypatch.setattr(config, 'S3_BUCKET', None, raising=False)
    s3_handler._client = None
    with pytest.raises(RuntimeError):
        s3_handler.generate_presigned_upload_url('x/y.jpg')


def test_dispatcher_routes_to_s3(monkeypatch):
    _configure_s3(monkeypatch)
    monkeypatch.setattr(config, 'STORAGE_BACKEND', 's3', raising=False)
    r = object_storage.presigned_upload_url('field-reports/1/z.png')
    assert 'X-Amz-Signature=' in r['upload_url']


def test_dispatcher_azure_default_uses_azure(monkeypatch):
    """Default backend routes to the Azure handler (keeps existing behaviour/tests)."""
    monkeypatch.setattr(config, 'STORAGE_BACKEND', 'azure', raising=False)
    sentinel = {'upload_url': 'u', 'blob_url': 'b', 'blob_name': 'n', 'expires_at': 'e'}
    import modules.azure_handler as az
    monkeypatch.setattr(az, 'generate_sas_upload_url', lambda name, expiry_minutes=15: sentinel)
    assert object_storage.presigned_upload_url('field-reports/1/z.png') is sentinel
