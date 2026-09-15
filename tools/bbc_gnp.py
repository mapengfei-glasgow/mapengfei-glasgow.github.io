#!/usr/bin/env python3
"""Backwards-compatible wrapper: downloads the latest BBC Global News Podcast.

The actual implementation now lives in bbc_podcast.py, which handles
multiple BBC shows. This file is kept so older calls/scripts keep working:

    python3 bbc_gnp.py [DOWNLOAD_DIR]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bbc_podcast  # noqa: E402


if __name__ == "__main__":
    sys.exit(bbc_podcast.entry(["global-news", *sys.argv[1:]]))
