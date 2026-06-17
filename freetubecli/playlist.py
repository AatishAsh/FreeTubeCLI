import json
import os
from pathlib import Path

PLAYLIST_DIR = Path.home() / ".freetube"
PLAYLIST_FILE = PLAYLIST_DIR / "playlists.json"

def load_playlists():
    """Loads playlists from ~/.freetube/playlists.json."""
    if not PLAYLIST_FILE.exists():
        return {}
    
    try:
        with open(PLAYLIST_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading playlists: {e}")
        return {}

def save_playlists(playlists):
    """Saves playlists to ~/.freetube/playlists.json."""
    try:
        PLAYLIST_DIR.mkdir(parents=True, exist_ok=True)
        with open(PLAYLIST_FILE, "w") as f:
            json.dump(playlists, f, indent=4)
    except Exception as e:
        print(f"Error saving playlists: {e}")

def add_to_playlist(playlist_name, video_entry):
    """Adds a video entry to a specific playlist."""
    playlists = load_playlists()
    if playlist_name not in playlists:
        playlists[playlist_name] = []
    
    # Avoid duplicates based on ID
    video_id = video_entry.get('id')
    if video_id and any(v.get('id') == video_id for v in playlists[playlist_name]):
        return False, "Video already in playlist."
        
    playlists[playlist_name].append(video_entry)
    save_playlists(playlists)
    return True, f"Added to {playlist_name}."

def delete_playlist(playlist_name):
    """Deletes a playlist."""
    playlists = load_playlists()
    if playlist_name in playlists:
        del playlists[playlist_name]
        save_playlists(playlists)
        return True
    return False

def get_playlist_names():
    """Returns a list of all playlist names."""
    playlists = load_playlists()
    return list(playlists.keys())
