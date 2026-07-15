"""Vercel serverless entrypoint (profile W, SPEC §12.1).

Vercel's Python runtime serves the ASGI `app`; every /api/* request is rewritten here
(see vercel.json). The bundled seed DB is opened read-only and /api/simulate returns 403
because the VERCEL env var is set on deployment.
"""

from backend.app.main import app  # noqa: F401
