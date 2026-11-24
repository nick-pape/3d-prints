import Module from "manifold-3d";
import { makeGeometry, DEFAULTS } from "./station.js";
import { threemf } from "./files.js";
import { readFileSync, writeFileSync } from "fs";
const wasm = await Module(); wasm.setup();
const g = makeGeometry(wasm);
const p = { ...DEFAULTS, slots: 4 };
const blob = threemf([{ name: "station 4 slot", tris: g.tris(g.station(p).part), count: 1 },
                      { name: "insert", tris: g.tris(g.insert(p).part), count: 2 }], readFileSync("../tools/petg_hf06.ini", "utf8"));
writeFileSync("../out/_tmp/web.3mf", Buffer.from(await blob.arrayBuffer()));
console.log("wrote", blob.size);
