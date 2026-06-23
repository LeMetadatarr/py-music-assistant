# Client API

`SimpleHTTPMusicAssistantClient` wraps a Music Assistant server's synchronous
JSON `/api` endpoint. Every method posts `{"command", "message_id", "args"}` and
returns the decoded JSON; a non-200 response raises
`music_assistant_models.errors.MusicAssistantError`.

```python
from py_music_assistant import SimpleHTTPMusicAssistantClient
api = SimpleHTTPMusicAssistantClient("http://192.168.1.100:8095")
```

The constructor accepts an optional `requests.Session` (handy for tests or
connection reuse).

## Catalog

| Method | Command | Returns |
|---|---|---|
| `search_media(query, media_types=None, limit=20)` | `music/search` | dict of buckets (`tracks`, `albums`, `artists`, `playlists`, `radio`, `podcasts`, `audiobooks`) |
| `track_info(uri)` | `music/item_by_uri` | single media-item dict |
| `recently_played()` | `music/recently_played_items` | list of media-item dicts |
| `recommendations()` | `music/recommendations` | dict |

## Players & queues

| Method | Command |
|---|---|
| `get_players()` | `players/all` (→ `Player` objects) |
| `get_player_state(player_id)` | derived (state/volume/current track) |
| `get_active_queue(player_id)` | `player_queues/get_active_queue` |
| `play_media(queue_id, media, option=PLAY, radio_mode=False)` | `player_queues/play_media` |
| `queue_command_play/pause/next/previous(queue_id)` | `player_queues/*` |
| `player_command_stop/seek(player_id, ...)` | `players/cmd/*` |
| `player_command_volume_set/up/down/mute(player_id, ...)` | `players/cmd/volume_*` |
| `player_command_power_on/off(player_id)` | `players/player_command_power_*` |

`media` passed to `play_media` is a `library://<type>/<id>` uri as returned by
search.
