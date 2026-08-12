"""YouTube transcript extractor + content pipeline.

Fetches video metadata and transcripts from YouTube URLs.
Uses youtube-transcript-api (install: pip install youtube-transcript-api)
with graceful fallback when not installed.

Usage:
    from shared.youtube_extractor import get_transcript, get_video_info
    transcript = get_transcript("https://youtube.com/watch?v=...")
"""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import quote

from defusedxml import ElementTree as DefusedElementTree

from shared.safe_http import SafeHTTPError, SafeHTTPPolicy, fetch


def _extract_video_id(url: str) -> str | None:
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/)([a-zA-Z0-9_-]{11})",
        r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
    ]
    for pat in patterns:
        match = re.search(pat, url)
        if match:
            return match.group(1)
    return None


def get_video_info(video_id: str) -> dict[str, Any]:
    """Get YouTube video metadata via oEmbed (no API key)."""
    oembed_url = (
        f"https://www.youtube.com/oembed?url=https://youtube.com/watch?v={video_id}&format=json"
    )
    try:
        response = fetch(
            oembed_url,
            headers={"User-Agent": "archeaxis-workspace/0.3"},
            policy=SafeHTTPPolicy(
                max_bytes=256_000,
                allowed_hosts=("www.youtube.com", "youtube.com"),
                allowed_content_types=("application/json",),
            ),
        )
        data = json.loads(response.body.decode("utf-8"))
        return {
            "video_id": video_id,
            "title": data.get("title", ""),
            "author": data.get("author_name", ""),
            "thumbnail": data.get("thumbnail_url", ""),
            "url": f"https://youtube.com/watch?v={video_id}",
        }
    except (SafeHTTPError, UnicodeDecodeError, json.JSONDecodeError):
        return {"video_id": video_id, "title": "", "author": "", "error": "oembed failed"}


def get_transcript(url_or_id: str, languages: list[str] | None = None) -> dict[str, Any]:
    """Fetch YouTube video transcript.

    Args:
        url_or_id: YouTube URL or video ID.
        languages: preferred language codes (default: ['en', 'zh-Hans', 'zh']).

    Returns:
        {video_id, title, transcript: [{text, start, duration}], full_text, language}.
    """
    video_id = _extract_video_id(url_or_id) or url_or_id
    if languages is None:
        languages = ["en", "zh-Hans", "zh", "ja", "ko"]

    info = get_video_info(video_id)

    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        transcript_list = YouTubeTranscriptApi.get_transcript(
            video_id,
            languages=languages,
        )
        full_text = " ".join(seg["text"] for seg in transcript_list)

        return {
            "video_id": video_id,
            "title": info.get("title", ""),
            "author": info.get("author", ""),
            "url": info.get("url", f"https://youtube.com/watch?v={video_id}"),
            "transcript": transcript_list,
            "full_text": full_text,
            "segment_count": len(transcript_list),
            "language": transcript_list[0].get("language", "unknown") if transcript_list else "",
        }
    except ImportError:
        return {
            "video_id": video_id,
            "title": info.get("title", ""),
            "error": "youtube-transcript-api not installed. Run: pip install youtube-transcript-api",
        }
    except Exception as e:
        return {
            "video_id": video_id,
            "title": info.get("title", ""),
            "error": str(e),
        }


def search_youtube(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """Search YouTube via RSS feed (no API key).

    Returns list of {video_id, title, url}.
    """
    encoded = quote(query)
    feed_url = f"https://www.youtube.com/feeds/videos.xml?q={encoded}"

    try:
        response = fetch(
            feed_url,
            headers={
                "User-Agent": "archeaxis-workspace/0.3",
            },
            policy=SafeHTTPPolicy(
                max_bytes=2_000_000,
                allowed_hosts=("www.youtube.com", "youtube.com"),
                allowed_content_types=("application/atom+xml", "application/xml", "text/xml"),
            ),
        )
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        root = DefusedElementTree.fromstring(response.body)
        results = []
        for entry in root.findall("atom:entry", ns)[:max_results]:
            title_el = entry.find("atom:title", ns)
            link_el = entry.find("atom:link", ns)
            vid = ""
            if link_el is not None:
                href = link_el.get("href", "")
                vid = _extract_video_id(href) or ""
            results.append(
                {
                    "video_id": vid,
                    "title": title_el.text if title_el is not None else "",
                    "url": f"https://youtube.com/watch?v={vid}",
                }
            )
        return results
    except (SafeHTTPError, DefusedElementTree.ParseError):
        return []
