"""Reuse the existing pure geometry replay helpers and local fake transport."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "quadrilaterals"))
