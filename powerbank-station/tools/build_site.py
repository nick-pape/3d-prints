"""Assemble the generator page + the PrusaSlicer config it embeds into a static directory (default _site/).
The Pages workflow builds it into the repo's _site/powerbank-station/.

    uv run python tools/build_site.py && python -m http.server -d _site 8000
"""
import shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "_site"
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)
for f in ("index.html", "app.js", "station.js", "files.js", "viewer.js", "style.css"):
    shutil.copy2(ROOT / "site" / f, OUT / f)
shutil.copy2(ROOT / "tools/petg_hf06.ini", OUT / "printer.ini")
(OUT / ".nojekyll").write_text("")
print("built", OUT)
