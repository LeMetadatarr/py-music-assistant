"""Converters from Music Assistant API dicts to mediavocab typed objects.

Music Assistant's ``music/search`` and ``music/recently_played_items`` endpoints
return media items as plain dicts. Each item carries (among others) ``name``,
``uri`` (a ``library://<type>/<id>`` identifier the ``ovos-media-plugin-mass``
playback backend resolves), ``media_type`` (``track``/``album``/``artist``/
``playlist``/``radio``/``podcast``/``audiobook``), ``is_playable``, ``favorite``,
an ``artists`` list, an ``album`` object, ``duration`` (seconds) and image data.

This module maps those dicts into :class:`mediavocab.Release` objects so a
:class:`MediaProvider` can stay a thin shim. Results are returned **unranked**
(``match_confidence`` left at ``0.0``); the provider scores them against the
parsed request ``Signals``.
"""
from typing import Any, Dict, List, Optional

from mediavocab import MediaType, Release, Work


# Music Assistant ``media_type`` string -> mediavocab ``MediaType``.
_MEDIA_TYPE_MAP: Dict[str, MediaType] = {
    "track": MediaType.MUSIC,
    "album": MediaType.MUSIC,
    "artist": MediaType.MUSIC,
    "playlist": MediaType.PLAYLIST,
    "radio": MediaType.RADIO,
    "podcast": MediaType.PODCAST,
    "audiobook": MediaType.AUDIOBOOK,
}

PLATFORM = "music-assistant"


def _extract_image(entry: Dict[str, Any]) -> str:
    """Return the first remotely-accessible image path for an item, or ``""``.

    Music Assistant exposes art either as a top-level ``image`` object or as a
    list under ``metadata.images``; in both cases an image is only usable when
    ``remotely_accessible`` is set (a local-only path is unreachable by OVOS).
    """
    img = entry.get("image")
    if isinstance(img, dict) and img.get("path") and img.get("remotely_accessible"):
        return img["path"]
    meta = entry.get("metadata") or {}
    for im in meta.get("images") or []:
        if isinstance(im, dict) and im.get("path") and im.get("remotely_accessible"):
            return im["path"]
    return ""


def _extract_artists(entry: Dict[str, Any]) -> List[str]:
    """Return artist names for an item, guarding against missing/empty fields.

    (The legacy ``load_track`` path crashed on items with no ``artists``/
    ``album``; the None-guards live here so every consumer benefits.)
    """
    if entry.get("media_type") == "artist":
        name = (entry.get("name") or "").strip()
        return [name] if name else []
    out: List[str] = []
    for a in entry.get("artists") or []:
        if isinstance(a, dict):
            n = (a.get("name") or "").strip()
            if n:
                out.append(n)
    return out


def item_to_release(entry: Dict[str, Any]) -> Optional[Release]:
    """Convert a single Music Assistant media-item dict to a :class:`Release`.

    Returns ``None`` for items that are not playable or have no ``uri``/``name``
    (e.g. an artist identity with no playable radio). ``artist``, ``album`` and
    ``duration`` are mirrored into ``work.extra`` so a player can render them
    without a second API call; ``match_confidence`` is left at ``0.0`` for the
    caller to score.
    """
    if not isinstance(entry, dict):
        return None
    if not entry.get("is_playable", True):
        return None

    name = (entry.get("name") or "").strip()
    uri = (entry.get("uri") or "").strip()
    if not name or not uri:
        return None

    media_type = _MEDIA_TYPE_MAP.get(entry.get("media_type"), MediaType.MUSIC)

    external_ids: Dict[str, str] = {}
    raw_ext = entry.get("external_ids")
    if isinstance(raw_ext, dict):
        external_ids = {str(k): str(v) for k, v in raw_ext.items() if v}

    artists = _extract_artists(entry)
    album = entry.get("album")
    album_name = album.get("name") if isinstance(album, dict) else None

    work_extra: Dict[str, Any] = {"mass_media_type": entry.get("media_type")}
    if artists:
        work_extra["artist"] = " & ".join(artists)
    if album_name:
        work_extra["album"] = album_name
    if entry.get("favorite"):
        work_extra["favorite"] = True
    duration = entry.get("duration")

    work = Work(
        title=name,
        media_type=media_type,
        runtime=float(duration) if isinstance(duration, (int, float)) and duration else None,
        external_ids=dict(external_ids),
        extra=work_extra,
    )

    return Release(
        work=work,
        uri=uri,
        image=_extract_image(entry),
        platform=PLATFORM,
        match_confidence=0.0,
        external_ids=dict(external_ids),
    )


def items_to_releases(items: Any) -> List[Release]:
    """Map a flat iterable of media-item dicts to a list of Releases.

    Non-dict and non-playable items are skipped. Used directly for the
    ``recently_played`` feed.
    """
    out: List[Release] = []
    for entry in items or []:
        rel = item_to_release(entry)
        if rel is not None:
            out.append(rel)
    return out


def search_to_releases(res: Dict[str, Any]) -> List[Release]:
    """Flatten a Music Assistant ``music/search`` response to a list of Releases.

    The response is a dict of buckets (``tracks``, ``albums``, ``artists``,
    ``playlists``, ``radio``, ``podcasts``, ``audiobooks``); each bucket is a
    list of media-item dicts. This is bucket-agnostic — every list-valued bucket
    is flattened — so new bucket keys are handled without code changes.
    """
    out: List[Release] = []
    for bucket in (res or {}).values():
        if isinstance(bucket, list):
            out.extend(items_to_releases(bucket))
    return out


# Recently-played feed shares the media-item shape, so it reuses the flat mapper.
recently_played_to_releases = items_to_releases
