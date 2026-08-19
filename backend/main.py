"""Compatibility entry point for the active application.

The production service is implemented in app.py and is launched as app:app.
This module intentionally exposes the same application instead of maintaining
a second, incompatible API implementation.
"""

try:
	from .app import app
except ImportError:
	from app import app

__all__ = ["app"]
