"""Minimal CSRF protection.

The project intentionally avoids extra dependencies (see repo.py / db.py),
so instead of pulling in Flask-WTF just for this, we implement the same
double-submit-token pattern by hand:

1. A random token is generated once per session and stored server-side
   in the session cookie (signed by Flask, so the client can't forge it).
2. Every state-changing form includes that token as a hidden field; every
   fetch()-based POST sends it in the `X-CSRFToken` header.
3. Before any POST/PUT/PATCH/DELETE request reaches a view, we verify the
   submitted token matches the one in the session.

This blocks classic CSRF (a third-party site can get a browser to fire a
POST with the victim's cookies, but it cannot read the token to include).
"""
import secrets

from flask import abort, request, session

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
# Endpoints that must stay reachable without a browser session token
# (pure JSON/webhook-style endpoints called by the tutor widget before any
# form was rendered). Keep this list tiny and explicit.
EXEMPT_ENDPOINTS = {"main.tutor_mensagem"}


def _get_or_create_token():
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_hex(32)
        session["csrf_token"] = token
    return token


def inject_csrf_token():
    """Callable exposed to Jinja as `csrf_token()`."""
    return _get_or_create_token()


def csrf_protect():
    if request.method in SAFE_METHODS:
        return None
    if request.endpoint in EXEMPT_ENDPOINTS:
        return None
    # Static files / missing endpoint (404) -- let the normal handlers deal with it.
    if not request.endpoint or request.endpoint.startswith("static"):
        return None

    expected = session.get("csrf_token")
    submitted = request.form.get("csrf_token") or request.headers.get("X-CSRFToken")
    if not submitted and request.is_json:
        submitted = (request.get_json(silent=True) or {}).get("csrf_token")

    if not expected or not submitted or not secrets.compare_digest(str(expected), str(submitted)):
        abort(403)
    return None
