"""Python client + mediavocab bridge for a Music Assistant server.

Exposes the synchronous :class:`SimpleHTTPMusicAssistantClient` HTTP client and
converters that map Music Assistant API dicts into :class:`mediavocab.Release`
objects, shared by the OVOS Music Assistant integrations.
"""
from py_music_assistant.client import (
    SimpleHTTPMusicAssistantClient,
    debug_method,
)
from py_music_assistant.converters import (
    PLATFORM,
    item_to_release,
    items_to_releases,
    recently_played_to_releases,
    search_to_releases,
)
from py_music_assistant.version import __version__

__all__ = [
    "SimpleHTTPMusicAssistantClient",
    "debug_method",
    "item_to_release",
    "items_to_releases",
    "search_to_releases",
    "recently_played_to_releases",
    "PLATFORM",
    "__version__",
]
