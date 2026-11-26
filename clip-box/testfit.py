"""Test-fit pieces cut from the real parts: one hinge (base + lid side) and the lock (housing + keeper), plus the
bolt and knob. Assemble them to check the hinge swing and stop, the M3 fits, the bolt travel and the detent click.

    uv run python testfit.py     # out/testfit_*.stl
"""
from pathlib import Path
from build123d import Box, Pos, Rot, Align, export_stl
from box import Params, base, lid

p = Params()
out = Path(__file__).parent / "out"
MIN = (Align.MIN, Align.MIN, Align.MIN)
B, Lp = base(p), lid(p)
x0, x1 = p.hinge_x - 22, p.hinge_x + 22
cuts = {
    "hinge_base": (B, Pos(x0, p.D - 12, p.Hb - 34) * Box(x1 - x0, 40, 50, align=MIN)),
    "hinge_lid": (Lp, Pos(x0, p.D - 12, p.Hb - 10) * Box(x1 - x0, 40, 40, align=MIN)),
    "lock_base": (B, Pos(-22, -15, 12) * Box(44, 27, 60, align=MIN)),
    "lock_lid": (Lp, Pos(-22, -15, p.Hb - 10) * Box(44, 27, 40, align=MIN)),
}
for name, (part, box) in cuts.items():
    s = part & box
    if name.endswith("lid"):   # print upside down like the lid
        s = Rot(180, 0, 0) * s
    bb = s.bounding_box()
    s = Pos(0, 0, -bb.min.Z) * s
    export_stl(s, str(out / f"testfit_{name}.stl"))
    print(f"testfit_{name}: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm, {s.volume / 1000:.1f} cm3")
