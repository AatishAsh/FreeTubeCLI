import subprocess
import sys
from rich import print as rprint

def play_media(media_url, audio_only=False, cookies=None, quality="1080"):
    """
    Play the media using mpv.
    media_url can be a direct stream URL or a YouTube URL.
    """
    cmd = ["mpv", media_url]
    
    if audio_only:
        cmd.append("--no-video")
    else:
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

def play_queue(entries, audio_only=False, cookies=None, quality="1080"):
    """Play a list of entries sequentially in a single mpv instance for native navigation."""
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

    cmd = ["mpv"] + urls
    
    if audio_only:
        cmd.append("--no-video")
    else:
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
