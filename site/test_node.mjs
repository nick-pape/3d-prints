// node test: build every size, check manifold status, print bbox + volume (compare with station.py)
import Module from "manifold-3d";
import { makeGeometry, DEFAULTS } from "./station.js";
import { writeFileSync, mkdirSync } from "fs";
const wasm = await Module(); wasm.setup();
const g = makeGeometry(wasm);
const t0 = performance.now();
for (let n = 1; n <= 6; n++) {
  const { part } = g.station({ ...DEFAULTS, slots: n });
  const b = part.boundingBox();
  if (part.status() !== "NoError" || part.volume() <= 0) { console.error(`station_${n} failed: ${part.status()}`); process.exit(1); }
  console.log(`station_${n}: ${(b.max[0]-b.min[0]).toFixed(1)} x ${(b.max[1]-b.min[1]).toFixed(1)} x ${(b.max[2]-b.min[2]).toFixed(1)} mm, ${(part.volume()/1000).toFixed(1)} cm3, status ${part.status()}, genus ${part.genus()}, ${part.numTri()} tris`);
}
const ins = g.insert(DEFAULTS);
const b = ins.part.boundingBox();
console.log(`insert: ${(b.max[0]-b.min[0]).toFixed(1)} x ${(b.max[1]-b.min[1]).toFixed(1)} x ${(b.max[2]-b.min[2]).toFixed(1)} mm, ${(ins.part.volume()/1000).toFixed(1)} cm3, ok ${ins.ok}`);
console.log(`total ${(performance.now()-t0).toFixed(0)} ms`);
// STL of the 4-slot for a visual check
const tr = g.tris(g.station({ ...DEFAULTS, slots: 4 }).part);
const buf = Buffer.alloc(84 + tr.length / 9 * 50); buf.writeUInt32LE(tr.length / 9, 80);
for (let i = 0; i < tr.length / 9; i++) for (let k = 0; k < 9; k++) buf.writeFloatLE(tr[i * 9 + k], 84 + i * 50 + 12 + k * 4);
mkdirSync("../out/_tmp", { recursive: true }); writeFileSync("../out/_tmp/web_station_4.stl", buf);
const ti = g.tris(ins.part); const bi = Buffer.alloc(84 + ti.length / 9 * 50); bi.writeUInt32LE(ti.length / 9, 80);
for (let i = 0; i < ti.length / 9; i++) for (let k = 0; k < 9; k++) bi.writeFloatLE(ti[i * 9 + k], 84 + i * 50 + 12 + k * 4);
writeFileSync("../out/_tmp/web_insert.stl", bi);
