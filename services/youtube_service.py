"""Helpers for turning a YouTube URL into a video id, metadata, and transcript."""
import re

import requests
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

YOUTUBE_ID_PATTERNS = [
    r"(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/shorts\/)([A-Za-z0-9_-]{11})",
    r"^([A-Za-z0-9_-]{11})$",  # raw id pasted directly
]


class TranscriptError(Exception):
    """Raised when a transcript cannot be retrieved for a video."""


def extract_video_id(url: str) -> str | None:
    url = url.strip()
    for pattern in YOUTUBE_ID_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def fetch_video_metadata(video_id: str) -> dict:
    """Pulls title/author/thumbnail via YouTube's public oEmbed endpoint (no API key needed)."""
    try:
        resp = requests.get(
            "https://www.youtube.com/oembed",
            params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"},
            timeout=8,
        )
        if resp.ok:
            data = resp.json()
            return {
                "title": data.get("title", "Untitled video"),
                "channel_name": data.get("author_name", ""),
                "thumbnail_url": data.get("thumbnail_url", f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"),
            }
    except requests.RequestException:
        pass
    return {
        "title": "Untitled video",
        "channel_name": "",
        "thumbnail_url": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
    }


def fetch_transcript(video_id: str, preferred_langs=None) -> tuple[str, str]:
    """Returns (transcript_text, language_code). Raises TranscriptError if unavailable."""
    preferred_langs = preferred_langs or ["en", "en-US", "en-GB"]

    try:
        api = YouTubeTranscriptApi()

        # Get available transcripts
        transcript_list = api.list(video_id)

        transcript = None

        # First try preferred languages
        try:
            transcript = transcript_list.find_transcript(preferred_langs)
        except NoTranscriptFound:
            # Fall back to the first available transcript
            for t in transcript_list:
                transcript = t
                break

        if transcript is None:
            raise TranscriptError(
                "No transcript track is available for this video."
            )

        lang_code = transcript.language_code

        # Fetch transcript
        fetched = transcript.fetch()

        # Convert transcript snippets to plain text
        text = " ".join(
            snippet.text.replace("\n", " ").strip()
            for snippet in fetched
            if snippet.text.strip()
        )

        if not text.strip():
            raise TranscriptError("The transcript for this video is empty.")

        return text, lang_code

    except TranscriptsDisabled:
        raise TranscriptError("Transcripts are disabled for this video.")

    except VideoUnavailable:
        raise TranscriptError("This video is unavailable or private.")

    except NoTranscriptFound:
        raise TranscriptError(
            "No transcript is available for this video."
        )

    except TranscriptError:
        raise

    except Exception as exc:
        raise TranscriptError(
            f"Could not fetch a transcript for this video ({exc})."
        )