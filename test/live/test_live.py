"""Opt-in live tests against a real Music Assistant server.

Skipped unless ``MASS_SERVER_URL`` points at a reachable server, e.g.::

    MASS_SERVER_URL=http://192.168.1.100:8095 pytest test/live/

These hit the network and assert that the live API still returns the shape the
converters expect, so upstream drift is caught here rather than in production.
"""
import os

import pytest

from mediavocab import Release

from py_music_assistant import SimpleHTTPMusicAssistantClient, search_to_releases

MASS_SERVER_URL = os.environ.get("MASS_SERVER_URL")

pytestmark = pytest.mark.skipif(
    not MASS_SERVER_URL, reason="set MASS_SERVER_URL to run live Music Assistant tests"
)


@pytest.fixture(scope="module")
def client():
    return SimpleHTTPMusicAssistantClient(MASS_SERVER_URL)


def test_get_players(client):
    players = client.get_players()
    assert isinstance(players, list)


def test_search_returns_mappable_releases(client):
    res = client.search_media("the beatles", limit=5)
    assert isinstance(res, dict)
    releases = search_to_releases(res)
    assert all(isinstance(r, Release) for r in releases)
    for r in releases:
        assert r.uri
        assert r.work.title
