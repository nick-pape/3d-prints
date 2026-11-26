// Power bank station geometry for the browser (and node), built with manifold-3d.
// A port of station.py for upright slots (lean = 0). Rounds and chamfers are made as convex hulls of stacked
// rounded-rectangle layers, so every cutter stays convex and every result is a closed, manifold solid.
//
// Frame: X = across the station (bank width), Y = front -> back (slots stack along Y), Z = up. Mesh in mm.

export const IN = 25.4;
export const BANKS = {
  zolo20k: { label: "Anker Zolo 20,000 mAh 30 W", h: 4.72 * IN, w: 2.89 * IN, t: 1.24 * IN },
  zolo10k: { label: "Anker Zolo 10,000 mAh", h: 4.32 * IN, w: 2.58 * IN, t: 0.98 * IN },
};

export const DEFAULTS = {
  slots: 4,
  bank: { ...BANKS.zolo20k },
  clear: 1.0,        // per side, bank -> slot
  depth: 45.0,       // how deep the bank sits
  floor: 2.4,
  wall: 3.0,
  div: 2.6,          // 4 lines of a 0.6 nozzle
  cable: "right",    // "left", "right" or "none"
  cable_w: 24.0,
  hole_d: 16.0,
  roof: 2.4,
  arch_r: 8.0,
  entries: ["front", "back"],   // cable entries into the box
  entry_h: 28.0,     // to the tip of its pointed top
  entry_r: 4.0,
  corner_r: 6.0,
  slot_r: 5.0,
  floor_r: 2.5,
  rim_r: 1.0,
  push_d: 22.0,
  push_lead: 2.0,
  mouth_lead: 1.0,
  // insert
  small: { ...BANKS.zolo10k },
  fit: 0.4,          // insert -> slot, per side
  ins_rim: 3.0,
  plate: 2.0,
};

const SEG = 64;            // segments for a full circle on holes
const ARC = 6;             // layers per quarter round in hulls

export function makeGeometry(wasm) {
  const { Manifold, CrossSection } = wasm;

  // rounded rectangle centred on (cx, cy); r is clamped so it always stays valid
  const rrect = (w, d, r, cx = 0, cy = 0) => {
    r = Math.max(0.01, Math.min(r, w / 2 - 0.01, d / 2 - 0.01));
    return CrossSection.square([w - 2 * r, d - 2 * r], true).offset(r, "Round", 2, SEG).translate([cx, cy]);
  };
  const pts3 = (cs, z) => cs.toPolygons().flat().map(([x, y]) => [x, y, z]);

  // solid through a list of [inset, z] layers of a rounded rectangle (inset > 0 shrinks, < 0 grows).
  // Each pair of neighbouring layers is a convex frustum; their union follows the profile exactly, including
  // a flare above a straight wall (a single hull would bridge straight across that).
  const loft = (w, d, r, layers, cx = 0, cy = 0) => {
    const ring = layers.map(([ins, z]) => pts3(rrect(w - 2 * ins, d - 2 * ins, r - ins, cx, cy), z));
    const parts = [];
    for (let i = 0; i + 1 < ring.length; i++) parts.push(Manifold.hull([...ring[i], ...ring[i + 1]]));
    return parts.length === 1 ? parts[0] : Manifold.union(parts);
  };

  // quarter-round as layers: inset goes rad -> 0 while z goes z0 -> z0 + rad (bottom fillet), or the mirror for a top
  const roundUp = (rad, z0) => Array.from({ length: ARC + 1 }, (_, k) => {
    const a = (k / ARC) * Math.PI / 2; return [rad * (1 - Math.sin(a)), z0 + rad * (1 - Math.cos(a))];
  });
  const roundDown = (rad, z1) => Array.from({ length: ARC + 1 }, (_, k) => {
    const a = (k / ARC) * Math.PI / 2; return [rad * (1 - Math.cos(a)), z1 - rad + rad * Math.sin(a)];
  });

  const cyl = (r0, r1, z0, z1, x, y) => Manifold.cylinder(z1 - z0, r0, r1, SEG).translate([x, y, z0]);

  function layout(p) {
    const sw = p.bank.w + 2 * p.clear, st = p.bank.t + 2 * p.clear;
    const H = p.floor + p.depth, pitch = st + p.div, y0 = p.wall;
    const back = y0 + (p.slots - 1) * pitch + st + p.wall;
    const xs = [-sw / 2 - p.wall, sw / 2 + p.wall];
    if (p.cable === "right") xs[1] += p.cable_w + p.wall;
    if (p.cable === "left") xs[0] -= p.cable_w + p.wall;
    const sgn = p.cable === "left" ? -1 : 1;
    const xc = sgn * (sw / 2 + p.wall + p.cable_w / 2);
    return { sw, st, H, pitch, y0, back, xs, xc };
  }

  function station(p) {
    const L = layout(p), { sw, st, H, pitch, y0, back, xs, xc } = L;
    const W = xs[1] - xs[0], cx = (xs[0] + xs[1]) / 2, cy = back / 2;
    // outer block: rounded corners, 0.6 chamfer at the bed, rounded top rim
    let body = loft(W, back, p.corner_r, [[0.6, 0], [0, 0.6], ...roundDown(p.rim_r, H)], cx, cy);
    const cuts = [];
    for (let i = 0; i < p.slots; i++) {
      const yc = y0 + i * pitch + st / 2;
      // slot: rounded floor, straight walls, lead-in chamfer at the mouth
      cuts.push(loft(sw, st, p.slot_r, [...roundUp(p.floor_r, p.floor), [0, H - p.mouth_lead],
        [-p.mouth_lead, H], [-p.mouth_lead, H + 1]], 0, yc));
      // push-out hole with a chamfer at the bed
      cuts.push(cyl(p.push_d / 2, p.push_d / 2, -1, p.floor + 1, 0, yc));
      cuts.push(cyl(p.push_d / 2 + p.push_lead + 1, p.push_d / 2, -1, p.push_lead, 0, yc));
    }
    if (p.cable === "left" || p.cable === "right") {
      const zf = p.floor, zt = H - p.roof, hw = p.cable_w / 2, R = p.arch_r, flat = 1.0, fr = 3.0;
      const cc = 0.414 * R + hw - flat, zs = zt - cc;
      // cross-section (x, z): rounded floor corners, vertical walls, arch curving into 45 deg up to a 2 mm flat
      const half = [];
      for (let k = 0; k <= ARC; k++) { const a = (k / ARC) * Math.PI / 2; half.push([hw - fr + fr * Math.sin(a), zf + fr - fr * Math.cos(a)]); }
      for (let d = 0; d <= 45; d += 5) { const a = d * Math.PI / 180; half.push([hw - R + R * Math.cos(a), zs + R * Math.sin(a)]); }
      half.push([flat, zt]);
      const poly = [...half.map(([x, z]) => [x, z]), ...half.slice().reverse().map(([x, z]) => [-x, z])];
      const ya = p.wall + 1, yb = back - p.wall - 1;
      const sec = CrossSection.ofPolygons([poly]);
      cuts.push(sec.extrude(yb - ya).rotate([90, 0, 0]).translate([xc, yb, 0]));   // extrusion runs along -Y
      for (let i = 0; i < p.slots; i++) {
        const yh = y0 + i * pitch + st / 2, r = p.hole_d / 2;
        cuts.push(cyl(r, r, zs - 1, H + 1, xc, yh));
        cuts.push(cyl(r, r + 2.5, H - 1.5, H + 1, xc, yh));                     // lead-in at the top
        cuts.push(cyl(r + 1.5, r, zt - 7, zt - 5.5, xc, yh));                    // lead-in from the void below
      }
      // cable entries (front and/or back): flush with the void floor, rounded bottom corners, straight sides,
      // a 45 deg pointed top to a 2 mm flat (nothing bridges), and a 2 mm 45 deg flare at the outer face
      const ehw = (p.cable_w - 2) / 2, eh = p.entry_h, fl = 2.0;
      const ring = (hw, top, y) => {
        const r = p.entry_r, half = [];
        for (let k = 0; k <= ARC; k++) { const a = (k / ARC) * Math.PI / 2; half.push([hw - r + r * Math.sin(a), zf + r - r * Math.cos(a)]); }
        half.push([hw, top - (hw - 1)], [1, top]);
        return [...half, ...half.map(([x, z]) => [-x, z])].map(([x, z]) => [xc + x, y, z]);
      };
      for (const end of p.entries || ["front", "back"]) {
        const [face, inw] = end === "back" ? [back, -1] : [0, 1];
        cuts.push(Manifold.hull([...ring(ehw, zf + eh, face + inw * (p.wall + 3)), ...ring(ehw, zf + eh, face - inw)]));
        cuts.push(Manifold.hull([...ring(ehw, zf + eh, face + inw * fl), ...ring(ehw + fl, zf + eh + fl, face),
          ...ring(ehw + fl, zf + eh + fl, face - inw)]));
      }
    }
    body = body.subtract(Manifold.union(cuts));
    return { part: body, layout: L };
  }

  function insert(p) {
    const sw = p.bank.w + 2 * p.clear, st = p.bank.t + 2 * p.clear;
    const ow = sw - 2 * p.fit, ot = st - 2 * p.fit;
    const iw = p.small.w + 2 * p.clear, it = p.small.t + 2 * p.clear;
    const riser = Math.max(p.plate + 1, p.bank.h - p.small.h), h = p.depth - 1.0;
    let s = loft(ow, ot, p.slot_r - p.fit, [[1.5, 0], [0, 1.5], ...roundDown(0.8, h)]);
    const cav = loft(iw, it, 4.0, [...roundUp(1.5, riser), [0, h - 1.2], [-1.2, h], [-1.2, h + 1]]);
    const hole = loft(iw - 2 * p.ins_rim, it - 2 * p.ins_rim, 3.0, [[0, p.plate], [0, riser + 0.5]]);
    s = s.subtract(cav).subtract(hole);
    return { part: s, ok: iw < ow - 2 && it < ot - 2 && p.small.h < p.bank.h };
  }

  // triangle soup (Float32Array, xyz per vertex) for the viewer and the STL / 3MF writers
  function tris(m) {
    const mesh = m.getMesh(), np = mesh.numProp, v = mesh.vertProperties, t = mesh.triVerts;
    const out = new Float32Array(t.length * 3);
    for (let i = 0; i < t.length; i++) { const o = t[i] * np; out[i * 3] = v[o]; out[i * 3 + 1] = v[o + 1]; out[i * 3 + 2] = v[o + 2]; }
    return out;
  }

  return { station, insert, tris, layout };
}
