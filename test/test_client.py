"""Tests for SimpleHTTPMusicAssistantClient (network-free, mocked session)."""
from unittest.mock import MagicMock

import pytest

from music_assistant_models.errors import MusicAssistantError

from py_music_assistant import SimpleHTTPMusicAssistantClient


def _client(json_return=None, status=200):
    session = MagicMock()
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_return if json_return is not None else {}
    resp.text = "error body"
    session.post.return_value = resp
    return SimpleHTTPMusicAssistantClient("http://mass.local:8095/", session=session), session


def test_url_normalisation():
    client, _ = _client()
    assert client.server_url == "http://mass.local:8095"
    assert client.api_url == "http://mass.local:8095/api"


def test_send_command_posts_payload_and_returns_json():
    client, session = _client(json_return={"ok": True})
    out = client.send_command("music/search", search_query="worms", limit=5)

    assert out == {"ok": True}
    session.post.assert_called_once()
    args, kwargs = session.post.call_args
    assert args[0] == "http://mass.local:8095/api"
    payload = kwargs["json"]
    assert payload["command"] == "music/search"
    assert payload["args"] == {"search_query": "worms", "limit": 5}
    assert "message_id" in payload


def test_send_command_raises_on_non_200():
    client, _ = _client(status=500)
    with pytest.raises(MusicAssistantError):
        client.send_command("players/all")


def test_search_media_builds_args():
    client, session = _client(json_return={"tracks": []})
    client.search_media("worms", limit=7)
    payload = session.post.call_args.kwargs["json"]
    assert payload["command"] == "music/search"
    assert payload["args"]["search_query"] == "worms"
    assert payload["args"]["limit"] == 7


def test_recently_played_command():
    client, session = _client(json_return=[])
    client.recently_played()
    assert session.post.call_args.kwargs["json"]["command"] == "music/recently_played_items"


def test_track_info_passes_uri():
    client, session = _client(json_return={})
    client.track_info("library://track/9903")
    payload = session.post.call_args.kwargs["json"]
    assert payload["command"] == "music/item_by_uri"
    assert payload["args"] == {"uri": "library://track/9903"}
