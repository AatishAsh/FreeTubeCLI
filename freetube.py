import argparse
import sys
import shutil
import os

from search import search_youtube
from ui import select_video
from player import play_media, play_queue

def check_dependencies():
    """Check if system dependencies (mpv) are installed."""
    if not shutil.which("mpv"):
        print("Error: 'mpv' is not installed or not in PATH.", file=sys.stderr)
        print("Please install mpv (e.g., 'sudo apt install mpv' or 'brew install mpv').", file=sys.stderr)
        sys.exit(1)

def main():
    check_dependencies()

    parser = argparse.ArgumentParser(
        description="FreeTubeCLI: Watch YouTube videos in your terminal without ads."
    )
    parser.add_argument(
        "query",
        nargs="*",
        help="Search query or YouTube URL"
    )
    parser.add_argument(
        "--audio-only",
        action="store_true",
        help="Stream audio only (no video window)"
    )
    parser.add_argument(
        "--playlist",
        action="store_true",
        help="Handle the query as a playlist"
    )
    parser.add_argument(
        "--cookies",
        help="Path to cookies file or browser name (e.g., 'chrome', 'firefox')"
    )
    parser.add_argument(
        "--quality",
        choices=["144", "240", "360", "480", "720", "1080", "1440", "2160"],
        default="1080",
        help="Maximum video height (e.g., 720 for 720p). Defaults to 1080."
    )

    args = parser.parse_args()

    if not args.query:
        parser.print_help()
        sys.exit(0)

    query_str = " ".join(args.query)
    
    # 1. Search/Fetch entries
    print(f"Fetching results for: {query_str}...")
    entries = search_youtube(query_str, is_playlist=args.playlist)
    
    if not entries:
        print("No results found or error occurred.")
        sys.exit(1)

    # 2. Handle results
    if args.playlist:
        # Play the entire playlist
        print(f"Playing playlist with {len(entries)} items...")
        urls = [f"https://www.youtube.com/watch?v={e['id']}" if 'id' in e else e.get('url') for e in entries if e]
        urls = [u for u in urls if u]
        exit_code = play_queue(urls, audio_only=args.audio_only, cookies=args.cookies, quality=args.quality)
    elif len(entries) == 1 and query_str.startswith(('http://', 'https://')):
        # Direct video URL provided
        entry = entries[0]
        url = entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}"
        print(f"Playing: {entry.get('title', 'Video')}...")
        exit_code = play_media(url, audio_only=args.audio_only, cookies=args.cookies, quality=args.quality)
    else:
        # Search results - show menu
        selected = select_video(entries)
        if selected:
            url = selected.get('url') or f"https://www.youtube.com/watch?v={selected.get('id')}"
            print(f"Playing: {selected.get('title', 'Video')}...")
            exit_code = play_media(url, audio_only=args.audio_only, cookies=args.cookies, quality=args.quality)
        else:
            print("No video selected.")
            sys.exit(0)

    sys.exit(exit_code if exit_code is not None else 0)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)
