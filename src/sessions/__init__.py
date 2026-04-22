"""SQLite-backed session manager for FinAgent MVP.

Designed for Mem0 integration in production; uses SQLite for the local demo
so that no external service is required during development.
"""
from .session_manager import SessionManager

__all__ = ["SessionManager"]
