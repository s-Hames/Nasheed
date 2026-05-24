import asyncio
import time
import yt_dlp
from app.utils.logger import logger
from app.core.exceptions import StreamExtractionException


# Different YouTube client configurations to try in order.
# When YouTube blocks one client, others may still work.
_CLIENT_CONFIGS = [
    {
        # Default: let yt-dlp pick (uses android_vr fallback when no JS runtime)
        'label': 'default',
        'opts': {},
    },
    {
        # Force the mweb (mobile web) client which often bypasses restrictions
        'label': 'mweb',
        'opts': {
            'extractor_args': {'youtube': {'player_client': ['mweb']}},
        },
    },
    {
        # Force the mediaconnect client
        'label': 'mediaconnect',
        'opts': {
            'extractor_args': {'youtube': {'player_client': ['mediaconnect']}},
        },
    },
    {
        # Try the TV embedded client
        'label': 'tv_embedded',
        'opts': {
            'extractor_args': {'youtube': {'player_client': ['tv_embedded']}},
        },
    },
]

MAX_RETRIES = 2
RETRY_DELAY = 1.0  # seconds


def _extract_stream_url_from_info(info: dict) -> str | None:
    """Extract the best audio stream URL from yt-dlp info dict."""
    # 1. Check top-level URL (normally maps to the format requested)
    stream_url = info.get('url')

    # 2. Scan formats for a high-quality audio stream
    if not stream_url:
        formats = info.get('formats', [])
        # Filter for audio-only streams (vcodec='none', acodec!='none')
        audio_formats = [
            f for f in formats
            if f.get('acodec') != 'none' and (f.get('vcodec') == 'none' or f.get('vcodec') is None)
        ]

        if audio_formats:
            # Sort by average bitrate (abr) descending
            audio_formats.sort(key=lambda x: x.get('abr') or 0, reverse=True)
            stream_url = audio_formats[0].get('url')
        elif formats:
            # Fallback to any available format
            formats.sort(key=lambda x: x.get('tbr') or 0, reverse=True)
            stream_url = formats[0].get('url')

    return stream_url


def _try_extract(video_id: str, client_config: dict) -> str | None:
    """
    Attempt extraction with a specific client configuration.
    Returns the stream URL on success, None on failure.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    label = client_config['label']

    base_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'skip_download': True,
        'no_warnings': True,
        'ignoreerrors': False,
    }
    # Merge client-specific options
    base_opts.update(client_config.get('opts', {}))

    logger.info(f"Attempting stream extraction for {video_id} with client '{label}'")

    try:
        with yt_dlp.YoutubeDL(base_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                logger.warning(f"Client '{label}': no info returned for {video_id}")
                return None

            stream_url = _extract_stream_url_from_info(info)
            if stream_url:
                logger.info(f"Client '{label}' succeeded for {video_id}")
                return stream_url
            else:
                logger.warning(f"Client '{label}': info returned but no stream URL for {video_id}")
                return None
    except Exception as e:
        logger.warning(f"Client '{label}' failed for {video_id}: {e}")
        return None


def _run_extract_stream(video_id: str) -> str:
    """
    Synchronous helper to extract direct audio streaming URL.
    Tries multiple YouTube client configurations with retries.
    Runs inside a threadpool via asyncio.to_thread.
    """
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        for config in _CLIENT_CONFIGS:
            try:
                stream_url = _try_extract(video_id, config)
                if stream_url:
                    return stream_url
            except Exception as e:
                last_error = e

        # Brief pause before retrying the full set of clients
        if attempt < MAX_RETRIES:
            logger.info(
                f"All clients failed for {video_id} on attempt {attempt}/{MAX_RETRIES}. "
                f"Retrying in {RETRY_DELAY}s..."
            )
            time.sleep(RETRY_DELAY)

    # All attempts exhausted
    logger.error(
        f"Stream extraction exhausted all {MAX_RETRIES} attempts across "
        f"{len(_CLIENT_CONFIGS)} clients for video {video_id}. "
        f"Last error: {last_error}"
    )
    raise StreamExtractionException(
        message=(
            f"Failed to retrieve playable audio stream for video {video_id}. "
            f"Direct streaming URL could not be extracted."
        ),
        details={
            "video_id": video_id,
            "attempts": MAX_RETRIES,
            "clients_tried": [c['label'] for c in _CLIENT_CONFIGS],
            "hint": (
                "YouTube may require a JavaScript runtime (Node.js or Deno) for reliable extraction. "
                "Install one and ensure it is on your PATH."
            ),
        },
    )


async def extract_stream_async(video_id: str) -> str:
    """
    Asynchronously extracts a direct audio stream URL for a YouTube video.
    """
    return await asyncio.to_thread(_run_extract_stream, video_id)
