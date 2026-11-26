"""Motion check: swing the lid on its hinge and look for collisions with the base; check the bolt and knob in
both parked positions.  uv run python check.py"""
from math import radians, cos, sin
import numpy as np, trimesh
from trimesh.transformations import rotation_matrix as R, translation_matrix as T
from box import Params, _axis, _lock_z

p = Params()
L = lambda n: trimesh.load(f"out/{n}.stl")
base, lid, bolt, knob = L("base"), L("lid"), L("bolt"), L("knob")
# undo the lid's print flip: z -> Hb + Hl - z, y -> -y
lid.apply_transform(T([0, 0, p.Hb + p.Hl]) @ R(np.pi, [1, 0, 0]))
knob.apply_transform(R(np.pi, [1, 0, 0])); knob.apply_translation([0, 0, -knob.bounds[0, 2]])   # undo print flips
ay, az = _axis(p)


def clash(a, b):
    i = trimesh.boolean.intersection([a, b], engine="manifold")
    return 0.0 if i.is_empty else i.volume


print("lid closed vs base:", round(clash(base, lid), 2), "mm3")
for deg in (20, 45, 70, 90, 98, 101, 103, 106, 110):
    m = lid.copy(); m.apply_transform(R(-radians(deg), [1, 0, 0], [0, ay, az]))
    print(f"lid open {deg:>3} deg vs base: {clash(base, m):8.2f} mm3")

zb0, travel, zo, zl = _lock_z(p)
for name, dz, turn in (("open", 0.0, p.turn_deg), ("locked", travel, p.turn_deg), ("locked, knob in the straight run", travel, 0)):
    b = bolt.copy(); b.apply_translation([0, p.bolt_y, zb0 + dz])
    # knob: built along +Z from the bolt flat; lay it along -Y (out the front), then turn it into the notch
    k = knob.copy()
    k.apply_transform(R(np.pi / 2, [1, 0, 0]))                  # +Z -> -Y
    k.apply_translation([0, p.bolt_y - (p.bolt_d / 2 - 0.5), zb0 + p.knob_at + dz])
    k.apply_transform(R(radians(turn), [0, 0, 1], [0, p.bolt_y, 0]))
    b.apply_transform(R(radians(turn), [0, 0, 1], [0, p.bolt_y, 0]))
    print(f"{name}: bolt vs base {clash(base, b):.2f}, bolt vs lid {clash(lid, b):.2f}, knob vs base {clash(base, k):.2f} mm3")
