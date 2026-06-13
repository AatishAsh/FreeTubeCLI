import json
import urllib.request
import urllib.parse
import yt_dlp

# List of some reliable public Invidious instances
INVIDIOUS_INSTANCES = [
    "https://inv.tux.rs",
    "https://invidious.io.lol",
    "https://iv.ggtyler.dev",
    "https://invidious.lunar.icu",
    "https://yewtu.be"
]

def search_youtube(query, is_playlist=False, max_results=10):
    """
    Search YouTube using Invidious API. 
    Falls back to yt-dlp if Invidious fails.
    """
    # If it's a direct URL, yt-dlp is still best for metadata extraction
    if query.startswith(('http://', 'https://')):
        return _search_ytdlp(query, is_playlist, max_results)

    # Try Invidious instances
    for instance in INVIDIOUS_INSTANCES:
        try:
            params = urllib.parse.urlencode({
                'q': query,
                'type': 'playlist' if is_playlist else 'video',
                'page': '1'
            })
            url = f"{instance}/api/v1/search?{params}"
            
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read().decode())
                
                # Format Invidious results to match our expected internal structure
                results = []
                for item in data[:max_results]:
                    # Map Invidious fields to common metadata fields
                    formatted = {
                        'id': item.get('videoId') or item.get('playlistId'),
                        'title': item.get('title'),
                        'uploader': item.get('author'),
                        'duration': item.get('lengthSeconds'),
                        'thumbnail': item.get('videoThumbnails', [{}])[-1].get('url') if item.get('videoThumbnails') else None,
                        'url': f"https://www.youtube.com/watch?v={item.get('videoId')}" if item.get('videoId') else None
                    }
                    results.append(formatted)
                
                if results:
                    return results
        except Exception as e:
            # Try next instance
            continue

    # Final Fallback to yt-dlp
    return _search_ytdlp(query, is_playlist, max_results)

def _search_ytdlp(query, is_playlist=False, max_results=10):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': 'in_playlist' if is_playlist else True,
        'skip_download': True,
    }

    if not query.startswith(('http://', 'https://')):
        search_query = f"ytsearch{max_results}:{query}"
    else:
        search_query = query

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(search_query, download=False)
            if 'entries' in info:
                return info['entries']
            else:
                return [info]
        except Exception:
            return []

def get_stream_url(video_url, audio_only=False):
    """Extract the direct stream URL for a given video/audio."""
    ydl_opts = {
        'format': 'bestaudio/best' if audio_only else 'bestvideo+bestaudio/best',
        'quiet': True,
        'no_warnings': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(video_url, download=False)
            return info['url']
        except Exception:
            return None
