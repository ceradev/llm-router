from __future__ import annotations

import sys
from pathlib import Path

# Make repo root importable so tests can import repo-level `packages/`.
repo_root = Path(__file__).resolve().parents[3]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

