"""Tests for the Music Assistant -> mediavocab converters (network-free)."""
import json
from os.path import dirname, join

from mediavocab import MediaType, Release, Work

from py_music_assistant.converters import (
    PLATFORM,
    item_to_release,
    items_to_releases,
    recently_played_to_releases,
    search_to_releases,
)

FIXTURES = join(dirname(__file__), "fixtures")


def _search_fixture():
    with open(join(FIXTURES, "search_worms.json")) as f:
        return json.load(f)


TRACK = {
    "media_type": "track",
    "name": "Worms",
    "uri": "library://track/9903",
    "is_playable": True,
    "favorite": True,
    "duration": 208,
    "artists": [{"name": "Viagra Boys"}],
    "album": {"name": "Street Worms"},
    "image": {"path": "https://art.example/worms.jpg", "remotely_accessible": True},
    "external_ids": {"musicbrainz": "mbid-worms-123"},
}


def test_item_to_release_builds_valid_release():
    rel = item_to_release(TRACK)
    assert isinstance(rel, Release)
    assert isinstance(rel.work, Work)
    assert rel.work.title == "Worms"
    assert rel.work.media_type == MediaType.MUSIC
    assert rel.uri == "library://track/9903"
    assert rel.image == "https://art.example/worms.jpg"
    assert rel.platform == PLATFORM
    assert rel.match_confidence == 0.0
    assert rel.work.runtime == 208.0
    assert rel.work.extra["artist"] == "Viagra Boys"
    assert rel.work.extra["album"] == "Street Worms"
    assert rel.work.extra["favorite"] is True
    assert rel.external_ids["musicbrainz"] == "mbid-worms-123"


def test_media_type_mapping():
    def mt(kind, uri="library://x/1"):
        return item_to_release(
            {"media_type": kind, "name": "x", "uri": uri, "is_playable": True}
        ).work.media_type

    assert mt("track") == MediaType.MUSIC
    assert mt("album") == MediaType.MUSIC
    assert mt("artist") == MediaType.MUSIC
    assert mt("playlist") == MediaType.PLAYLIST
    assert mt("radio") == MediaType.RADIO
    assert mt("podcast") == MediaType.PODCAST
    assert mt("audiobook") == MediaType.AUDIOBOOK
    assert mt("something-new") == MediaType.MUSIC  # unknown -> music fallback


def test_item_to_release_skips_unplayable():
    assert item_to_release({**TRACK, "is_playable": False}) is None


def test_item_to_release_skips_missing_name_or_uri():
    assert item_to_release({"name": "", "uri": "library://x/1", "is_playable": True}) is None
    assert item_to_release({"name": "x", "uri": "", "is_playable": True}) is None
    assert item_to_release("not a dict") is None


def test_item_to_release_none_guards_missing_artists_and_album():
    """Items with no artists/album must not raise (the legacy load_track crash)."""
    rel = item_to_release(
        {"media_type": "track", "name": "bare", "uri": "library://track/1", "is_playable": True,
         "artists": None, "album": None}
    )
    assert isinstance(rel, Release)
    assert "artist" not in rel.work.extra
    assert "album" not in rel.work.extra


def test_image_falls_back_to_metadata_images():
    rel = item_to_release(
        {"media_type": "track", "name": "x", "uri": "library://track/2", "is_playable": True,
         "metadata": {"images": [{"path": "https://m/i.jpg", "remotely_accessible": True}]}}
    )
    assert rel.image == "https://m/i.jpg"


def test_image_skipped_when_not_remotely_accessible():
    rel = item_to_release(
        {"media_type": "track", "name": "x", "uri": "library://track/3", "is_playable": True,
         "image": {"path": "/local/x.jpg", "remotely_accessible": False}}
    )
    assert rel.image == ""


def test_artist_identity_uses_own_name():
    rel = item_to_release(
        {"media_type": "artist", "name": "Viagra Boys", "uri": "library://artist/77",
         "is_playable": True}
    )
    assert rel.work.extra["artist"] == "Viagra Boys"


def test_search_to_releases_flattens_all_buckets():
    res = _search_fixture()
    releases = search_to_releases(res)
    titles = [r.work.title for r in releases]
    # the unplayable artist and the local-only-art track are still playable-by-flag;
    # only the non-playable artist is dropped
    assert "Worms" in titles
    assert "Street Worms" in titles
    assert "Viagra Boys" in titles
    assert "Worm Radio" in titles
    assert "The Worm Cast" in titles
    assert "How to Train Your Worm" in titles
    assert "Not Playable Artist" not in titles
    assert all(isinstance(r, Release) for r in releases)
    # media types preserved across buckets
    by_title = {r.work.title: r.work.media_type for r in releases}
    assert by_title["Worm Radio"] == MediaType.RADIO
    assert by_title["The Worm Cast"] == MediaType.PODCAST
    assert by_title["How to Train Your Worm"] == MediaType.AUDIOBOOK


def test_search_to_releases_handles_empty_and_garbage():
    assert search_to_releases({}) == []
    assert search_to_releases(None) == []
    assert search_to_releases({"tracks": "notalist", "albums": None}) == []


def test_recently_played_is_items_mapper():
    assert recently_played_to_releases is items_to_releases
    rels = recently_played_to_releases([TRACK, {"is_playable": False}])
    assert len(rels) == 1
    assert rels[0].work.title == "Worms"
