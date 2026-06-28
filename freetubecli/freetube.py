import argparse
import sys
import shutil
import os
from rich.console import Console
from rich.panel import Panel
from rich import print as rprint

from rich.table import Table
from .search import search_youtube
from .ui import select_video, choice_menu
from .player import play_media, play_queue
from .config import load_config, save_config
from . import playlist

console = Console()

class AppState:
    def __init__(self):
        config = load_config()
        self.quality = config.get("quality", "1080")
        self.audio_only = config.get("audio_only", False)
        self.auto_play = config.get("auto_play", True)
        self.cookies = config.get("cookies")
        self.show_thumbnails = config.get("show_thumbnails", True)

    def save(self):
        save_config({
            "quality": self.quality,
            "audio_only": self.audio_only,
            "auto_play": self.auto_play,
            "cookies": self.cookies,
            "show_thumbnails": self.show_thumbnails
        })

def check_dependencies():
    """Check if system dependencies (mpv) are installed."""
    if not shutil.which("mpv"):
        rprint("[red]Error: 'mpv' is not installed or not in PATH.[/red]")
        rprint("[yellow]Please install mpv (e.g., 'sudo apt install mpv').[/yellow]")
        sys.exit(1)

def show_header(state):
    console.clear()
    status = f"[cyan]Quality:[/cyan] {state.quality}p | [cyan]Audio-Only:[/cyan] {'Yes' if state.audio_only else 'No'} | [cyan]Thumbnails:[/cyan] {'Yes' if state.show_thumbnails else 'No'}"
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
            {"label": "My Playlists", "value": "my_playlists"},
            {"label": "Play from URL", "value": "direct_url"},
            {"label": "Settings", "value": "settings"},
            {"label": "Exit", "value": "exit"}
        ]
        
        idx = choice_menu("Main Menu", options, current_index=current_idx)
        
        if idx == -1 or options[idx]["value"] == "exit":
            rprint("\n[yellow]Goodbye![/yellow]")
            break
            
        current_idx = idx
        action = options[idx]["value"]
        
        try:
            if action == "search":
                query = console.input("\n[bold cyan]Enter search query: [/bold cyan]")
                if query:
                    run_search_and_play(query, False, state)
            elif action == "playlist_search":
                query = console.input("\n[bold cyan]Enter playlist query/URL: [/bold cyan]")
                if query:
                    run_search_and_play(query, True, state)
            elif action == "my_playlists":
                manage_playlists(state)
            elif action == "direct_url":
                url = console.input("\n[bold cyan]Paste YouTube URL: [/bold cyan]").strip()
                if url:
                    run_search_and_play(url, "playlist" in url.lower(), state)
            elif action == "settings":
                settings_menu(state)
        except KeyboardInterrupt:
            rprint("\n[yellow]Action cancelled.[/yellow]")
            import time; time.sleep(0.5)

def settings_menu(state):
    current_idx = 0
    while True:
        show_header(state)
        options = [
            {"label": f"Quality: {state.quality}p", "value": "quality"},
            {"label": f"Audio-Only: {'On' if state.audio_only else 'Off'}", "value": "audio"},
            {"label": f"Auto-play: {'On' if state.auto_play else 'Off'}", "value": "autoplay"},
            {"label": f"Thumbnails: {'On' if state.show_thumbnails else 'Off'}", "value": "thumbnails"},
            {"label": "Back", "value": "back"}
        ]
        
        idx = choice_menu("Settings", options, current_index=current_idx)
        if idx == -1 or options[idx]["value"] == "back":
            break
            
        current_idx = idx
        action = options[idx]["value"]
        
        if action == "quality":
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
        elif action == "autoplay":
            state.auto_play = not state.auto_play
            state.save()
        elif action == "thumbnails":
            state.show_thumbnails = not state.show_thumbnails
            state.save()

def manage_playlists(state):
    while True:
        show_header(state)
        playlist_names = playlist.get_playlist_names()
        if not playlist_names:
            rprint("[yellow]No playlists found.[/yellow]")
            console.input("\nPress Enter to return...")
            return

        options = [{"label": name, "value": name} for name in playlist_names]
        options.append({"label": "Back", "value": "back"})
        
        idx = choice_menu("My Playlists", options)
        if idx == -1 or options[idx]["value"] == "back":
            return
            
        name = options[idx]["value"]
        
        all_playlists = playlist.load_playlists()
        entries = all_playlists.get(name, [])
        
        sub_options = [
            {"label": "Play Entire Playlist", "value": "play"},
            {"label": "Select & Play Video", "value": "select_play"},
            {"label": "Delete Playlist", "value": "delete"},
            {"label": "Back", "value": "back"}
        ]
        
        show_header(state)
        # Display the list of videos in the playlist
        if entries:
            video_table = Table(show_header=True, header_style="bold magenta", expand=True)
            video_table.add_column("#", width=3, justify="right")
            video_table.add_column("Title", ratio=3)
            video_table.add_column("Channel", ratio=2)
            video_table.add_column("Duration", ratio=1)
            
            limit = 8
            for i, entry in enumerate(entries[:limit]):
                title = entry.get('title', 'Unknown')
                uploader = entry.get('uploader', 'Unknown')
                duration = entry.get('duration')
                duration_str = f"{int(duration)//60}:{int(duration)%60:02d}" if duration else "??:??"
                video_table.add_row(str(i + 1), title, uploader, duration_str)
                
            footer = ""
            if len(entries) > limit:
                footer = f"\n[dim]... and {len(entries) - limit} more videos[/dim]"
                
            console.print(Panel(video_table, title=f"[bold cyan] Videos in '{name}' ({len(entries)} total) [/bold cyan]", border_style="cyan", subtitle=footer))
        else:
            rprint("[yellow]Playlist is empty.[/yellow]")
            
        sub_idx = choice_menu(f"Playlist: {name}", sub_options)
        if sub_idx == -1 or sub_options[sub_idx]["value"] == "back":
            continue
            
        sub_action = sub_options[sub_idx]["value"]
        if sub_action == "play":
            if entries:
                play_queue(entries, audio_only=state.audio_only, cookies=state.cookies, quality=state.quality, show_thumbnails=state.show_thumbnails)
            else:
                rprint("[red]Playlist is empty.[/red]")
                import time; time.sleep(1)
        elif sub_action == "select_play":
            if entries:
                res = select_video(entries, page=1, show_thumbnails=state.show_thumbnails)
                if res and res.get('type') == 'play':
                    selected = res.get('entry')
                    try:
                        idx_sel = entries.index(selected)
                        to_play = entries[idx_sel:]
                        play_queue(to_play, audio_only=state.audio_only, cookies=state.cookies, quality=state.quality, show_thumbnails=state.show_thumbnails)
                    except ValueError:
                        url = selected.get('url') or f"https://www.youtube.com/watch?v={selected.get('id')}"
                        play_media(url, audio_only=state.audio_only, cookies=state.cookies, quality=state.quality, show_thumbnails=state.show_thumbnails)
            else:
                rprint("[red]Playlist is empty.[/red]")
                import time; time.sleep(1)
        elif sub_action == "delete":
            confirm = console.input(f"\n[red]Are you sure you want to delete '{name}'? (y/n): [/red]").lower()
            if confirm == 'y':
                playlist.delete_playlist(name)
                rprint(f"[green]Deleted {name}.[/green]")
                import time; time.sleep(1)

def run_search_and_play(query, is_playlist, state):
    current_page = 1
    
    while True:
        show_header(state)
        rprint(f"\n[cyan]Fetching Page {current_page} for:[/cyan] [bold]{query}[/bold]...")
        entries = search_youtube(query, is_playlist=is_playlist, page=current_page)
        
        if not entries:
            rprint("[red]No results found.[/red]")
            if current_page > 1:
                rprint("[yellow]Returning to Page 1...[/yellow]")
                current_page = 1
                import time; time.sleep(1)
                continue
            console.input("\nPress Enter to return...")
            return

        if is_playlist:
            rprint(f"[green]Playing playlist with {len(entries)} items...[/green]")
            play_queue(entries, audio_only=state.audio_only, cookies=state.cookies, quality=state.quality, show_thumbnails=state.show_thumbnails)
            break
        elif len(entries) == 1 and query.startswith(('http://', 'https://')):
            # Direct video URL - play immediately
            entry = entries[0]
            url = entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}"
            rprint(f"[green]Playing:[/green] [bold]{entry.get('title', 'Video')}[/bold]...")
            play_media(url, audio_only=state.audio_only, cookies=state.cookies, quality=state.quality, show_thumbnails=state.show_thumbnails)
            break
        else:
            while True:
                show_header(state)
                rprint(f"\n[cyan]Results for:[/cyan] [bold]{query}[/bold] (Page {current_page})")
                res = select_video(entries, page=current_page, show_thumbnails=state.show_thumbnails)
                
                if not res:
                    return # Cancelled
                
                if res.get('type') == 'nav':
                    if res['action'] == 'next':
                        current_page += 1
                    elif res['action'] == 'prev':
                        current_page = max(1, current_page - 1)
                    break # Break inner loop to re-fetch/re-render outer loop
                
                action = res.get('type')
                selected = res.get('entry')
                
                if action == 'add':
                    playlist_names = playlist.get_playlist_names()
                    options = [{"label": "[ New Playlist ]", "value": "new"}]
                    options.extend([{"label": name, "value": name} for name in playlist_names])
                    options.append({"label": "Cancel", "value": "cancel"})
                    
                    idx = choice_menu("Add to Playlist", options)
                    if idx != -1 and options[idx]["value"] != "cancel":
                        target_name = None
                        if options[idx]["value"] == "new":
                            name = console.input("\n[bold cyan]Enter new playlist name: [/bold cyan]").strip()
                            if name: target_name = name
                        else:
                            target_name = options[idx]["value"]
                        
                        if target_name:
                            success, msg = playlist.add_to_playlist(target_name, selected)
                            rprint(f"[{'green' if success else 'red'}]{msg}[/{'green' if success else 'red'}]")
                            import time; time.sleep(1)
                    continue # Back to selection
                
                if action == 'play':
                    if state.auto_play:
                        try:
                            idx = entries.index(selected)
                            to_play = entries[idx:]
                            play_queue(to_play, audio_only=state.audio_only, cookies=state.cookies, quality=state.quality, show_thumbnails=state.show_thumbnails)
                        except ValueError:
                            url = selected.get('url') or f"https://www.youtube.com/watch?v={selected.get('id')}"
                            rprint(f"[green]Playing:[/green] [bold]{selected.get('title')}[/bold]...")
                            play_media(url, audio_only=state.audio_only, cookies=state.cookies, quality=state.quality, show_thumbnails=state.show_thumbnails)
                    else:
                        url = selected.get('url') or f"https://www.youtube.com/watch?v={selected.get('id')}"
                        rprint(f"[green]Playing:[/green] [bold]{selected.get('title')}[/bold]...")
                        play_media(url, audio_only=state.audio_only, cookies=state.cookies, quality=state.quality, show_thumbnails=state.show_thumbnails)
                    return # Exit after playing

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
    parser.add_argument("--no-thumbnails", action="store_true", help="Disable video thumbnails generation/display")

    args = parser.parse_args()
    
    # Initialize state from saved config
    state = AppState()

    # CLI arguments override saved config for the current session ONLY if they were provided
    if args.quality: state.quality = args.quality
    if args.audio_only: state.audio_only = True
    if args.cookies: state.cookies = args.cookies
    if args.no_thumbnails: state.show_thumbnails = False

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
