import json
import urllib.request
import urllib.parse
import yt_dlp

# List of reliable public Invidious instances
INVIDIOUS_INSTANCES = [
    "https://inv.tux.rs",
    "https://invidious.io.lol",
    "https://iv.ggtyler.dev",
    "https://invidious.lunar.icu",
    "https://yewtu.be",
    "https://invidious.projectsegfau.lt",
    "https://invidious.nerdvpn.de",
    "https://invidious.privacydev.net"
]

# Global cache
SEARCH_CACHE = {}

def search_youtube(query, is_playlist=False, page=1, max_results=20):
    cache_key = (query, is_playlist, page)
    if cache_key in SEARCH_CACHE:
        return SEARCH_CACHE[cache_key]

    if query.startswith(('http://', 'https://')):
        res = _search_ytdlp(query, is_playlist, page=1)
        if res: SEARCH_CACHE[cache_key] = res
        return res

    # Try Invidious instances
    for instance in INVIDIOUS_INSTANCES:
        try:
            params = urllib.parse.urlencode({
                'q': query,
                'type': 'playlist' if is_playlist else 'video',
                'page': str(page)
            })
            url = f"{instance}/api/v1/search?{params}"
            
            with urllib.request.urlopen(url, timeout=7) as response:
                data = json.loads(response.read().decode())
                
                if not isinstance(data, list):
                    continue

                results = []
                for item in data:
                    # Some instances return a lot, we cap it at max_results
                    if len(results) >= max_results: break
                    
                    formatted = {
                        'id': item.get('videoId') or item.get('playlistId'),
                        'title': item.get('title'),
                        'uploader': item.get('author'),
                        'duration': item.get('lengthSeconds'),
                        'thumbnail': item.get('videoThumbnails', [{}])[-1].get('url') if item.get('videoThumbnails') else None,
                        'url': f"https://www.youtube.com/watch?v={item.get('videoId')}" if item.get('videoId') else None,
                        'type': 'video' if item.get('videoId') else 'playlist'
                    }
                    if formatted['id']: # Only add if we have an ID
                        results.append(formatted)
                
                if results:
                    SEARCH_CACHE[cache_key] = results
                    return results
        except Exception:
            continue

    # Final Fallback to yt-dlp
    res = _search_ytdlp(query, is_playlist, page=page, max_results=max_results)
    if res: SEARCH_CACHE[cache_key] = res
    return res

def _search_ytdlp(query, is_playlist=False, page=1, max_results=20):
    total_to_fetch = page * max_results
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': 'in_playlist' if is_playlist else True,
        'skip_download': True,
    }

    if not query.startswith(('http://', 'https://')):
        search_query = f"ytsearch{total_to_fetch}:{query}"
    else:
        search_query = query

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(search_query, download=False)
            if 'entries' in info:
                all_entries = info['entries']
                start_idx = (page - 1) * max_results
                return all_entries[start_idx : start_idx + max_results]
            else:
                return [info]
        except Exception:
            return []
