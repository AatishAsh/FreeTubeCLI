import sys
import io
import urllib.request
from PIL import Image
from rich.text import Text
from rich.style import Style

# Global cache for ASCII art
# Format: {url: rich.text.Text}
IMAGE_CACHE = {}

def get_ascii_image(url, width=40):
    """
    Downloads an image and converts it to Half-Block ASCII art.
    Includes in-memory caching to prevent redundant processing.
    """
    if url in IMAGE_CACHE:
        return IMAGE_CACHE[url]

    try:
        # 1. Download image with a User-Agent to avoid blocks
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            img_data = response.read()
        
        img = Image.open(io.BytesIO(img_data)).convert("RGB")
        
        # 2. Aspect Ratio Correction
        original_width, original_height = img.size
        aspect_ratio = original_height / original_width
        height = int(width * aspect_ratio)
        
        if height % 2 != 0:
            height += 1
            
        img = img.resize((width, height), Image.Resampling.LANCZOS)
        pixels = img.load()
        
        result = Text()
        
        # 3. Half-Block Technique with Style objects
        for y in range(0, height, 2):
            for x in range(width):
                r1, g1, b1 = pixels[x, y]
                r2, g2, b2 = pixels[x, y+1]
                
                fg = f"#{r1:02x}{g1:02x}{b1:02x}"
                bg = f"#{r2:02x}{g2:02x}{b2:02x}"
                
                result.append("▀", style=Style(color=fg, bgcolor=bg))
            result.append("\n")
            
        IMAGE_CACHE[url] = result
        return result
    except Exception as e:
        return Text(f"[Image Error: {e}]", style="red")
