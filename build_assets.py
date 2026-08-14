"""Write minified siblings of the stylesheet and the script.

The readable files stay the ones in the repository and the ones a reader
opens; the minified copies are what the running site serves (see ``asset``
in flask_website/__init__.py). Run after editing either source:

    python build_assets.py

A minified file older than its source is ignored at serve time, so
forgetting to run this costs a larger download and nothing else.
"""

from __future__ import annotations

from pathlib import Path

import rcssmin
import rjsmin

STATIC = Path(__file__).resolve().parent / "flask_website" / "static"
TARGETS = [
    (STATIC / "css" / "style.css", rcssmin.cssmin),
    (STATIC / "js" / "scrollspy.js", rjsmin.jsmin),
]


def main() -> None:
    """Minify each target beside itself and report the saving."""
    for source, minify in TARGETS:
        if not source.exists():
            print(f"skipped (missing): {source.name}")
            continue
        text = source.read_text(encoding="utf-8")
        out = source.with_suffix(f".min{source.suffix}")
        # Trailing newline: POSIX defines a text file as ending in one, and
        # the end-of-file-fixer pre-commit hook rewrites files that do not -
        # which would fail the commit on every rebuild. Harmless in both CSS
        # and JavaScript.
        out.write_text(minify(text) + "\n", encoding="utf-8")
        before, after = len(text), out.stat().st_size
        print(f"{source.name:16} {before / 1024:6.1f}KB -> "
              f"{after / 1024:5.1f}KB  ({100 - after * 100 // before}% smaller)")


if __name__ == "__main__":
    main()
