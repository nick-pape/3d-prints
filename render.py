"""Preview renders: station with banks in the slots, and the parts as printed.  uv run python render.py"""
import sys
from math import cos, sin, tan, radians
from pathlib import Path
import numpy as np, trimesh
from build123d import export_stl
from station import Params, station, insert, slot_size, ZOLO_10K

OUT = Path(__file__).parent / "out"; TMP = OUT / "_tmp"; TMP.mkdir(parents=True, exist_ok=True)
ORANGE, BANK, BANK2 = [235, 137, 47, 255], [196, 220, 238, 255], [225, 225, 228, 255]

def tm(part, name):
    f = TMP / f"{name}.stl"; export_stl(part, str(f)); return trimesh.load(f)

def bank_mesh(b, r=6.0):
    m = trimesh.creation.box(extents=[b.w - 0.01, b.t - 0.01, b.h - 0.01])
    try:
        import trimesh.creation as c
        m = c.box(extents=[b.w - 2 * r, b.t, b.h]).union(c.box(extents=[b.w, b.t, b.h - 2 * r]))
    except Exception:
        pass
    m.apply_translation([0, b.t / 2, b.h / 2]); return m

def placed(p, i, mesh, lift=0.0):
    a = radians(p.lean); sw, st = slot_size(p)
    zb = p.floor + st * sin(a); pitch = (st + p.div) / cos(a); y0 = p.wall / cos(a) + zb * tan(a)
    m = mesh.copy(); m.apply_translation([0, p.clear, lift])
    m.apply_transform(trimesh.transformations.rotation_matrix(-a, [1, 0, 0]))
    m.apply_translation([0, y0 + i * pitch, zb]); return m

def shot(meshes, path, angles, dist=1.3, res=(1400, 1050)):
    s = trimesh.Scene()
    for m, col in meshes:
        m = m.copy(); m.visual.face_colors = col; s.add_geometry(m)
    s.set_camera(angles=np.radians(angles), distance=s.scale * dist, center=s.centroid)
    path.write_bytes(s.save_image(resolution=res, visible=True, background=[236, 234, 228, 255]))

p = Params(slots=int(sys.argv[1]) if len(sys.argv) > 1 else 4)
st_m = tm(station(p), "st"); ins = tm(insert(p), "ins")
big, small = bank_mesh(p.bank), bank_mesh(ZOLO_10K)
sw, stt = slot_size(p)
items = [(st_m, ORANGE)]
for i in range(p.slots):
    if i == 1:   # one slot shows the 10K in its insert
        fit = 0.3; ins_m = ins.copy(); ins_m.apply_translation([0, stt / 2 - p.clear, 0])
        items.append((placed(p, i, ins_m, 0), ORANGE))
        items.append((placed(p, i, small, p.bank.h - ZOLO_10K.h).apply_translation([0, 0, 0]) if False else
                      placed(Params(**{**p.__dict__, "clear": p.clear + (stt - ZOLO_10K.t - 2 * p.clear) / 2}), i, small, p.bank.h - ZOLO_10K.h), BANK2))
    else:
        items.append((placed(p, i, big), BANK))
shot(items, OUT / f"render_{p.slots}_loaded.png", (68, 0, 215), dist=1.2)
shot([(st_m, ORANGE)], OUT / f"render_{p.slots}_empty.png", (55, 0, 210), dist=1.5)
i2 = ins.copy(); i2.apply_translation([st_m.bounds[1][0] - i2.bounds[0][0] + 15, 0, 0])
shot([(st_m, ORANGE), (i2, ORANGE)], OUT / f"render_{p.slots}_parts.png", (50, 0, 150), dist=1.4)
print("ok")
