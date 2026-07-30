# py-music-assistant

A thin, synchronous Python client for a [Music Assistant](https://www.music-assistant.io/)
server, plus a [mediavocab](https://github.com/TigreGotico/mediavocab) bridge.

## Why this exists

The OVOS Music Assistant integrations all need to talk to a Music Assistant
server and turn its catalog into typed, shareable media objects. Keeping this
in one library puts the transport and the dict-to-`Release` mapping in exactly
one place, including the None-guards and image-resolution rules. Without this
library, that logic would be copy-pasted across the playback backend, the
search provider, and the legacy skill.

## Two layers

| Module | Class / functions | Role |
|---|---|---|
| `py_music_assistant.client` | `SimpleHTTPMusicAssistantClient` | HTTP transport over the server's `/api` endpoint |
| `py_music_assistant.converters` | `item_to_release`, `search_to_releases`, `recently_played_to_releases` | map API dicts to `mediavocab.Release` |

The top-level `py_music_assistant` package re-exports both layers.

## The flow

```
"play viagra boys"
   │
   ▼
SimpleHTTPMusicAssistantClient.search_media(...)   # → dict of buckets
   │
   ▼
search_to_releases(res)                            # → list[mediavocab.Release]
   │  (each Release.uri is "library://track/9903")
   ▼
ovos-media-plugin-mass backend.load_track(uri)     # resolves + plays
```

See [client-api.md](client-api.md) and [mediavocab-bridge.md](mediavocab-bridge.md).
