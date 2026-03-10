"""
Vercel Serverless Function entry point.
Exposes the FastAPI auth backend as a single serverless function.
All /api/* requests are routed here by vercel.json rewrites.
"""

import sys
import os

# Add the auth backend directory to Python path so all imports resolve
_backend_dir = os.path.join(os.path.dirname(__file__), '..', 'auth_app', 'backend')
_backend_dir = os.path.abspath(_backend_dir)
sys.path.insert(0, _backend_dir)

# Set VERCEL flag so database.py uses NullPool
os.environ.setdefault("VERCEL", "1")

try:
    # Import the FastAPI app — Vercel auto-detects the ASGI `app` object
    from main import app  # noqa: E402, F401
except Exception as exc:
    # Surface import errors as a visible JSON response instead of opaque 500
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    app = FastAPI()

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    async def error_handler(path: str):
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to import auth backend",
                "detail": str(exc),
                "backend_dir": _backend_dir,
                "sys_path": sys.path[:5],
            },
        )
