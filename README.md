# FreeTubeCLI 📺

A minimalist, high-performance YouTube CLI for watching videos and playlists in your terminal without ads or tracking.


## Features
- **Fast Search**: Instant search for videos and playlists.
- **Ad-Free Playback**: Uses `mpv` for a clean, distraction-free experience.
- **Local Playlists**: Create and manage your own video collections locally.
- **Auto-play**: Keep the vibe going with automatic next-video playback.
- **ASCII Thumbnails**: High-quality terminal image previews.
- **Audio-Only Mode**: Save bandwidth and listen to music/podcasts.
- **Configurable**: Persist your quality preferences and cookie settings.

## Prerequisites
FreeTubeCLI depends on `mpv` for media playback.

- **Linux**: `sudo apt install mpv`
- **macOS**: `brew install mpv`
- **Windows**: [Download mpv](https://mpv.io/installation/) and add to PATH.

## Installation

### From GitHub (Recommended)
```bash
git clone https://github.com/AatishAsh/FreeTubeCLI.git
cd freetube-cli
pip install .
```

### Direct Install
```bash
pip install git+https://github.com/AatishAsh/FreeTubeCLI.git
```

## Usage

Launch the interactive interface:
```bash
freetube-cli
```

One-shot commands:
```bash
# Search and play
freetube-cli "RickRoll"

# Play a specific URL
freetube-cli https://www.youtube.com/watch?v=...

# Audio-only mode
freetube-cli "podcast" --audio-only
```

## Controls

### Navigation
- **`↑/↓`**: Navigate menus and search results.
- **`ENTER`**: Play video or select option.
- **`a`**: Add highlighted video to a playlist.
- **`q`**: Go back or exit.

### During Playback (mpv)
- **`space`**: Pause / Resume.
- **`>`**: Skip to Next.
- **`<`**: Go to Previous.
- **`9 / 0`**: Volume down / up.
- **`f`**: Toggle Fullscreen.
- **`Ctrl+C`**: Stop playback and return to menu.

## License
MIT License - see [LICENSE](LICENSE) for details.
