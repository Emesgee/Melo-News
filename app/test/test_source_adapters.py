"""
Tests for source adapters (RSS, Reddit).
Twitter/X adapter was removed from the pipeline.
"""
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest


# ─── Helper: dummy location filter ───────────────────────────────────
def _dummy_filter(text):
    """Simple filter that matches 'gaza' or 'rafah' in text."""
    if not text:
        return None, None
    lower = text.lower()
    for city in ['gaza', 'rafah', 'jenin', 'nablus']:
        if city in lower:
            return city, city
    return None, None

