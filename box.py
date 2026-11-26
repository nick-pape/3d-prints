"""Parametric hinged box: four sealed sections, M3 bolt hinges at the back, a turn-to-lock sliding bolt at the front.

Frame: X = across (left -> right), Y = front (0) -> back (D), Z = up. The base sits on the bed open side up,
the lid prints upside down (its top on the bed), the bolt stands up, the knob prints grip-down.

    uv run python box.py        # out/base.stl, out/lid.stl, out/bolt.stl, out/knob.stl

Sealing: the lid carries a ring per section that drops 4 mm into it, so with the lid shut every section is a
closed cup and clips can't hop over a divider when the box is shaken or dropped.

Lock: a round bolt slides up out of a housing on the base front into a keeper on the lid. An M3 screw holds a
knob on the bolt; the knob rides in a slot shaped like a stretched Z, so the bolt is parked by turning the knob
sideways into a notch at the top (locked) or the bottom (open). A small bump at each notch mouth makes it click.
"""
from dataclasses import dataclass
from math import cos, sin, tan, radians, pi
from pathlib import Path

from manifold3d import OpType, JoinType
from build123d import (Align, Axis, Box, Cylinder, Cone, Face, Wire, Pos, Rot, Part, Plane, export_stl,
                       extrude, fillet, chamfer, Vector)

IN = 25.4
C = (Align.CENTER, Align.CENTER, Align.MIN)


@dataclass(frozen=True)
class Params:
    W: float = 186.0            # outside, across
    D: float = 186.0            # outside, front to back (hinge and bolt stick out ~20 mm more; bed is 210 deep)
    Hb: float = 2.0 * IN        # base height
    Hl: float = 12.0            # lid height
    wall: float = 3.6           # 6 lines of a 0.6 nozzle
    floor: float = 3.0
    top: float = 2.4            # lid top plate
    div: float = 3.0            # dividers
    corner_r: float = 10.0      # outside vertical corners
    pocket_r: float = 6.0       # section corners in plan
    pocket_fr: float = 5.0      # section floor round (scoops clips out easily)
    seal: float = 4.0           # lid rings drop this far into each section
    seal_t: float = 2.0         # ring thickness
    seal_c: float = 0.4         # ring -> section wall clearance
    # hinge (one per back corner): base knuckle | lid knuckle | base knuckle on an M3 x 30 bolt + nyloc
    hinge_x: float = 58.0       # hinge centre from the middle
    knuckle_r: float = 5.0
    knuckle_c: float = 0.5      # radial and axial clearance between moving parts
    k_out: float = 11.5         # outer (base) knuckle width
    k_mid: float = 10.0         # middle (lid) knuckle width
    open_deg: float = 102.0     # lid stops here
    stop_l: float = 7.5         # stop block reach behind the hinge axis
    # bolt lock
    bolt_d: float = 8.0
    bolt_l: float = 30.0
    bolt_c: float = 0.3         # bolt -> bore, radial
    bolt_y: float = -3.0        # bolt axis, from the front face
    housing_r: float = 6.8
    engage: float = 8.0         # bolt travel into the keeper
    neck_d: float = 5.0         # knob neck, rides in the slot
    slot_w: float = 5.4
    detent: float = 0.3         # bump per side at each notch mouth
    turn_deg: float = 60.0      # how far the knob turns into a notch
    knob_at: float = 13.0       # knob screw height on the bolt, from its bottom


def _hull(pts):
    pts = sorted(set((round(a, 6), round(b, 6)) for a, b in pts))
    cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]


def _circle(cx, cy, r, n=64):
    return [(cx + r * cos(2 * pi * k / n), cy + r * sin(2 * pi * k / n)) for k in range(n)]


def _yz_prism(pts, x0, x1):
    """Polygon in (y, z), extruded along X from x0 to x1."""
    face = Face(Wire.make_polygon([Vector(x0, y, z) for y, z in pts], close=True))
    return extrude(face, amount=x1 - x0, dir=(1, 0, 0))


def _xy_prism(pts, z0, z1):
    face = Face(Wire.make_polygon([Vector(x, y, z0) for x, y in pts], close=True))
    return extrude(face, amount=z1 - z0, dir=(0, 0, 1))


def _rbox(w, d, h, r, fr=0.0, at=(0, 0, 0)):
    """Box with rounded vertical edges (r) and optionally a rounded bottom (fr), bottom-centred at `at`."""
    b = Box(w, d, h, align=C)
    b = fillet(b.edges().filter_by(Axis.Z), r)
    if fr:
        b = fillet(b.edges().filter_by_position(Axis.Z, -1e-3, 1e-3), fr)
    return Pos(*at) * b


def _try(op, sizes, part, what):
    for s in sizes:
        try:
            return op(s)
        except Exception:
            pass
    print(f"{what} skipped")
    return part


def pockets(p: Params):
    """Centres and size of the four sections."""
    inner = (p.W - 2 * p.wall, p.D - 2 * p.wall)
    pw, pd = (inner[0] - p.div) / 2, (inner[1] - p.div) / 2
    xs = (-(p.div + pw) / 2, (p.div + pw) / 2)
    ys = (p.wall + pd / 2, p.wall + pd + p.div + pd / 2)
    return pw, pd, [(x, y) for x in xs for y in ys]


def hinge_slots(p: Params):
    """[(x0, x1, who)] per knuckle, who = 'base' or 'lid'."""
    g = p.knuckle_c
    out = []
    for xc in (-p.hinge_x, p.hinge_x):
        span = 2 * p.k_out + p.k_mid + 2 * g
        x0 = xc - span / 2
        out += [(x0, x0 + p.k_out, "base"), (x0 + p.k_out + g, x0 + p.k_out + g + p.k_mid, "lid"),
                (x0 + p.k_out + 2 * g + p.k_mid, x0 + span, "base")]
    return out


def _axis(p):
    return p.D + p.knuckle_r, p.Hb          # hinge axis (y, z)


def _lid_hinge_profile(p):
    """(y, z) outline of the lid's hinge block: knuckle + web up to the lid top. The 60 deg flank behind the
    knuckle keeps it printable upside down."""
    ay, az = _axis(p)
    z1 = p.Hb + p.Hl
    return _hull(_circle(ay, az, p.knuckle_r) + [(p.D - 0.2, z1), (ay, z1), (ay, az + 2 * p.knuckle_r)])


def _stop_profile(p):
    """Stop block under the lid knuckle: a block behind the back wall, minus everything the lid's hinge block
    sweeps through from closed to open_deg (+ clearance), so it only touches at open_deg."""
    from manifold3d import CrossSection
    ay, az = _axis(p)
    blk = CrossSection([[(p.D - 0.2, az - 31), (ay + p.stop_l, az - 14), (ay + p.stop_l, az - 0.3), (p.D - 0.2, az - 0.3)]])
    lidp = CrossSection([_lid_hinge_profile(p)]).translate((-ay, -az))
    swept = [lidp.rotate(-a) for a in [x * 0.5 for x in range(int(p.open_deg * 2) + 1)]]
    cut = CrossSection.batch_boolean(swept, OpType.Add).offset(0.3, JoinType.Round).translate((ay, az))
    cut = cut + CrossSection.circle(p.knuckle_r + p.knuckle_c, 64).translate((ay, az))
    return [[tuple(v) for v in poly] for poly in (blk - cut).to_polygons() if len(poly) > 2]


def _lock_z(p):
    zb0 = p.Hb - 0.5 - p.bolt_l             # bore floor: an unlocked bolt's top sits 0.5 under the lid
    travel = p.engage + 0.5
    return zb0, travel, zb0 + p.knob_at, zb0 + p.knob_at + travel   # floor, travel, knob z open / locked


def _housing_plan(p):
    return _hull(_circle(0, p.bolt_y, p.housing_r) + [(-8.0, 0.5), (8.0, 0.5)])


def base(p: Params = Params()) -> Part:
    pw, pd, cs = pockets(p)
    body = _rbox(p.W, p.D, p.Hb, p.corner_r, at=(0, p.D / 2, 0))
    body = _try(lambda r: chamfer(body.edges().filter_by_position(Axis.Z, -1e-3, 1e-3), r), (1.0, 0.6), body, "base bed chamfer")
    body = _try(lambda r: fillet(body.edges().filter_by_position(Axis.Z, p.Hb - 1e-3, p.Hb + 1e-3), r), (1.2, 0.8), body, "base rim round")
    for cx, cy in cs:
        body -= _rbox(pw, pd, p.Hb, p.pocket_r, p.pocket_fr, at=(cx, cy, p.floor))
    # section mouths: lead-in so the lid rings find their way in
    mouth = [e for e in body.edges().filter_by_position(Axis.Z, p.Hb - 1e-3, p.Hb + 1e-3)
             if p.wall - 0.5 < e.center().Y < p.D - p.wall + 0.5 and abs(e.center().X) < p.W / 2 - p.wall + 0.5]
    body = _try(lambda r: chamfer(mouth, r), (0.8, 0.6), body, "section mouth chamfer")

    # hinge blocks behind the back wall
    ay, az = _axis(p)
    kr, g = p.knuckle_r, p.knuckle_c
    t = radians(p.open_deg - 90)
    for x0, x1, who in hinge_slots(p):
        if who == "base":   # knuckle with a 63 deg web down to the back wall
            prof = _hull(_circle(ay, az, kr) + [(p.D - 0.2, az - 21)])
            body += _yz_prism(prof, x0, x1)
        else:                # under the lid knuckle: a stop block the lid's hinge block lands on at open_deg
            for poly in _stop_profile(p):
                body += _yz_prism(poly, x0 + 0.01, x1 - 0.01)
            # room for the lid knuckle in the back wall
            body -= Pos(x0 - g, ay, az) * Rot(0, 90, 0) * Cylinder(kr + g, x1 - x0 + 2 * g, align=C)
    for xc in (-p.hinge_x, p.hinge_x):  # M3: bore, head counterbore on the outer face, nyloc pocket on the inner
        span = 2 * p.k_out + p.k_mid + 2 * g
        x0, x1 = xc - span / 2, xc + span / 2
        body -= Pos(x0 - 1, ay, az) * Rot(0, 90, 0) * Cylinder(1.7, span + 2, align=C)
        body -= Pos(x0 - 1, ay, az) * Rot(0, 90, 0) * Cylinder(3.2, 1 + 3.5, align=C)       # head, 3.5 deep
        hexa = [(ay + 3.3 * cos(pi / 2 + k * pi / 3), az + 3.3 * sin(pi / 2 + k * pi / 3)) for k in range(6)]
        body -= _yz_prism(hexa, x1 - 4.5, x1 + 1)                                           # nyloc, point up

    # bolt housing on the front, 45 deg taper underneath
    zb0, travel, zo, zl = _lock_z(p)
    plan = _housing_plan(p)
    zh = zb0 - 3.0
    body += _xy_prism(plan, zh, p.Hb)
    wedge = _yz_prism([(0.5, zh - 10.5), (0.5, zh + 0.01), (p.bolt_y - p.housing_r - 0.5, zh + 0.01)], -9, 9)
    body += wedge & _xy_prism(plan, zh - 11, zh + 0.01)
    rb = p.bolt_d / 2 + p.bolt_c
    body -= Pos(0, p.bolt_y, zb0) * Cylinder(rb, p.Hb - zb0 + 1, align=C)
    # knob slot: straight run facing the front, a notch turning toward +X at each end
    sw = p.slot_w
    body -= Pos(0, p.bolt_y - 7, zo - sw / 2) * Box(sw, 14, zl - zo + sw, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for zn in (zo, zl):
        for k in range(0, int(p.turn_deg) + 1, 5):
            body -= Pos(0, p.bolt_y, zn) * Rot(0, 0, k) * Pos(0, -7, 0) * Box(sw, 14, sw)
        # detent bumps at the notch mouth (top and bottom edge of the slot), only in the housing wall
        a = radians(p.turn_deg / 2)
        for s in (-1, 1):
            bump = Pos(0, p.bolt_y, zn + s * (sw / 2 + 1.0 - p.detent)) * Rot(0, 0, p.turn_deg / 2) * \
                Pos(0, -(rb + p.housing_r + 1) / 2, 0) * Rot(90, 0, 0) * Cylinder(1.0, p.housing_r + 1 - rb, align=(Align.CENTER, Align.CENTER, Align.CENTER))
            body += (bump & _xy_prism(plan, zb0, p.Hb)) - Pos(0, p.bolt_y, zb0) * Cylinder(rb, p.Hb, align=C)

    # thumb scoops in the front rim, to get a finger under the lid
    for xs in (-50, 50):
        body -= Pos(xs, -1, p.Hb + 6) * Rot(-90, 0, 0) * Cylinder(10, 3.0, align=C)
    return body


def lid(p: Params = Params()) -> Part:
    pw, pd, cs = pockets(p)
    z0, z1 = p.Hb, p.Hb + p.Hl
    body = _rbox(p.W, p.D, p.Hl, p.corner_r, at=(0, p.D / 2, z0))
    body = _try(lambda r: chamfer(body.edges().filter_by_position(Axis.Z, z1 - 1e-3, z1 + 1e-3), r), (2.0, 1.5, 1.0), body, "lid top chamfer")
    body = _try(lambda r: fillet(body.edges().filter_by_position(Axis.Z, z0 - 1e-3, z0 + 1e-3), r), (1.2, 0.8), body, "lid rim round")
    # one sealing ring per section, dropping into it
    ins_o, ins_i = p.seal_c, p.seal_c + p.seal_t
    for cx, cy in cs:
        ring = _rbox(pw - 2 * ins_o, pd - 2 * ins_o, p.seal + 0.5, p.pocket_r - ins_o, at=(cx, cy, z0 - p.seal))
        ring = _try(lambda r: chamfer(ring.edges().filter_by_position(Axis.Z, z0 - p.seal - 1e-3, z0 - p.seal + 1e-3), r), (0.8, 0.6), ring, "ring lead-in")
        body += ring
    for cx, cy in cs:
        cav = _rbox(pw - 2 * ins_i, pd - 2 * ins_i, p.seal + 1 + p.Hl - p.top, p.pocket_r - ins_i, at=(cx, cy, z0 - p.seal - 1))
        cav = _try(lambda r: fillet(cav.edges().filter_by_position(Axis.Z, z1 - p.top - 1e-3, z1 - p.top + 1e-3), r), (3.0, 2.0), cav, "lid pocket round")
        body -= cav

    ay, az = _axis(p)
    kr, g = p.knuckle_r, p.knuckle_c
    for x0, x1, who in hinge_slots(p):
        if who == "lid":
            body += _yz_prism(_lid_hinge_profile(p), x0, x1)
            body -= Pos(x0 - 1, ay, az) * Rot(0, 90, 0) * Cylinder(1.8, x1 - x0 + 2, align=C)
        else:   # room for the base knuckle in the lid's back wall
            body -= Pos(x0 - g, ay, az) * Rot(0, 90, 0) * Cylinder(kr + g, x1 - x0 + 2 * g, align=C)

    # keeper for the bolt, with a lead-in
    zb0, travel, zo, zl = _lock_z(p)
    body += _xy_prism(_housing_plan(p), z0, z1)
    rk = p.bolt_d / 2 + p.bolt_c + 0.1
    top = p.Hb + p.engage + 1.0
    body -= Pos(0, p.bolt_y, z0 - 1) * Cylinder(rk, top - z0 + 1, align=C)
    body -= Pos(0, p.bolt_y, z0 - 0.01) * Cone(rk + 1.5, rk, 1.5, align=C)
    return body


def bolt(p: Params = Params()) -> Part:
    """Stands on the bed. The flat and the tapped hole take the knob's M3 screw."""
    r = p.bolt_d / 2
    b = Cylinder(r, p.bolt_l, align=C)
    b = chamfer(b.edges().filter_by_position(Axis.Z, p.bolt_l - 1e-3, p.bolt_l + 1e-3), 1.5)
    b = chamfer(b.edges().filter_by_position(Axis.Z, -1e-3, 1e-3), 0.6)
    b -= Pos(0, -r - 5 + 0.5, p.knob_at) * Box(10, 10, p.neck_d + 1)           # flat for the knob, 0.5 deep
    b -= Pos(0, 0, p.knob_at) * Rot(90, 0, 0) * Cylinder(1.3, 2 * r + 2)         # M3 pilot, self-taps
    return b


def knob(p: Params = Params()) -> Part:
    """Neck through the slot + grip, along +Z from the bolt flat. Exported flipped to print grip-down."""
    reach = p.housing_r + 4.5 - (p.bolt_d / 2 - 0.5)       # from the bolt flat to clear the housing
    grip_l, grip_d = 8.0, 10.0
    k = Cylinder(p.neck_d / 2, reach, align=C) + Pos(0, 0, reach) * Cylinder(grip_d / 2, grip_l, align=C)
    k = _try(lambda r: chamfer(k.edges().filter_by_position(Axis.Z, reach + grip_l - 1e-3, reach + grip_l + 1e-3), r), (0.8, 0.5), k, "knob end chamfer")
    k = _try(lambda r: fillet(k.edges().filter_by_position(Axis.Z, reach - 1e-3, reach + 1e-3), r), (1.5, 1.0), k, "grip round")
    k -= Cylinder(1.7, reach + grip_l + 1, align=C)
    k -= Pos(0, 0, reach + grip_l - 5.5) * Cylinder(3.2, 6, align=C)              # screw head (M3 x 16)
    return k


def main():
    p = Params()
    out = Path(__file__).parent / "out"
    out.mkdir(exist_ok=True)
    for name, part in (("base", base(p)), ("lid", lid(p)), ("bolt", bolt(p)), ("knob", knob(p))):
        if name in ("lid", "knob"):   # print upside down
            part = Pos(0, 0, part.bounding_box().max.Z) * Rot(180, 0, 0) * part
        bb = part.bounding_box()
        export_stl(part, str(out / f"{name}.stl"))
        print(f"{name}: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm, {part.volume / 1000:.1f} cm3")


if __name__ == "__main__":
    main()
