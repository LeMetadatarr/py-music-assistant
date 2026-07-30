# py-music-assistant

A Python HTTP client and [mediavocab](https://github.com/TigreGotico/mediavocab)
bridge for a [Music Assistant](https://www.music-assistant.io/) server.

It is the single transport and conversion layer shared by the OVOS Music Assistant
integrations:

- **[ovos-media-plugin-mass](https://github.com/OpenVoiceOS/ovos-media-plugin-mass)**: playback backend (`opm.media.audio`)
- **[ovos-media-provider-mass](https://github.com/OpenVoiceOS/ovos-media-provider-mass)**: catalog/search provider (`opm.media.provider`)
- **[ovos-skill-music-assistant](https://github.com/OpenVoiceOS/ovos-skill-music-assistant)**: legacy OCP search skill

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

The client talks to the server's synchronous JSON `/api` endpoint. It has no
WebSocket lifecycle. Item `uri` values are `library://<type>/<id>` identifiers.
The `ovos-media-plugin-mass` backend resolves and plays these identifiers.

## Docs

- [docs/index.md](docs/index.md): overview
- [docs/client-api.md](docs/client-api.md): `SimpleHTTPMusicAssistantClient` reference
- [docs/mediavocab-bridge.md](docs/mediavocab-bridge.md): dict to `Release` mapping

## Tests

```bash
pip install -e .[test]
pytest test/                                   # unit + end2end, network-free (mocked + fixtures)
MASS_SERVER_URL=http://<host>:8095 pytest test/live/   # opt-in, against a real server
```

The end-to-end tests ([test/end2end/](test/end2end/)) exercise the full round trip
this library owns: HTTP transport, then the Music Assistant `/api` protocol, then
the mediavocab bridge, then typed `Release` objects, all against a mocked server.
This is a transport library with no skills and no message bus, so `ovoscope`
end-to-end tests live in the consumers
([ovos-media-plugin-mass](https://github.com/OpenVoiceOS/ovos-media-plugin-mass),
[ovos-media-provider-mass](https://github.com/OpenVoiceOS/ovos-media-provider-mass),
[ovos-skill-music-assistant](https://github.com/OpenVoiceOS/ovos-skill-music-assistant)).

## License

Apache-2.0
