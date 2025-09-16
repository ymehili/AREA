"""Server app Python startup adjustments forwarding to repo root patch."""

from pathlib import Path
import runpy

_root_sitecustomize = Path(__file__).resolve().parents[1] / "sitecustomize.py"
if _root_sitecustomize.exists():
    runpy.run_path(_root_sitecustomize)
