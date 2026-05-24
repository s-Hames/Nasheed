import asyncio
import yt_dlp
from typing import List, Dict, Any
from app.utils.logger import logger

def _run_yt_dlp_search(query: str, limit: int) -> List[Dict[str, Any]]:
    """
    Synchronous helper to search YouTube using yt-dlp flat extraction.
    Runs inside a threadpool via asyncio.to_thread.
    """
    ydl_opts = {
        'quiet': True,
        'extract_flat': 'in_playlist',
        'skip_download': True,
        'playlistend': limit,
        'no_warnings': True,
        'ignoreerrors': True,
    }
    
    # We search specifically for the user query
    search_query = f"ytsearch{limit}:{query}"
    logger.info(f"Initiating yt-dlp flat search for query: '{search_query}'")
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(search_query, download=False)
            if not info or 'entries' not in info:
                logger.info(f"No search results returned for query: '{query}'")
                return []
            
            results = []
            for entry in info['entries']:
                if not entry:
                    continue
                
                video_id = entry.get('id')
                if not video_id:
                    continue
                
                # Resolve thumbnail
                thumbnail = None
                thumbnails = entry.get('thumbnails')
                if thumbnails:
                    # Select the last thumbnail URL as it's typically higher quality
                    thumbnail = thumbnails[-1].get('url')
                
                duration = entry.get('duration')
                if duration is not None:
                    duration = int(duration)
                
                results.append({
                    'youtube_id': video_id,
                    'title': entry.get('title') or 'Unknown Title',
                    'thumbnail': thumbnail,
                    'duration': duration,
                    'channel': entry.get('channel') or entry.get('uploader') or 'Unknown Channel',
                    'upload_date': entry.get('upload_date'),
                })
            
            logger.info(f"Found {len(results)} items before scoring/filtering.")
            return results
        except Exception as e:
            logger.error(f"Error during yt-dlp search for '{query}': {str(e)}")
            return []

async def search_youtube_async(query: str, limit: int = 15) -> List[Dict[str, Any]]:
    """
    Asynchronous entry point to search YouTube. Defers execution to a threadpool.
    """
    return await asyncio.to_thread(_run_yt_dlp_search, query, limit)

def _run_get_video_metadata(video_id: str) -> Dict[str, Any]:
    """
    Retrieve video details from YouTube using yt-dlp.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'no_warnings': True,
        'ignoreerrors': False,
    }
    logger.info(f"Fetching metadata for YouTube video ID: {video_id}")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            if not info:
                raise Exception("No video info returned by yt-dlp")
            
            thumbnail = info.get('thumbnail')
            if not thumbnail and info.get('thumbnails'):
                thumbnail = info.get('thumbnails')[-1].get('url')
                
            return {
                'youtube_id': video_id,
                'title': info.get('title') or 'Unknown Title',
                'thumbnail': thumbnail,
                'duration': int(info.get('duration')) if info.get('duration') else None,
                'channel': info.get('channel') or info.get('uploader') or 'Unknown Channel',
                'upload_date': info.get('upload_date')
            }
        except Exception as e:
            logger.error(f"Failed to fetch metadata for video {video_id}: {str(e)}")
            from app.core.exceptions import VideoNotFoundException
            raise VideoNotFoundException(
                message=f"YouTube video with ID {video_id} could not be retrieved: {str(e)}"
            )

async def fetch_video_metadata_async(video_id: str) -> Dict[str, Any]:
    """
    Asynchronously retrieve video details from YouTube.
    """
    return await asyncio.to_thread(_run_get_video_metadata, video_id)
