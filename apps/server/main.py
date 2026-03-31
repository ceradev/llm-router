from __future__ import annotations

import sys
from pathlib import Path

import uvicorn

# Ensure repo-level `packages/` is importable when running from `apps/api`.
repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from app.main import app


def main() -> None:
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
