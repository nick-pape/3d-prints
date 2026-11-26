"""Preview renders.  uv run python render.py   -> out/render_*.png"""
from math import radians
from pathlib import Path
import numpy as np, trimesh
from trimesh.transformations import rotation_matrix as R, translation_matrix as T
from box import Params, _axis, _lock_z

p = Params()
OUT = Path(__file__).parent / "out"
L = lambda n: trimesh.load(OUT / f"{n}.stl")
base, lid0, bolt0, knob0 = L("base"), L("lid"), L("bolt"), L("knob")
lid0.apply_transform(T([0, 0, p.Hb + p.Hl]) @ R(np.pi, [1, 0, 0]))
knob0.apply_transform(R(np.pi, [1, 0, 0])); knob0.apply_translation([0, 0, -knob0.bounds[0, 2]])   # undo print flips
ay, az = _axis(p)
zb0, travel, zo, zl = _lock_z(p)
BASE, LID, METAL = [96, 170, 190, 255], [235, 160, 190, 255], [90, 90, 96, 255]


def lock(locked):
    dz, turn = (travel if locked else 0.0), p.turn_deg
    b = bolt0.copy(); b.apply_translation([0, p.bolt_y, zb0 + dz])
    k = knob0.copy(); k.apply_transform(R(np.pi / 2, [1, 0, 0]))
    k.apply_translation([0, p.bolt_y - (p.bolt_d / 2 - 0.5), zb0 + p.knob_at + dz])
    for m in (b, k):
        m.apply_transform(R(radians(turn), [0, 0, 1], [0, p.bolt_y, 0]))
    return [(b, METAL), (k, METAL)]


def lid(deg):
    m = lid0.copy(); m.apply_transform(R(-radians(deg), [1, 0, 0], [0, ay, az])); return m


def shot(items, name, angles, dist=1.5, center=None, res=(1400, 1050)):
    s = trimesh.Scene()
    for m, col in items:
        m = m.copy(); m.visual.face_colors = col; s.add_geometry(m)
    s.set_camera(angles=np.radians(angles), distance=s.scale * dist, center=s.centroid if center is None else center)
    (OUT / f"render_{name}.png").write_bytes(s.save_image(resolution=res, visible=True, background=[240, 238, 233, 255]))


shot([(base, BASE), (lid(0), LID)] + lock(True), "closed", (62, 0, 20))
shot([(base, BASE), (lid(100), LID)] + lock(False), "open", (55, 0, 200), dist=1.4)
shot([(base, BASE)] + lock(False), "base", (50, 0, 20), dist=1.3)
shot([(base, BASE), (lid(0), LID)] + lock(True), "lock", (78, 0, 8), dist=0.32, center=[0, -8, p.Hb - 6])
shot([(base, BASE), (lid(0), LID)] + lock(False), "unlocked", (78, 0, 8), dist=0.32, center=[0, -8, p.Hb - 6])
shot([(base, BASE), (lid(100), LID)], "hinge", (70, 0, 140), dist=0.35, center=[p.hinge_x, p.D + 5, p.Hb])
print("ok")
