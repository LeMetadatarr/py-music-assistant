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


def test_send_command_passes_timeout_to_session():
    """Regression: a request without a timeout can hang the caller forever."""
    client, session = _client(json_return={})
    client.send_command("players/all")
    assert session.post.call_args.kwargs["timeout"] == client.timeout


def test_custom_timeout_is_honoured():
    session = MagicMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {}
    session.post.return_value = resp
    client = SimpleHTTPMusicAssistantClient("http://mass.local:8095", session=session, timeout=2.5)

    client.send_command("players/all")

    assert session.post.call_args.kwargs["timeout"] == 2.5


QUEUE_ITEM = {
    "queue_id": "queue_1",
    "queue_item_id": "item_1",
    "name": "Worms",
    "duration": 208,
    "media_item": {
        "media_type": "track",
        "item_id": "9903",
        "provider": "library",
        "name": "Worms",
        "uri": "library://track/9903",
        "provider_mappings": [],
        "artists": [{"item_id": "1", "provider": "library", "name": "Viagra Boys",
                      "media_type": "artist", "provider_mappings": []}],
    },
}


def test_get_player_queue_items_returns_queue_item_objects():
    """Regression: raw dicts were returned instead of QueueItem objects, so
    downstream ``hasattr(item, "name")`` checks in ``_extract_track_from_queue``
    always failed (dicts have no ``name`` attribute) and the queue-based track
    fallback silently never worked."""
    client, session = _client(json_return=[QUEUE_ITEM])

    items = client.get_player_queue_items("queue_1")

    assert len(items) == 1
    item = items[0]
    assert hasattr(item, "name")
    assert item.name == "Worms"
    assert item.media_item.name == "Worms"


def test_get_player_queue_items_passes_pagination_args():
    client, session = _client(json_return=[])
    client.get_player_queue_items("queue_1", limit=5, offset=10)
    payload = session.post.call_args.kwargs["json"]
    assert payload["args"] == {"queue_id": "queue_1", "limit": 5, "offset": 10}


def test_get_player_queue_items_empty_result():
    client, _ = _client(json_return=[])
    assert client.get_player_queue_items("queue_1") == []


PLAYER_WITH_UNTITLED_CURRENT_MEDIA = {
    "player_id": "p1",
    "provider": "sonos",
    "type": "player",
    "name": "Kitchen",
    "available": True,
    "device_info": {},
    "powered": True,
    "volume_level": 30,
    # current_media has no title (typical mid-transition state), so
    # get_player_state must fall back to the active queue's current item.
    "current_media": {"uri": "library://track/9903", "queue_item_id": "item_1"},
}


def test_get_player_state_falls_back_to_queue_item_name():
    """End-to-end regression for the get_player_queue_items dict/object bug:
    when current_media carries no title, get_player_state must resolve the
    track name from the active queue item instead of silently returning
    "No track"."""
    session = MagicMock()

    def post(url, json=None, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        if json["command"] == "players/all":
            resp.json.return_value = [PLAYER_WITH_UNTITLED_CURRENT_MEDIA]
        elif json["command"] == "player_queues/items":
            resp.json.return_value = [QUEUE_ITEM]
        else:
            raise AssertionError(f"unexpected command {json['command']}")
        return resp

    session.post.side_effect = post
    client = SimpleHTTPMusicAssistantClient("http://mass.local:8095", session=session)

    state = client.get_player_state("p1")

    assert state["current_track"] == "Worms"


def test_no_token_sends_no_authorization_header():
    client, session = _client(json_return={})
    client.send_command("players/all")
    headers = session.post.call_args.kwargs["headers"]
    assert headers is None


def test_token_arg_sets_bearer_header():
    session = MagicMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {}
    session.post.return_value = resp
    client = SimpleHTTPMusicAssistantClient(
        "http://mass.local:8095", session=session, token="secret-tok"
    )

    client.send_command("players/all")

    headers = session.post.call_args.kwargs["headers"]
    assert headers == {"Authorization": "Bearer secret-tok"}


def test_token_from_env_var(monkeypatch):
    monkeypatch.setenv("MASS_TOKEN", "env-tok")
    session = MagicMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {}
    session.post.return_value = resp
    client = SimpleHTTPMusicAssistantClient("http://mass.local:8095", session=session)

    client.send_command("players/all")

    headers = session.post.call_args.kwargs["headers"]
    assert headers == {"Authorization": "Bearer env-tok"}


def test_token_arg_overrides_env_var(monkeypatch):
    monkeypatch.setenv("MASS_TOKEN", "env-tok")
    client, session = _client(json_return={})
    client2 = SimpleHTTPMusicAssistantClient(
        "http://mass.local:8095", session=session, token="explicit-tok"
    )
    client2.send_command("players/all")
    headers = session.post.call_args.kwargs["headers"]
    assert headers == {"Authorization": "Bearer explicit-tok"}


def test_401_raises_typed_authentication_error():
    from music_assistant_models.errors import AuthenticationRequired

    client, _ = _client(status=401)
    with pytest.raises(AuthenticationRequired) as exc_info:
        client.send_command("players/all")

    message = str(exc_info.value)
    assert "MASS_TOKEN" in message
    assert "token=" in message
    assert "settings/users" in message


def test_authenticated_call_with_token_succeeds():
    session = MagicMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"ok": True}
    session.post.return_value = resp
    client = SimpleHTTPMusicAssistantClient(
        "http://mass.local:8095", session=session, token="secret-tok"
    )

    out = client.send_command("players/all")

    assert out == {"ok": True}
    assert session.post.call_args.kwargs["headers"] == {"Authorization": "Bearer secret-tok"}


def test_login_sets_token_and_returns_it():
    session = MagicMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "success": True,
        "access_token": "minted-tok",
        "user": {"user_id": "u1", "username": "miro", "display_name": "Miro", "role": "admin"},
    }
    session.post.return_value = resp
    client = SimpleHTTPMusicAssistantClient("http://mass.local:8095", session=session)

    token = client.login("miro", "hunter2")

    assert token == "minted-tok"
    assert client.token == "minted-tok"
    payload = session.post.call_args.kwargs["json"]
    assert payload["command"] == "auth/login"
    assert payload["args"] == {"username": "miro", "password": "hunter2"}


def test_login_failure_raises_authentication_required():
    from music_assistant_models.errors import AuthenticationRequired

    session = MagicMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"success": False, "error": "Invalid credentials"}
    session.post.return_value = resp
    client = SimpleHTTPMusicAssistantClient("http://mass.local:8095", session=session)

    with pytest.raises(AuthenticationRequired):
        client.login("miro", "wrong")
