import sys
import tty
import termios
import contextlib
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich import print as rprint
from .image import get_ascii_image

console = Console()

@contextlib.contextmanager
def raw_mode():
    """Puts terminal in cbreak mode to capture keys immediately."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        yield
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def get_key():
    """Reads a single keypress robustly."""
    b = sys.stdin.read(1)
    if b == '\x1b':
        # Potential escape sequence
        b2 = sys.stdin.read(1)
        if b2 == '[':
            b3 = sys.stdin.read(1)
            if b3 == 'A': return "UP"
            if b3 == 'B': return "DOWN"
            if b3 == 'C': return "RIGHT"
            if b3 == 'D': return "LEFT"
        return "ESC"
    elif b in ('\n', '\r', '\x0d'):
        return "ENTER"
    elif b.lower() == 'q':
        return "QUIT"
    return b

def choice_menu(title, options, current_index=0):
    """
    Generic arrow-key menu using rich.live.
    Full-width with extra spacing.
    """
    def render_menu(idx):
        table = Table.grid(padding=(1, 1), expand=True)
        table.add_column(justify="left", ratio=1)
        
        for i, opt in enumerate(options):
            label = opt if isinstance(opt, str) else opt.get('label', 'Option')
            if i == idx:
                table.add_row(f"[bold black on cyan]  > {label}  [/bold black on cyan]")
            else:
                table.add_row(f"    {label} ")
        
        return Panel(
            table, 
            title=f"[bold cyan] {title} [/bold cyan]", 
            border_style="blue", 
            expand=True,
            title_align="left",
            padding=(1, 2)
        )

    with raw_mode():
        with Live(render_menu(current_index), console=console, auto_refresh=False, transient=True) as live:
            while True:
                key = get_key()
                if key == "UP":
                    current_index = (current_index - 1) % len(options)
                elif key == "DOWN":
                    current_index = (current_index + 1) % len(options)
                elif key == "ENTER":
                    return current_index
                elif key == "QUIT":
                    return -1
                
                live.update(render_menu(current_index), refresh=True)

def select_video(entries, page=1):
    """
    Video selection menu with thumbnails, arrow-key navigation, and pagination.
    Optimized for stability and to prevent terminal scrolling glitches.
    """
    if not entries:
        rprint("[red]No results found.[/red]")
        return None

    def render_loading():
        return Panel(
            "[bold cyan]Generating thumbnails...[/bold cyan]", 
            title=f"Page {page}", 
            border_style="yellow", 
            expand=True
        )

    # Use Live even for the loading state to keep terminal clean
    with Live(render_loading(), console=console, auto_refresh=False, transient=True) as live:
        cached_thumbs = []
        for entry in entries:
            thumb_url = entry.get('thumbnail')
            if not thumb_url and entry.get('thumbnails'):
                thumb_url = entry.get('thumbnails')[-1].get('url')
            
            if thumb_url:
                # Reduced width to 40 to save vertical space
                cached_thumbs.append(get_ascii_image(thumb_url, width=40))
            else:
                cached_thumbs.append(None)

        # Add navigation entries
        nav_entries = entries.copy()
        if page > 1:
            nav_entries.insert(0, {"title": "[ PREVIOUS PAGE ]", "type": "nav", "action": "prev"})
        nav_entries.append({"title": "[ NEXT PAGE ]", "type": "nav", "action": "next"})

        def render_video_list(idx):
            entry = nav_entries[idx]
            
            if entry.get('type') == 'nav':
                card_content = f"\n[bold green]Navigate to {entry['title']}[/bold green]\n"
                card = Panel(card_content, title=f" Page {page} ", border_style="yellow", expand=True, height=12)
            else:
                title = entry.get('title', 'Unknown')
                uploader = entry.get('uploader', 'Unknown')
                duration = entry.get('duration')
                duration_str = f"{int(duration)//60}:{int(duration)%60:02d}" if duration else "??:??"
                
                meta_table = Table.grid(padding=(0, 1), expand=True)
                meta_table.add_column(justify="left", ratio=1)
                meta_table.add_row(f"[bold yellow]{title}[/bold yellow]")
                meta_table.add_row(f"[cyan]Channel:[/cyan] {uploader}")
                meta_table.add_row(f"[cyan]Duration:[/cyan] {duration_str}")
                
                layout_table = Table.grid(padding=(0, 2), expand=True)
                thumb_idx = idx - (1 if page > 1 else 0)
                thumb = cached_thumbs[thumb_idx] if 0 <= thumb_idx < len(cached_thumbs) else None
                
                if thumb:
                    layout_table.add_column(width=42) 
                    layout_table.add_column(ratio=1)
                    layout_table.add_row(thumb, meta_table)
                else:
                    layout_table.add_row(meta_table)
                    
                # Fixed height Panel helps prevent flickering/scrolling
                card = Panel(
                    layout_table, 
                    title=f" Page {page} | {idx+1}/{len(nav_entries)} ", 
                    border_style="green",
                    expand=True,
                    title_align="left",
                    height=12
                )

            # Results List (Reduced count to 5 for stability)
            list_table = Table.grid(padding=(0, 0), expand=True)
            list_table.add_column(justify="left", ratio=1)
            
            start = max(0, idx - 2)
            end = min(len(nav_entries), start + 5)
            if end == len(nav_entries): start = max(0, end - 5)
            
            for i in range(start, end):
                item_title = nav_entries[i].get('title', 'Unknown')
                if i == idx:
                    list_table.add_row(f"[bold black on green] > {item_title} [/bold black on green]")
                else:
                    list_table.add_row(f"   {item_title}")

            results_panel = Panel(list_table, title=" Results ", border_style="blue", expand=True)

            combined = Table.grid(expand=True)
            combined.add_row(card)
            combined.add_row(results_panel)
            combined.add_row(f"[dim center]↑/↓: Nav | ENTER: Play | a: Add to Playlist | q: Back[/dim center]")
            return combined

        current_index = 1 if page > 1 else 0
        live.update(render_video_list(current_index), refresh=True)
        
        with raw_mode():
            while True:
                key = get_key()
                if key == "UP":
                    current_index = (current_index - 1) % len(nav_entries)
                elif key == "DOWN":
                    current_index = (current_index + 1) % len(nav_entries)
                elif key == "ENTER":
                    entry = nav_entries[current_index]
                    if entry.get('type') == 'nav':
                        return entry
                    return {"type": "play", "entry": entry}
                elif key == "a":
                    entry = nav_entries[current_index]
                    if entry.get('type') != 'nav':
                        return {"type": "add", "entry": entry}
                elif key == "QUIT":
                    return None
                
                live.update(render_video_list(current_index), refresh=True)
