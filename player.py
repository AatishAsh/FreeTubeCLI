import subprocess
import sys

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

def play_queue(urls, audio_only=False, cookies=None, quality="1080"):
    """Play a list of URLs sequentially."""
    for url in urls:
        print(f"Playing: {url}")
        res = play_media(url, audio_only, cookies, quality)
        if res != 0:
            print(f"Playback stopped or failed with code {res}")
            break
    return 0
