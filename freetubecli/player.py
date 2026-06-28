import subprocess
import sys
import socket
import json
import threading
import time
import os
import math
import select
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import print as rprint
from rich.live import Live

from .ui import raw_mode, console
from .image import get_ascii_image

class MPVClient:
    """
    Background worker that communicates with mpv over a UNIX domain socket.
    Observes/polls properties like current position, duration, and pause state.
    """
    def __init__(self, socket_path):
        self.socket_path = socket_path
        self.socket = None
        self.properties = {
            "time-pos": 0.0,
            "duration": 0.0,
            "pause": False,
            "volume": 100.0,
            "playlist-pos": 0,
            "playlist-count": 0,
            "media-title": ""
        }
        self.running = False
        self._buffer = b""

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        connected = False
        # Retry connection for up to 2 seconds to give mpv time to spin up
        for _ in range(20):
            try:
                self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.socket.connect(self.socket_path)
                connected = True
                break
            except Exception:
                time.sleep(0.1)

        if not connected:
            return

        self.socket.setblocking(True)
        
        # Start a thread to poll properties regularly
        poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        poll_thread.start()

        while self.running:
            try:
                data = self.socket.recv(4096)
                if not data:
                    break
                self._buffer += data
                while b"\n" in self._buffer:
                    line, self._buffer = self._buffer.split(b"\n", 1)
                    try:
                        msg = json.loads(line.decode("utf-8", errors="ignore"))
                        if "data" in msg and "request_id" in msg:
                            req_id = msg["request_id"]
                            prop_map = {
                                1: "time-pos",
                                2: "duration",
                                3: "pause",
                                4: "volume",
                                5: "playlist-pos",
                                6: "playlist-count",
                                7: "media-title"
                            }
                            if req_id in prop_map:
                                self.properties[prop_map[req_id]] = msg["data"]
                    except Exception:
                        pass
            except Exception:
                break

    def _poll_loop(self):
        while self.running and self.socket:
            try:
                commands = [
                    {"command": ["get_property", "time-pos"], "request_id": 1},
                    {"command": ["get_property", "duration"], "request_id": 2},
                    {"command": ["get_property", "pause"], "request_id": 3},
                    {"command": ["get_property", "volume"], "request_id": 4},
                    {"command": ["get_property", "playlist-pos"], "request_id": 5},
                    {"command": ["get_property", "playlist-count"], "request_id": 6},
                    {"command": ["get_property", "media-title"], "request_id": 7}
                ]
                for cmd in commands:
                    self.socket.sendall((json.dumps(cmd) + "\n").encode("utf-8"))
            except Exception:
                pass
            time.sleep(0.25)

    def send_command(self, cmd_list):
        if not self.socket:
            return
        try:
            payload = {"command": cmd_list}
            self.socket.sendall((json.dumps(payload) + "\n").encode("utf-8"))
        except Exception:
            pass

    def stop(self):
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass

def get_equalizer_bar(paused):
    """Generates an animating equalizer representation."""
    if paused:
        return "▃▃▃▃▃▃▃▃▃▃▃▃"
    t = time.time()
    bars = []
    chars = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
    for i in range(12):
        val = int(4 + 4 * math.sin(t * 10 + i * 0.6))
        val = max(0, min(val, len(chars) - 1))
        bars.append(chars[val])
    return "".join(bars)

def make_progress_bar(pos, duration):
    """Builds a formatted progress bar string."""
    if duration <= 0:
        return "[cyan]░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░[/cyan] [bold white]00:00[/bold white] / [bold]00:00[/bold]"
    pos = max(0, min(pos, duration))
    pos_min, pos_sec = int(pos) // 60, int(pos) % 60
    dur_min, dur_sec = int(duration) // 60, int(duration) % 60
    
    ratio = pos / duration
    width = 30
    filled = int(width * ratio)
    bar = "█" * filled + "░" * (width - filled)
    
    return f"[cyan]{bar}[/cyan] [bold white]{pos_min:02d}:{pos_sec:02d}[/bold white] / [bold]{dur_min:02d}:{dur_sec:02d}[/bold]"

def get_key_nonblocking(timeout=0.1):
    """Reads keyboard inputs non-blockingly using select and unbuffered raw OS reads."""
    fd = sys.stdin.fileno()
    rlist, _, _ = select.select([sys.stdin], [], [], timeout)
    if rlist:
        try:
            # Read up to 10 bytes directly from raw OS stdin to avoid Python stream buffering
            data = os.read(fd, 10)
            if not data:
                return None
            
            # Map ANSI escape sequences for arrow keys and ESC
            if data == b'\x1b[A': return "UP"
            if data == b'\x1b[B': return "DOWN"
            if data == b'\x1b[C': return "RIGHT"
            if data == b'\x1b[D': return "LEFT"
            if data == b'\x1b': return "ESC"
            
            c = data.decode("utf-8", errors="ignore")
            if c in ('\n', '\r', '\x0d'):
                return "ENTER"
            if c.lower() == 'q':
                return "QUIT"
            return c
        except Exception:
            return None
    return None

def render_audio_tui_layout(
    entry,
    playlist_pos,
    playlist_count,
    time_pos,
    duration,
    paused,
    volume,
    show_thumbnails,
    cached_ascii_thumb,
    entries
):
    """Renders the play panel with equalizer, progress, volume, queue and optional thumbnail."""
    if not entry:
        title = "Loading title..."
        uploader = "Loading channel..."
        thumb_url = None
    else:
        if isinstance(entry, str):
            title = entry
            uploader = "Direct Stream"
            thumb_url = None
        else:
            title = entry.get('title', 'Unknown Title')
            uploader = entry.get('uploader', 'Unknown Channel')
            thumb_url = entry.get('thumbnail')
            if not thumb_url and entry.get('thumbnails'):
                thumb_url = entry.get('thumbnails')[-1].get('url')

    # Metadata & state
    meta_table = Table.grid(padding=(1, 0), expand=True)
    meta_table.add_column(ratio=1)
    
    eq_bar = get_equalizer_bar(paused)
    state_str = "[bold red]❚❚ PAUSED[/bold red]" if paused else f"[bold green]▶ PLAYING  [cyan]{eq_bar}[/cyan][/bold green]"
    
    track_info = f"Track {playlist_pos + 1} of {playlist_count}" if playlist_pos is not None else ""
    
    meta_table.add_row(f"[bold yellow]{title}[/bold yellow]")
    meta_table.add_row(f"[cyan]Channel:[/cyan] {uploader}")
    meta_table.add_row(f"[cyan]State:[/cyan] {state_str}  [dim]({track_info})[/dim]")
    
    # Progress
    meta_table.add_row(make_progress_bar(time_pos, duration))
    
    # Volume
    vol_ratio = volume / 100.0
    vol_width = 15
    vol_filled = int(vol_width * min(1.0, max(0.0, vol_ratio)))
    vol_bar = "█" * vol_filled + "░" * (vol_width - vol_filled)
    meta_table.add_row(f"[cyan]Volume:[/cyan] [bold white]{vol_bar}[/bold white] {int(volume)}%")
    
    # Queue / Up Next (Next 2 items)
    if playlist_pos is not None and playlist_count > 1:
        queue_table = Table.grid(padding=(0, 1))
        queue_table.add_column(justify="left", ratio=1)
        queue_table.add_row("[bold cyan]Next in Queue:[/bold cyan]")
        
        shown = 0
        for i in range(playlist_pos + 1, len(entries)):
            if shown >= 2:
                break
            next_entry = entries[i]
            next_title = next_entry if isinstance(next_entry, str) else next_entry.get('title', 'Unknown Title')
            if len(next_title) > 45:
                next_title = next_title[:42] + "..."
            queue_table.add_row(f"[dim]- {next_title}[/dim]")
            shown += 1
            
        if shown == 0:
            queue_table.add_row("[dim]- End of Queue -[/dim]")
            
        meta_table.add_row("")
        meta_table.add_row(queue_table)
        
    # Controls Help Card
    controls_text = Text.assemble(
        ("Space", "bold yellow"), " Play/Pause  |  ",
        ("←/→", "bold yellow"), " Seek 10s  |  ",
        ("↑/↓", "bold yellow"), " Vol +/-  |  ",
        ("< / ,", "bold yellow"), " Prev  |  ",
        ("> / .", "bold yellow"), " Next  |  ",
        ("q / Esc", "bold red"), " Return"
    )
    meta_table.add_row("")
    meta_table.add_row(Panel(controls_text, border_style="dim", expand=False))

    # Incorporate thumbnail if requested and available
    if show_thumbnails and thumb_url:
        layout_table = Table.grid(padding=(0, 4), expand=True)
        layout_table.add_column(width=42)
        layout_table.add_column(ratio=1)
        
        if cached_ascii_thumb:
            layout_table.add_row(cached_ascii_thumb, meta_table)
        else:
            placeholder = Panel(
                Text("\n\nLoading\nThumbnail...", style="bold cyan", justify="center"),
                border_style="yellow",
                width=40,
                height=11
            )
            layout_table.add_row(placeholder, meta_table)
            
        card_content = layout_table
    else:
        card_content = meta_table

    return Panel(
        card_content,
        title="[bold red] FreeTube Audio Player [/bold red]",
        border_style="red",
        expand=True
    )

def play_audio_tui(entries, urls, cookies=None, show_thumbnails=True):
    """Launches mpv in background and runs interactive playback interface."""
    tmp_dir = os.path.join(os.getcwd(), ".freetube_tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    socket_path = os.path.join(tmp_dir, f"mpv_{os.getpid()}.sock")
    
    # Pre-clean socket if it leftover
    if os.path.exists(socket_path):
        try: os.remove(socket_path)
        except Exception: pass

    cmd = ["mpv", f"--input-ipc-server={socket_path}", "--no-video"]
    if cookies:
        if "/" in cookies or "." in cookies:
            cmd.append(f"--ytdl-raw-options=cookies={cookies}")
        else:
            cmd.append(f"--ytdl-raw-options=cookies-from-browser={cookies}")
    cmd.extend(urls)

    # Launch background mpv
    process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    client = MPVClient(socket_path)
    client.start()
    
    current_thumb_url = None
    cached_ascii_thumb = None
    
    try:
        with raw_mode():
            with Live("", console=console, auto_refresh=False, transient=True) as live:
                while True:
                    if process.poll() is not None:
                        break # mpv exited

                    props = client.properties
                    playlist_pos = props.get("playlist-pos")
                    playlist_count = props.get("playlist-count") or len(entries)
                    time_pos = props.get("time-pos") or 0.0
                    duration = props.get("duration") or 0.0
                    paused = props.get("pause") or False
                    volume = props.get("volume") or 100.0
                    
                    # Resolve entry
                    current_entry = None
                    if playlist_pos is not None and 0 <= playlist_pos < len(entries):
                        current_entry = entries[playlist_pos]
                    elif len(entries) == 1:
                        current_entry = entries[0]
                        
                    # Handle async thumbnail fetch on track change
                    if current_entry and not isinstance(current_entry, str):
                        url = current_entry.get('thumbnail')
                        if not url and current_entry.get('thumbnails'):
                            url = current_entry.get('thumbnails')[-1].get('url')
                        
                        if url != current_thumb_url:
                            current_thumb_url = url
                            cached_ascii_thumb = None
                            if url and show_thumbnails:
                                def fetch_thumb(target_url):
                                    nonlocal cached_ascii_thumb
                                    art = get_ascii_image(target_url, width=40)
                                    if current_thumb_url == target_url:
                                        cached_ascii_thumb = art
                                threading.Thread(target=fetch_thumb, args=(url,), daemon=True).start()
                    else:
                        current_thumb_url = None
                        cached_ascii_thumb = None
                    
                    renderable = render_audio_tui_layout(
                        current_entry,
                        playlist_pos,
                        playlist_count,
                        time_pos,
                        duration,
                        paused,
                        volume,
                        show_thumbnails,
                        cached_ascii_thumb,
                        entries
                    )
                    live.update(renderable, refresh=True)
                    
                    # Keyboard action
                    key = get_key_nonblocking(timeout=0.1)
                    if key in ("QUIT", "ESC"):
                        break
                    elif key == " ":
                        client.send_command(["cycle", "pause"])
                    elif key == "RIGHT":
                        client.send_command(["seek", 10])
                    elif key == "LEFT":
                        client.send_command(["seek", -10])
                    elif key == "UP":
                        client.send_command(["add", "volume", 5])
                    elif key == "DOWN":
                        client.send_command(["add", "volume", -5])
                    elif key in (">", ".", "n", "N"):
                        client.send_command(["playlist-next"])
                    elif key in ("<", ",", "p", "P"):
                        client.send_command(["playlist-prev"])
                        
    finally:
        # Cleanup mpv process
        if process.poll() is None:
            process.terminate()
            try: process.wait(timeout=1.0)
            except subprocess.TimeoutExpired: process.kill()
            
        client.stop()
        
        # Cleanup socket files
        try:
            if os.path.exists(socket_path):
                os.remove(socket_path)
            if os.path.exists(tmp_dir) and not os.listdir(tmp_dir):
                os.rmdir(tmp_dir)
        except Exception:
            pass
            
    return 0

def play_media(media_url, audio_only=False, cookies=None, quality="1080", show_thumbnails=True):
    """
    Play the media using mpv.
    media_url can be a direct stream URL or a YouTube URL.
    """
    if audio_only:
        # Wrap single url and delegate to custom TUI queue player
        return play_queue([{"title": media_url, "url": media_url}], audio_only=True, cookies=cookies, quality=quality, show_thumbnails=show_thumbnails)

    cmd = ["mpv", media_url]
    # Set max height quality
    cmd.append(f"--ytdl-format=bestvideo[height<=?{quality}]+bestaudio/best")
    
    if cookies:
        if "/" in cookies or "." in cookies: # Likely a path
            cmd.append(f"--ytdl-raw-options=cookies={cookies}")
        else: # Likely a browser name
            cmd.append(f"--ytdl-raw-options=cookies-from-browser={cookies}")

    # Inherit stdin, stdout, stderr so the user can control mpv (e.g., space for pause)
    try:
        process = subprocess.run(cmd)
        return process.returncode
    except Exception as e:
        print(f"Error launching mpv: {e}", file=sys.stderr)
        return 1

def play_queue(entries, audio_only=False, cookies=None, quality="1080", show_thumbnails=True):
    """Play a list of entries sequentially."""
    if not entries:
        return 0
        
    urls = []
    for entry in entries:
        if isinstance(entry, str):
            urls.append(entry)
        else:
            url = entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}"
            if url:
                urls.append(url)
                
    if not urls:
        return 0

    if audio_only:
        # Launch custom Audio TUI
        return play_audio_tui(entries, urls, cookies=cookies, show_thumbnails=show_thumbnails)

    cmd = ["mpv"] + urls
    cmd.append(f"--ytdl-format=bestvideo[height<=?{quality}]+bestaudio/best")
    
    if cookies:
        if "/" in cookies or "." in cookies:
            cmd.append(f"--ytdl-raw-options=cookies={cookies}")
        else:
            cmd.append(f"--ytdl-raw-options=cookies-from-browser={cookies}")

    rprint(f"\n[bold green]Starting playback of {len(urls)} items...[/bold green]")
    rprint("[dim]Navigation: '<' Previous | '>' Next | 'q' Menu | 'space' Pause[/dim]")
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        rprint("\n[yellow]Playback stopped.[/yellow]")
    return 0
