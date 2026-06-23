# py-music-assistant

Python HTTP client and [mediavocab](https://github.com/TigreGotico/mediavocab)
bridge for a [Music Assistant](https://www.music-assistant.io/) server.

It is the single transport + conversion layer shared by the OVOS Music Assistant
integrations:

- **[ovos-media-plugin-mass](https://github.com/OpenVoiceOS/ovos-media-plugin-mass)** — playback backend (`opm.media.audio`)
- **[ovos-media-provider-mass](https://github.com/OpenVoiceOS/ovos-media-provider-mass)** — catalog/search provider (`opm.media.provider`)
- **[ovos-skill-music-assistant](https://github.com/OpenVoiceOS/ovos-skill-music-assistant)** — legacy OCP search skill

## Install

```bash
pip install py-music-assistant
```

## Usage

```python
from py_music_assistant import SimpleHTTPMusicAssistantClient, search_to_releases

api = SimpleHTTPMusicAssistantClient("http://192.168.1.100:8095")

# raw search (dict of buckets: tracks/albums/artists/radio/podcasts/audiobooks)
res = api.search_media("viagra boys", limit=10)

# mapped to typed mediavocab.Release objects (unranked; score them yourself)
releases = search_to_releases(res)
for r in releases:
    print(r.work.title, r.work.media_type, r.uri)   # e.g. "Worms" MUSIC library://track/9903
```

The client talks to the server's synchronous JSON `/api` endpoint (no WebSocket
lifecycle). Item `uri`s are `library://<type>/<id>` identifiers that the
`ovos-media-plugin-mass` backend resolves and plays.

## Docs

- [docs/index.md](docs/index.md) — overview
- [docs/client-api.md](docs/client-api.md) — `SimpleHTTPMusicAssistantClient` reference
- [docs/mediavocab-bridge.md](docs/mediavocab-bridge.md) — dict → `Release` mapping

## Tests

```bash
pip install -e .[test]
pytest test/                                   # network-free (mocked + fixtures)
MASS_SERVER_URL=http://<host>:8095 pytest test/live/   # opt-in, against a real server
```

## License

Apache-2.0
