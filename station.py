"""Parametric charging station: power banks stand ports-up in a row of leaning, file-folder style slots.

Frame: X = across the station (bank width), Y = front -> back (slots stack this way), Z = up.
Sized for the Anker Zolo 20,000 mAh 30 W (built-in USB-C); `insert()` adapts a slot to the 10,000 mAh model.

    uv run python station.py              # writes out/station_{1..6}.stl and out/insert_10k.stl
"""
from dataclasses import dataclass
from math import cos, sin, tan, radians
from pathlib import Path

from build123d import (Align, Axis, Box, Cylinder, Location, Plane, Polyline, Pos, Rot, Part, export_stl,
                       extrude, fillet, chamfer, make_face, Select)

IN = 25.4


@dataclass(frozen=True)
class Bank:
    h: float   # long side, stands vertical
    w: float   # across the station
    t: float   # thickness, slots stack along this


ZOLO_20K = Bank(4.72 * IN, 2.89 * IN, 1.24 * IN)   # 119.9 x 73.4 x 31.5 mm, 270 g
ZOLO_10K = Bank(4.32 * IN, 2.58 * IN, 0.98 * IN)   # 109.7 x 65.5 x 24.9 mm, 212 g


@dataclass(frozen=True)
class Params:
    slots: int = 4
    bank: Bank = ZOLO_20K
    clear: float = 1.0          # per side, bank -> slot (2 mm total)
    depth: float = 45.0         # how far the bank sits in its slot (along the lean)
    lean: float = 8.0           # deg, slots tip back so banks rest on the back wall
    floor: float = 2.4          # under the deepest point of a slot
    wall: float = 3.0           # outer walls
    div: float = 2.6            # between slots (4 lines of a 0.6 nozzle)
    cable: str = "right"        # cable box side: "left", "right" or "none"
    cable_w: float = 24.0       # inside width of the cable box
    hole_d: float = 16.0        # one per slot, passes a USB-C plug
    roof: float = 2.4           # top of the cable box
    arch_r: float = 8.0         # cable box ceiling: walls curve in on this radius, then 45 deg to the top
    entry_h: float = 28.0       # cable entry at the back (width = cable_w - 2)
    entry_r: float = 4.0        # its corner radius
    corner_r: float = 6.0       # outer leaning corners
    slot_r: float = 5.0         # slot corners in plan (the banks have soft corners)
    floor_r: float = 2.5        # slot floor to wall
    rim_r: float = 1.0          # every top edge (dividers are 2.4 thick)
    push_d: float = 22.0        # push-out hole in each slot floor, fits a finger
    push_lead: float = 2.0      # its chamfer at the bed
    mouth_lead: float = 1.0     # slot mouth chamfer (dividers are 2.6 thick)


def slot_size(p: Params):
    b = p.bank
    return b.w + 2 * p.clear, b.t + 2 * p.clear


def _try(op, sizes, part, what):
    """Apply an edge op at the first size that works; geometry stays valid if none does."""
    for r in sizes:
        try:
            return op(r)
        except Exception:
            pass
    print(f"{what} skipped")
    return part


def _near_circle(e, xc, ycs, r, tol=0.6):
    """Edge lies on a vertical cylinder of radius r around (xc, yc) for one of ycs."""
    pts = [e.position_at(u) for u in (0.0, 0.5, 1.0)]
    return any(all(abs(((q.X - xc) ** 2 + (q.Y - yc) ** 2) ** 0.5 - r) < tol for q in pts) for yc in ycs)


def station(p: Params = Params()) -> Part:
    a = radians(p.lean)
    sw, st = slot_size(p)
    zb = p.floor + st * sin(a)                       # front-bottom corner of a slot
    H = zb + p.depth * cos(a)                        # top of the block
    pitch = (st + p.div) / cos(a)
    y0 = p.wall / cos(a) + zb * tan(a)               # first slot's front-bottom, wall measured square to the lean
    back_bottom = y0 + (p.slots - 1) * pitch + st * cos(a) - p.floor * tan(a) + p.wall / cos(a)
    t = tan(a)
    xs = [-sw / 2 - p.wall, sw / 2 + p.wall]
    if p.cable == "right":
        xs[1] += p.cable_w + p.wall
    elif p.cable == "left":
        xs[0] -= p.cable_w + p.wall
    # side profile (YZ): parallelogram leaning back with the slots, extruded across X
    prof = Polyline((0, 0), (back_bottom, 0), (back_bottom + H * t, H), (H * t, H), close=True)
    body = extrude(Plane.YZ.offset(xs[0]) * make_face(prof), amount=xs[1] - xs[0])
    # the four leaning outer corners, and a small chamfer on the bed edge against elephant's foot
    corner = [e for e in body.edges() if abs(e.tangent_at(0).X) < 1e-6 and abs(e.tangent_at(0).Z) > 0.5]
    body = fillet(corner, p.corner_r)
    body = chamfer(body.edges().filter_by_position(Axis.Z, -1e-3, 1e-3), 0.6)
    # slots: rounded corners and floor
    for i in range(p.slots):
        cut = Box(sw, st, p.depth + 80, align=(Align.CENTER, Align.MIN, Align.MIN))
        cut = fillet(cut.edges().filter_by(Axis.Z), p.slot_r)
        cut = fillet(cut.edges().filter_by_position(Axis.Z, -1e-3, 1e-3), p.floor_r)
        body -= Pos(0, y0 + i * pitch, zb) * (Rot(-p.lean, 0, 0) * cut)
        # push-out hole through the floor, under the middle of the slot
        yc = y0 + i * pitch + st / 2 * cos(a)
        push = Cylinder(p.push_d / 2, zb + 4, align=(Align.CENTER, Align.CENTER, Align.MIN))
        body -= Pos(0, yc, -1) * push
    # cable box: closed void along one side, a round hole up beside each slot, a big entry at the back
    if p.cable in ("left", "right"):
        sgn = 1 if p.cable == "right" else -1
        x_in = sw / 2 + p.wall                          # inner face of the void (shared wall with the slots)
        xc = sgn * (x_in + p.cable_w / 2)
        # straight (non-leaning) tunnel along Y, ends placed so the leaning front/back walls stay >= wall thick
        zf, zt = p.floor, H - p.roof
        y_a = (p.wall + 1.0) / cos(a) + zt * t
        y_b = back_bottom - (p.wall + 1.0) / cos(a) + zf * t
        # cross-section: teardrop arch, vertical walls curving into 45 deg slopes to a 2 mm flat -> no bridging
        hw, R, flat = p.cable_w / 2, p.arch_r, 1.0
        cc = 0.414 * R + hw - flat                       # height of the arch above where it springs
        zs = zt - cc
        arc = [(hw - R + R * cos(radians(d)), zs + R * sin(radians(d))) for d in range(0, 46, 5)]
        right = [(hw, zf)] + arc + [(flat, zt)]
        pts = [(xc + x, z) for x, z in right] + [(xc - x, z) for x, z in reversed(right)]
        sec = make_face(Polyline(*pts, close=True))
        void = extrude(Plane.XZ * sec, amount=y_b - y_a)
        vb = void.bounding_box()
        void = Pos(0, y_a - vb.min.Y, 0) * void
        void = _try(lambda r: fillet(void.edges().filter_by_position(Axis.Z, zf - 1e-3, zf + 1e-3), r), (3.0, 2.0), void, "void floor round")
        body -= void
        for i in range(p.slots):                          # hole level with the middle of each slot's mouth
            yh = y0 + i * pitch + (H - zb) * t + st / (2 * cos(a))
            body -= Pos(xc, yh, zs - 1) * Cylinder(p.hole_d / 2, p.roof + cc + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
        # back entry: rounded rectangle flush with the void floor, its outer edge rounded too
        ew, eh = p.cable_w - 2, p.entry_h
        ent = Box(ew, 40, eh, align=(Align.CENTER, Align.CENTER, Align.MIN))
        ent = fillet(ent.edges().filter_by(Axis.Y), p.entry_r)
        body -= Pos(xc, back_bottom + (zf + eh / 2) * t, zf) * ent
        on_back = lambda v: abs(v.Y - (back_bottom + v.Z * t)) < 0.05 and abs(v.X - xc) < ew / 2 + 0.1 and v.Z < zf + eh + 0.1
        lip = [e for e in body.edges() if all(on_back(v) for v in e.vertices()) and e.center().Z > 0.5]
        for r in (2.0, 1.5, 1.0):
            try:
                body = fillet(lip, r); break
            except Exception:
                try:   # the bottom edge sits flush with the void floor; round the rest
                    body = fillet([e for e in lip if e.center().Z > zf + 0.5], r); break
                except Exception:
                    pass
        else:
            print("entry round skipped")
    # push-out holes: lead-in where the finger goes in (45 deg chamfer prints fine at the bed)
    holes = [e for e in body.edges().filter_by_position(Axis.Z, -1e-3, 1e-3)
             if e.geom_type.name == "CIRCLE" and abs(e.radius - p.push_d / 2) < 0.01]
    body = _try(lambda r: chamfer(holes, r), (p.push_lead, 1.5, 1.0), body, "push-out lead-in")
    # USB-C holes: lead-in from the void below (a 45 deg cone in a 45 deg ceiling, still no bridging)
    if p.cable in ("left", "right"):
        under = [e for e in body.edges() if zt - cc - 0.5 < e.center().Z < H - p.roof + 0.01 and
                 abs(e.center().X - xc) < p.hole_d / 2 + 0.6 and
                 any(abs(e.center().Y - (y0 + i * pitch + (H - zb) * t + st / (2 * cos(a)))) < p.hole_d / 2 + 0.6 for i in range(p.slots))
                 and abs(((e.center().X - xc) ** 2 + 0) ** 0.5) >= 0 and e.length > 3]
        under = [e for e in under if _near_circle(e, xc, [y0 + i * pitch + (H - zb) * t + st / (2 * cos(a)) for i in range(p.slots)], p.hole_d / 2)]
        if under:
            body = _try(lambda r: chamfer(under, r), (1.5, 1.0, 0.6), body, f"USB-C hole underside lead-in ({len(under)} edges)")
        else:
            print("USB-C hole underside: no edges found")
    # top: round the outer rim, then lead-in chamfers on every slot mouth and USB-C hole
    x0, x1, yfr, ybk = xs[0], xs[1], H * t, back_bottom + H * t
    outer_d = lambda c: min(c.X - x0, x1 - c.X, c.Y - yfr, ybk - c.Y)
    at_top = lambda: [e for e in body.edges() if all(abs(v.Z - H) < 1e-3 for v in e.vertices())]
    body = _try(lambda r: fillet([e for e in at_top() if outer_d(e.center()) < 2.0], r), (p.rim_r, 0.8, 0.5), body, "outer rim round")
    is_hole = lambda e: e.geom_type.name == "CIRCLE" and abs(e.radius - p.hole_d / 2) < 0.01
    mouths = [e for e in at_top() if outer_d(e.center()) >= 2.0 and not is_hole(e)]
    body = _try(lambda r: chamfer(mouths, r), (p.mouth_lead, 0.8, 0.6), body, "slot mouth lead-in")
    body = _try(lambda r: chamfer([e for e in at_top() if is_hole(e)], r), (1.5, 1.0), body, "USB-C hole lead-in")
    return body


def insert(p: Params = Params(), small: Bank = ZOLO_10K, fit: float = 0.4, rim: float = 3.0,
           plate: float = 2.0) -> Part:
    """Drop-in sleeve that holds a smaller bank in a slot, its top level with where the big bank's would be."""
    sw, st = slot_size(p)
    ow, ot = sw - 2 * fit, st - 2 * fit
    iw, it = small.w + 2 * p.clear, small.t + 2 * p.clear
    riser = p.bank.h - small.h
    h = p.depth - 1.0                 # finishes just under the slot rim
    s = Box(ow, ot, h, align=(Align.CENTER, Align.CENTER, Align.MIN))
    s = fillet(s.edges().filter_by(Axis.Z), p.slot_r - fit)
    s = chamfer(s.edges().filter_by_position(Axis.Z, -1e-3, 1e-3), 1.5)      # lead-in into the slot
    cav = Box(iw, it, h, align=(Align.CENTER, Align.CENTER, Align.MIN))
    cav = fillet(cav.edges().filter_by(Axis.Z), 4.0)
    cav = fillet(cav.edges().filter_by_position(Axis.Z, -1e-3, 1e-3), 1.5)
    s -= Pos(0, 0, riser) * cav
    # hollow riser, closed by a bottom plate so a finger through the station's push-out hole lifts the whole insert
    hole = Box(iw - 2 * rim, it - 2 * rim, riser - plate + 1, align=(Align.CENTER, Align.CENTER, Align.MIN))
    s -= Pos(0, 0, plate) * fillet(hole.edges().filter_by(Axis.Z), 3.0)
    top = lambda: [e for e in s.edges() if all(abs(v.Z - h) < 1e-3 for v in e.vertices())]
    inner = lambda e: abs(e.center().X) < iw / 2 + 0.05 and abs(e.center().Y) < it / 2 + 0.05
    s = fillet([e for e in top() if not inner(e)], 0.8)
    s = chamfer([e for e in top() if inner(e)], 1.2)                          # lead-in for the bank
    return s


if __name__ == "__main__":
    out = Path(__file__).parent / "out"
    out.mkdir(exist_ok=True)
    for n in range(1, 7):
        part = station(Params(slots=n))
        bb = part.bounding_box()
        export_stl(part, str(out / f"station_{n}.stl"))
        print(f"station_{n}: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm, {part.volume / 1000:.0f} cm3")
    ins = insert()
    export_stl(ins, str(out / "insert_10k.stl"))
    bb = ins.bounding_box()
    print(f"insert_10k: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm, {ins.volume / 1000:.0f} cm3")
