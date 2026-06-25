"""End-to-end test for py-music-assistant.

``py-music-assistant`` is a pure transport + conversion library — it has no skills
and no message bus, so an *ovoscope* harness (which drives an OVOS mini-stack)
does not apply here; the ovoscope end-to-end tests live in the consumers
(``ovos-media-plugin-mass``, ``ovos-media-provider-mass``,
``ovos-skill-music-assistant``). The genuine end-to-end surface for *this* library
is the full round-trip it owns:

    HTTP transport  ->  Music Assistant /api JSON protocol  ->  mediavocab bridge

This test exercises that whole path with a mocked :class:`requests.Session`: a
real :class:`SimpleHTTPMusicAssistantClient` serialises a command to the wire,
the fake server routes it by ``command`` and replies with a recorded payload, and
the response is mapped through ``search_to_releases`` /
``recently_played_to_releases`` into typed ``mediavocab.Release`` objects with
playable ``library://`` uris. No network or server is required.
"""
import json
import unittest
from os.path import dirname, join

from mediavocab import MediaType, Release

from py_music_assistant import (
    SimpleHTTPMusicAssistantClient,
    recently_played_to_releases,
    search_to_releases,
)

FIXTURES = join(dirname(dirname(__file__)), "fixtures")
SERVER_URL = "http://mass.local:8095"

_RECENTLY_PLAYED = [
    {"media_type": "track", "name": "Recent Hit", "uri": "library://track/55",
     "is_playable": True, "artists": [{"name": "Someone"}]},
    {"media_type": "radio", "name": "Recent Radio", "uri": "library://radio/7",
     "is_playable": True},
]


def _search_fixture() -> dict:
    with open(join(FIXTURES, "search_worms.json")) as f:
        return json.load(f)


class _FakeResponse:
    """Minimal stand-in for ``requests.Response``."""

    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.text = "" if status_code == 200 else "server error"

    def json(self):
        return self._payload


class _FakeMAssServer:
    """Routes Music Assistant ``/api`` commands to recorded payloads.

    Plays the role of a real server at the HTTP boundary: it is handed to the
    client as its ``requests.Session`` and answers ``session.post`` by reading the
    ``command`` out of the JSON-RPC-style body.
    """

    def __init__(self):
        self.calls = []  # every (command, args) the client sent
        self._routes = {
            "music/search": lambda args: _search_fixture(),
            "music/recently_played_items": lambda args: list(_RECENTLY_PLAYED),
            "music/item_by_uri": lambda args: {
                "name": "Worms", "uri": args["uri"], "media_type": "track",
                "is_playable": True, "artists": [{"name": "Augustus Pablo"}],
                "duration": 180,
            },
            "players/all": lambda args: [],
        }

    def post(self, url, json=None, **kwargs):
        body = json or {}
        command = body.get("command")
        args = body.get("args", {})
        self.calls.append((command, args))
        if command not in self._routes:
            return _FakeResponse({"error": "unknown"}, status_code=500)
        return _FakeResponse(self._routes[command](args))

    def last_args(self, command):
        for cmd, args in reversed(self.calls):
            if cmd == command:
                return args
        raise AssertionError(f"client never sent command {command!r}")


class TestPyMusicAssistantEndToEnd(unittest.TestCase):
    def setUp(self):
        self.server = _FakeMAssServer()
        self.client = SimpleHTTPMusicAssistantClient(SERVER_URL, session=self.server)

    # -- transport / protocol ---------------------------------------------

    def test_search_serialises_correct_command(self):
        """search_media must hit /api with the music/search command + args."""
        self.client.search_media("worms", limit=5)
        args = self.server.last_args("music/search")
        self.assertEqual(args["search_query"], "worms")
        self.assertEqual(args["limit"], 5)

    def test_http_error_raises(self):
        """A non-200 reply must surface as an error, not silent bad data."""
        from music_assistant_models.errors import MusicAssistantError
        with self.assertRaises(MusicAssistantError):
            self.client.send_command("does/not/exist")

    # -- the full round-trip the library owns ------------------------------

    def test_search_round_trip_to_releases(self):
        """search_media -> search_to_releases yields typed, playable Releases."""
        res = self.client.search_media("worms")
        releases = search_to_releases(res)

        self.assertTrue(releases)
        self.assertTrue(all(isinstance(r, Release) for r in releases))
        # every release is a playable library:// item carrying the MA platform tag
        self.assertTrue(all(r.uri.startswith("library://") for r in releases))
        self.assertTrue(all(r.platform == "music-assistant" for r in releases))

        # the buckets map to the expected mediavocab types
        kinds = {r.work.media_type for r in releases}
        self.assertIn(MediaType.MUSIC, kinds)
        self.assertIn(MediaType.RADIO, kinds)
        self.assertIn(MediaType.PODCAST, kinds)
        self.assertIn(MediaType.AUDIOBOOK, kinds)

        # titles survived the round-trip
        titles = {r.work.title for r in releases}
        self.assertIn("Worms", titles)

    def test_track_info_round_trip(self):
        """track_info resolves a single uri the playback backend would load."""
        info = self.client.track_info("library://track/9903")
        self.assertEqual(info["uri"], "library://track/9903")
        self.assertEqual(self.server.last_args("music/item_by_uri")["uri"],
                         "library://track/9903")

    def test_recently_played_round_trip_to_releases(self):
        """recently_played -> recently_played_to_releases for featured content."""
        feed = self.client.recently_played()
        releases = recently_played_to_releases(feed)
        self.assertEqual([r.work.title for r in releases],
                         ["Recent Hit", "Recent Radio"])
        self.assertTrue(all(r.uri.startswith("library://") for r in releases))

    def test_get_players_round_trip(self):
        """get_players is the reachability probe the provider/plugin use."""
        self.assertEqual(self.client.get_players(), [])
        self.assertEqual(self.server.calls[-1][0], "players/all")


if __name__ == "__main__":
    unittest.main()
