"""Shared Supabase client accessor for v2 modules.

Reuses the client initialized in storage.session.init_pool().
"""


def get_client():
    """Lazy-import client from storage.session module."""
    from storage import session as _session_mod
    return _session_mod._client
