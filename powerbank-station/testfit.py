"""Thin test-fit slices: the top of the 1-slot station and the top of the 10K insert, sitting flat on the bed.
They carry the real outlines and lead-in chamfers, so a bank / insert dropping through them tells you the fit.

    uv run python testfit.py [height_mm]     # out/testfit_station.stl, out/testfit_insert.stl
"""
import sys
from pathlib import Path
from build123d import Plane, Keep, Pos, export_stl
from station import Params, station, insert

H = float(sys.argv[1]) if len(sys.argv) > 1 else 8.0
out = Path(__file__).parent / "out"
for name, part in (("station", station(Params(slots=1))), ("insert", insert(Params()))):
    top = part.bounding_box().max.Z
    s = part.split(Plane.XY.offset(top - H), keep=Keep.TOP)
    s = Pos(0, 0, -(top - H)) * s
    bb = s.bounding_box()
    export_stl(s, str(out / f"testfit_{name}.stl"))
    print(f"testfit_{name}: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm, {s.volume / 1000:.1f} cm3")
