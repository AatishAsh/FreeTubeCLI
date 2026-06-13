import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich import print as rprint
from image import get_ascii_image

console = Console()

def select_video(entries):
    """
    Present a list of videos to the user with thumbnails and return selection.
    Uses 'rich' for a beautiful TUI.
    """
    if not entries:
        rprint("[red]No results found.[/red]")
        return None

    rprint("\n[bold cyan]Search Results:[/bold cyan]\n")
    
    for i, entry in enumerate(entries, 1):
        title = entry.get('title', 'Unknown Title')
        duration = entry.get('duration')
        duration_str = f"{int(duration)//60}:{int(duration)%60:02d}" if duration else "??:??"
        uploader = entry.get('uploader', 'Unknown Uploader')
        
        # Get thumbnail URL robustly
        thumbnail_url = entry.get('thumbnail')
        if not thumbnail_url and entry.get('thumbnails'):
            thumbnail_url = entry.get('thumbnails')[-1].get('url') # Get highest quality available
        
        # Create Metadata text
        meta_table = Table.grid(padding=(0, 1))
        meta_table.add_row(f"[bold yellow]{i}. {title}[/bold yellow]")
        meta_table.add_row(f"[cyan]Channel:[/cyan] {uploader}")
        meta_table.add_row(f"[cyan]Duration:[/cyan] {duration_str}")
        meta_table.add_row(f"[dim]ID: {entry.get('id')}[/dim]")

        if thumbnail_url:
            # Get ASCII Thumbnail
            thumbnail = get_ascii_image(thumbnail_url, width=30)
            
            # Combine Thumbnail and Metadata in a layout
            layout_table = Table.grid(padding=(0, 2))
            layout_table.add_row(thumbnail, meta_table)
            panel = Panel(layout_table, expand=False, border_style="blue")
        else:
            panel = Panel(meta_table, expand=False, border_style="blue")
            
        console.print(panel)

    rprint(f"\n[bold green]{len(entries) + 1}. [Cancel][/bold green]")

    while True:
        try:
            choice = console.input(f"\n[bold white]Select a video (1-{len(entries) + 1}): [/bold white]")
            if not choice.strip():
                continue
            
            idx = int(choice)
            if idx == len(entries) + 1:
                return None
            if 1 <= idx <= len(entries):
                return entries[idx - 1]
            else:
                rprint(f"[red]Please enter a number between 1 and {len(entries) + 1}.[/red]")
        except ValueError:
            rprint("[red]Invalid input. Please enter a number.[/red]")
        except (KeyboardInterrupt, EOFError):
            rprint("\n[yellow]Cancelled.[/yellow]")
            return None
