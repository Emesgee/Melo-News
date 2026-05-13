"""
Shared key function for Flask-Limiter on authenticated endpoints.

Limiting by IP alone is too coarse for citizen-journalism deployments:
reporters in many regions sit behind carrier-grade NAT or shared Wi-Fi,
so a single bad actor on the same NAT could rate-limit a whole city.
Limiting by JWT user id when one is present is much more targeted, and
we still fall back to IP for unauthenticated paths.
"""

from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_limiter.util import get_remote_address


def per_user_or_ip_key() -> str:
    """Return a limiter key keyed to the JWT user when available, else the IP."""
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        if identity:
            return f"user:{identity}"
    except Exception:
        # Bad/expired token — fall through to IP, the request will be
        # rejected by jwt_required anyway.
        pass
    return get_remote_address()
