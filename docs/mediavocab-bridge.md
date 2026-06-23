# mediavocab bridge

`py_music_assistant.converters` maps Music Assistant media-item dicts to
[`mediavocab.Release`](https://github.com/TigreGotico/mediavocab) objects.

```python
from py_music_assistant import item_to_release, search_to_releases, recently_played_to_releases
```

## Functions

| Function | Input | Output |
|---|---|---|
| `item_to_release(entry)` | one media-item dict | `Release` or `None` |
| `items_to_releases(items)` | flat list of item dicts | `list[Release]` |
| `search_to_releases(res)` | a `music/search` response (dict of buckets) | `list[Release]` |
| `recently_played_to_releases(items)` | a `recently_played` list | `list[Release]` (alias of `items_to_releases`) |

`search_to_releases` is **bucket-agnostic**: it flattens every list-valued bucket,
so a new bucket key on the server is handled without code changes.

## Mapping rules

- **Dropped** (returns `None`): items where `is_playable` is `false`, or with no
  `name`/`uri`. Artist identities are kept only when the server marks them
  playable (a playable artist radio).
- **`media_type`**:

  | MAss `media_type` | `mediavocab.MediaType` |
  |---|---|
  | `track`, `album`, `artist` | `MUSIC` |
  | `playlist` | `PLAYLIST` |
  | `radio` | `RADIO` |
  | `podcast` | `PODCAST` |
  | `audiobook` | `AUDIOBOOK` |
  | *(unknown)* | `MUSIC` (fallback) |

- **`uri`**: copied verbatim (`library://<type>/<id>`) — resolved at playback by
  the `ovos-media-plugin-mass` backend.
- **`image`**: the first **remotely-accessible** image, from the top-level
  `image` object or `metadata.images`; local-only paths are dropped (`""`).
- **`work.runtime`**: `duration` (seconds) when present.
- **`work.extra`**: `artist` (joined with `&`), `album`, `favorite`, and
  `mass_media_type` (the original bucket type) for display without a second call.
- **`external_ids`**: copied from the item when present.
- **`match_confidence`**: left at `0.0`. The caller (the provider) scores results
  against the parsed request `Signals`; the OCP pipeline ranks across providers.

## Example

```python
api = SimpleHTTPMusicAssistantClient("http://192.168.1.100:8095")
releases = search_to_releases(api.search_media("worms", limit=10))
# Release(work=Work(title="Worms", media_type=MUSIC, runtime=208.0,
#                   extra={"artist": "Viagra Boys", "album": "Street Worms", ...}),
#         uri="library://track/9903", image="https://…", platform="music-assistant")
```
