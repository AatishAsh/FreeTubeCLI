import os
import shutil
import yt_dlp
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, DownloadColumn, TransferSpeedColumn
from rich import print as rprint
from rich.panel import Panel

def download_media(entry, audio_only=False, cookies=None, quiet=False):
    """
    Downloads the selected video or audio using yt-dlp.
    Shows a premium Rich progress bar with speed, size, and ETA unless quiet is True.
    """
    if isinstance(entry, str):
        entry = {'title': entry, 'url': entry, 'id': entry}
        
    url = entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}"
    title = entry.get('title', 'Video')
    
    # Save in a local Downloads folder
    download_dir = os.path.join(os.getcwd(), "Downloads")
    os.makedirs(download_dir, exist_ok=True)
    
    outtmpl = os.path.join(download_dir, '%(title)s.%(ext)s')
    
    ydl_opts = {
        'outtmpl': outtmpl,
        'quiet': True,
        'no_warnings': True,
    }
    
    # Apply cookies if present
    if cookies:
        if "/" in cookies or "." in cookies:
            ydl_opts['cookiefile'] = cookies
        else:
            ydl_opts['cookiesfrombrowser'] = (cookies,)

    has_ffmpeg = shutil.which("ffmpeg") is not None
    
    if audio_only:
        if has_ffmpeg:
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
            if not quiet:
                rprint("[cyan]FFmpeg detected. Will convert audio to MP3 format.[/cyan]")
        else:
            ydl_opts.update({
                'format': 'bestaudio/best',
            })
            if not quiet:
                rprint("[yellow]FFmpeg not found. Downloading audio in its native format to skip conversion...[/yellow]")
                rprint("[dim]Tip: Install 'ffmpeg' on your system to enable auto-conversion to MP3.[/dim]")
    else:
        ydl_opts.update({
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
        })
        if not has_ffmpeg and not quiet:
            rprint("[yellow]Warning: FFmpeg not found. High-quality streams might download video & audio separately.[/yellow]")
            rprint("[dim]Tip: Install 'ffmpeg' to allow merging video and audio into a single MP4.[/dim]")

    if not quiet:
        rprint(f"\n[bold cyan]Preparing download for:[/bold cyan] [bold yellow]{title}[/bold yellow]")

        # Custom Rich Progress Bar
        with Progress(
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(bar_width=40),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            transient=True
        ) as progress:
            task_desc = "Downloading Audio..." if audio_only else "Downloading Video..."
            task = progress.add_task(task_desc, total=None)
            
            def progress_hook(d):
                if d['status'] == 'downloading':
                    total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                    downloaded = d.get('downloaded_bytes') or 0
                    if total > 0:
                        progress.update(task, total=total, completed=downloaded)
                    else:
                        progress.update(task, completed=downloaded)
                elif d['status'] == 'finished':
                    progress.update(task, description="Finished downloading!")
                    
            ydl_opts['progress_hooks'] = [progress_hook]
            
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                rprint(f"[bold green]✓ Successfully downloaded to:[/bold green] [underline]{download_dir}[/underline]")
                from .playlist import add_to_playlist
                add_to_playlist("Downloaded", entry)
                import time; time.sleep(1.5)
            except Exception as e:
                rprint(f"[bold red]✗ Download failed:[/bold red] {e}")
                input("\nPress Enter to continue...")
    else:
        # Quiet download for background execution
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            from .playlist import add_to_playlist
            add_to_playlist("Downloaded", entry)
        except Exception:
            pass
