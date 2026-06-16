import argparse
import sys
import shutil
import os
from rich.console import Console
from rich.panel import Panel
from rich import print as rprint

from search import search_youtube
from ui import select_video, choice_menu
from player import play_media, play_queue
from config import load_config, save_config

console = Console()

class AppState:
    def __init__(self):
        config = load_config()
        self.quality = config.get("quality", "1080")
        self.audio_only = config.get("audio_only", False)
        self.cookies = config.get("cookies")

    def save(self):
        save_config({
            "quality": self.quality,
            "audio_only": self.audio_only,
            "cookies": self.cookies
        })

def check_dependencies():
    """Check if system dependencies (mpv) are installed."""
    if not shutil.which("mpv"):
        rprint("[red]Error: 'mpv' is not installed or not in PATH.[/red]")
        rprint("[yellow]Please install mpv (e.g., 'sudo apt install mpv').[/yellow]")
        sys.exit(1)

def show_header(state):
    console.clear()
    status = f"[cyan]Quality:[/cyan] {state.quality}p | [cyan]Audio-Only:[/cyan] {'Yes' if state.audio_only else 'No'}"
    if state.cookies:
        status += f" | [cyan]Cookies:[/cyan] Active"
    
    header = Panel(
        f"[bold red]FreeTube CLI[/bold red]\n{status}",
        border_style="red",
        expand=True
    )
    console.print(header)

def interactive_loop(state):
    current_idx = 0
    while True:
        show_header(state)
        options = [
            {"label": "Search Videos", "value": "search"},
            {"label": "Search Playlists", "value": "playlist_search"},
            {"label": f"Toggle Quality ({state.quality}p)", "value": "quality"},
            {"label": f"Toggle Audio-Only ({'On' if state.audio_only else 'Off'})", "value": "audio"},
            {"label": "Exit", "value": "exit"}
        ]
        
        idx = choice_menu("Main Menu", options, current_index=current_idx)
        
        if idx == -1 or options[idx]["value"] == "exit":
            rprint("\n[yellow]Goodbye![/yellow]")
            break
            
        current_idx = idx
        action = options[idx]["value"]
        
        if action == "search":
            query = console.input("\n[bold cyan]Enter search query: [/bold cyan]")
            if query:
                run_search_and_play(query, False, state)
        elif action == "playlist_search":
            query = console.input("\n[bold cyan]Enter playlist query/URL: [/bold cyan]")
            if query:
                run_search_and_play(query, True, state)
        elif action == "quality":
            qualities = ["144", "240", "360", "480", "720", "1080", "1440", "2160"]
            try:
                q_idx = qualities.index(state.quality)
                state.quality = qualities[(q_idx + 1) % len(qualities)]
            except ValueError:
                state.quality = "1080"
            state.save()
        elif action == "audio":
            state.audio_only = not state.audio_only
            state.save()

def run_search_and_play(query, is_playlist, state):
    current_page = 1
    
    while True:
        rprint(f"\n[cyan]Fetching Page {current_page} for:[/cyan] [bold]{query}[/bold]...")
        entries = search_youtube(query, is_playlist=is_playlist, page=current_page)
        
        if not entries:
            rprint("[red]No results found.[/red]")
            if current_page > 1:
                rprint("[yellow]Returning to Page 1...[/yellow]")
                current_page = 1
                continue
            console.input("\nPress Enter to return...")
            return

        if is_playlist:
            rprint(f"[green]Playing playlist with {len(entries)} items...[/green]")
            urls = [f"https://www.youtube.com/watch?v={e['id']}" if 'id' in e else e.get('url') for e in entries if e]
            urls = [u for u in urls if u]
            play_queue(urls, audio_only=state.audio_only, cookies=state.cookies, quality=state.quality)
            break
        else:
            selected = select_video(entries, page=current_page)
            
            if not selected:
                break # Cancelled
            
            if selected.get('type') == 'nav':
                if selected['action'] == 'next':
                    current_page += 1
                elif selected['action'] == 'prev':
                    current_page = max(1, current_page - 1)
                continue # Re-search with new page
            
            # Standard selection
            url = selected.get('url') or f"https://www.youtube.com/watch?v={selected.get('id')}"
            rprint(f"[green]Playing:[/green] [bold]{selected.get('title')}[/bold]...")
            play_media(url, audio_only=state.audio_only, cookies=state.cookies, quality=state.quality)
            break # Exit loop after playing

def main():
    check_dependencies()

    parser = argparse.ArgumentParser(
        description="FreeTubeCLI: Watch YouTube videos in your terminal without ads."
    )
    parser.add_argument("query", nargs="*", help="Search query or YouTube URL (starts in one-shot mode)")
    parser.add_argument("--audio-only", action="store_true", help="Stream audio only")
    parser.add_argument("--playlist", action="store_true", help="Handle query as a playlist")
    parser.add_argument("--cookies", help="Cookies path or browser")
    parser.add_argument("--quality", choices=["144", "240", "360", "480", "720", "1080", "1440", "2160"], help="Max height")

    args = parser.parse_args()
    
    # Initialize state from saved config
    state = AppState()

    # CLI arguments override saved config for the current session ONLY if they were provided
    if args.quality: state.quality = args.quality
    if args.audio_only: state.audio_only = True
    if args.cookies: state.cookies = args.cookies

    if args.query:
        # One-shot mode
        run_search_and_play(" ".join(args.query), args.playlist, state)
    else:
        # Full interactive mode
        try:
            interactive_loop(state)
        except KeyboardInterrupt:
            rprint("\n[yellow]Exiting...[/yellow]")

if __name__ == "__main__":
    main()
