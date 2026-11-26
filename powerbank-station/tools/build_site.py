"""Assemble the static GitHub Pages site into _site/ (the generator page + the PrusaSlicer config it embeds).

    uv run python tools/build_site.py && python -m http.server -d _site 8000
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_site"
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir()
for f in ("index.html", "app.js", "station.js", "files.js", "viewer.js", "style.css"):
    shutil.copy2(ROOT / "site" / f, OUT / f)
shutil.copy2(ROOT / "tools/petg_hf06.ini", OUT / "printer.ini")
(OUT / ".nojekyll").write_text("")
print("built", OUT)
