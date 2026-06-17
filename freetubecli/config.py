import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".freetube"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "quality": "1080",
    "audio_only": False,
    "auto_play": True,
    "cookies": None
}

def load_config():
    """Loads configuration from ~/.freetube/config.json."""
    if not CONFIG_FILE.exists():
        return DEFAULT_CONFIG.copy()
    
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            # Merge with defaults to ensure all keys exist
            return {**DEFAULT_CONFIG, **config}
    except Exception as e:
        print(f"Error loading config: {e}")
        return DEFAULT_CONFIG.copy()

def save_config(config_data):
    """Saves configuration to ~/.freetube/config.json."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(config_data, f, indent=4)
    except Exception as e:
        print(f"Error saving config: {e}")
