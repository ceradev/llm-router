from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def run_migrations() -> None:
    root = _repo_root()
    alembic_ini = root / "alembic.ini"
    if not alembic_ini.is_file():
        raise FileNotFoundError(f"Missing {alembic_ini}")
    env = os.environ.copy()
    py_path = env.get("PYTHONPATH", "")
    extra = f"{root}{os.pathsep}{root / 'apps' / 'server'}"
    env["PYTHONPATH"] = f"{extra}{os.pathsep}{py_path}" if py_path else extra
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(alembic_ini), "upgrade", "head"],
        cwd=str(root),
        check=True,
        env=env,
    )
