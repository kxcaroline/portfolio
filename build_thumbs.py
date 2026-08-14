"""Regenerate the screenshot thumbnails the projects page serves.

The full captures average 40KB and one is 194KB, yet they render in a
172px tile; serving them whole cost roughly a megabyte per page load for
pixels nobody saw. This writes a tile-sized copy of each into
static/images/thumbs, mirroring the folder layout, and the page fetches
the original only when a visitor opens the lightbox.

Run after adding or replacing a screenshot:

    python build_thumbs.py
"""

import json
import shutil
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent / "flask_website" / "static" / "images"
SOURCE = ROOT / "projects"
TARGET = ROOT / "thumbs"
SIZES = Path(__file__).resolve().parent / "flask_website" / "data" / "thumb_sizes.json"

# Twice the rendered tile width, so the thumbnail is still sharp on a
# high-density display. The ratio matches the tile's 16:10 frame.
TILE_WIDTH = 344
TILE_RATIO = 1.6

# Above this height-to-width ratio the tile shows the top of the capture
# rather than the whole thing (see THUMB_TALL_RATIO in pages.py), so only
# that part needs to exist in the thumbnail.
TALL_RATIO = 2.0


def build():
    """Write a thumbnail for every screenshot. Returns (count, bytes saved)."""
    if not SOURCE.is_dir():
        sys.exit(f"no screenshots at {SOURCE}")
    if TARGET.exists():
        shutil.rmtree(TARGET)

    made = source_bytes = thumb_bytes = 0
    sizes = {}
    for path in sorted(SOURCE.rglob("*.webp")):
        image = Image.open(path).convert("RGB")
        width, height = image.size
        if height > width * TALL_RATIO:
            image = image.crop((0, 0, width, round(width / TILE_RATIO)))
        image.thumbnail((TILE_WIDTH, TILE_WIDTH * 6), Image.Resampling.LANCZOS)

        out = TARGET / path.relative_to(SOURCE)
        out.parent.mkdir(parents=True, exist_ok=True)
        image.save(out, "WEBP", quality=80, method=6)

        made += 1
        sizes[str(path.relative_to(SOURCE))] = list(image.size)
        source_bytes += path.stat().st_size
        thumb_bytes += out.stat().st_size

    # The page needs each thumbnail's pixel size to reserve its box before
    # the image loads. Writing it here rather than reading the files at
    # request time keeps Pillow out of the deployed application entirely -
    # it is a build tool, not a runtime dependency.
    SIZES.write_text(json.dumps(sizes, indent=2, sort_keys=True) + "\n",
                     encoding="utf-8")
    return made, source_bytes, thumb_bytes


if __name__ == "__main__":
    count, before, after = build()
    print(f"{count} thumbnails: {before // 1024}KB -> {after // 1024}KB")
