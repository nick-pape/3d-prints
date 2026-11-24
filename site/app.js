import Module from "https://cdn.jsdelivr.net/npm/manifold-3d@3.5.4/manifold.js";
import { makeGeometry, DEFAULTS, BANKS } from "./station.js";
import { stl, threemf, download, bounds, pack } from "./files.js";
import { Viewer } from "./viewer.js";

const $ = (id) => document.getElementById(id);
const status = (t) => { $("status").textContent = t || ""; $("status").hidden = !t; };
// PrusaSlicer on the reference settings (2 perimeters, 15% gyroid): 4-slot + insert = 206 cm3 of model -> 201 g, 3 h 43 min
const G_PER_CM3 = 0.976, MIN_PER_CM3 = 1.08;
const BED = [250, 210];

const viewer = new Viewer($("view"));
let geo, ini = "", current = null, cable = "right";

// ---- inputs ----
function presets(sel, key) {
  for (const [k, b] of Object.entries(BANKS)) sel.add(new Option(`${b.label} (${b.h.toFixed(1)} × ${b.w.toFixed(1)} × ${b.t.toFixed(1)})`, k));
  sel.add(new Option("Custom size", "custom"));
  sel.value = key;
}
presets($("bank"), "zolo20k"); presets($("small"), "zolo10k");
const setDims = (pre, b) => { $(pre + "-h").value = b.h.toFixed(1); $(pre + "-w").value = b.w.toFixed(1); $(pre + "-t").value = b.t.toFixed(1); };
setDims("b", BANKS.zolo20k); setDims("s", BANKS.zolo10k);
for (const [sel, pre] of [["bank", "b"], ["small", "s"]]) {
  $(sel).addEventListener("change", () => { if (BANKS[$(sel).value]) setDims(pre, BANKS[$(sel).value]); schedule(); });
  for (const d of ["h", "w", "t"]) $(`${pre}-${d}`).addEventListener("input", () => { $(sel).value = "custom"; schedule(); });
}
for (const k of ["slots", "clear", "depth", "ins"]) {
  $(k + "-r").addEventListener("input", () => { $(k).value = $(k + "-r").value; schedule(); });
  $(k).addEventListener("input", () => { $(k + "-r").value = $(k).value; schedule(); });
}
document.querySelectorAll("[data-cable]").forEach((b) => b.addEventListener("click", () => {
  cable = b.dataset.cable; document.querySelectorAll("[data-cable]").forEach((x) => x.classList.toggle("on", x === b)); schedule();
}));
$("ghost").addEventListener("change", () => current && show(true));

const num = (id, lo, hi, d) => { const v = parseFloat($(id).value); return Number.isFinite(v) ? Math.min(hi, Math.max(lo, v)) : d; };
function params() {
  const bank = { h: num("b-h", 40, 250, BANKS.zolo20k.h), w: num("b-w", 20, 150, BANKS.zolo20k.w), t: num("b-t", 8, 80, BANKS.zolo20k.t) };
  const small = { h: num("s-h", 30, 250, BANKS.zolo10k.h), w: num("s-w", 15, 150, BANKS.zolo10k.w), t: num("s-t", 5, 80, BANKS.zolo10k.t) };
  const slots = Math.round(num("slots", 1, 8, 4));
  const depth = Math.min(num("depth", 20, 90, 45), bank.h - 15);
  return { ...DEFAULTS, slots, bank, small, clear: num("clear", 0.3, 2.5, 1), depth, cable,
           inserts: Math.min(Math.round(num("ins", 0, 8, 1)), slots) };
}

let timer;
function schedule() {
  const p = params();
  $("slots-out").textContent = p.slots === 1 ? "1 bank" : `${p.slots} banks`;
  $("ins-out").textContent = p.inserts ? `${p.inserts} of ${p.slots} slots` : "none";
  for (const k of ["ins", "ins-r"]) $(k).max = p.slots;
  clearTimeout(timer); timer = setTimeout(run, 150);
}

const stat = (v, label) => `<div class="stat"><b>${v}</b><span>${label}</span></div>`;

function run() {
  if (!geo) return;
  const p = params(), t0 = performance.now();
  let st, ins;
  try {
    st = geo.station(p); ins = geo.insert(p);
  } catch (e) { console.error(e); status("Couldn't build that one: " + e.message); return; }
  const stTris = geo.tris(st.part), insTris = geo.tris(ins.part);
  const vol = st.part.volume() / 1000, ivol = ins.part.volume() / 1000;
  st.part.delete(); ins.part.delete();
  const nIns = ins.ok ? p.inserts : 0;
  current = { p, L: st.layout, stTris, insTris, insOk: ins.ok, nIns };
  show(!!run.shown); run.shown = true; status("");

  const b = bounds(stTris).size, total = vol + nIns * ivol;
  const fits = pack([[b[0], b[1]], ...Array(nIns).fill([bounds(insTris).size[0], bounds(insTris).size[1]])], BED);
  $("stats").innerHTML = [
    stat(`${b[0].toFixed(0)} × ${b[1].toFixed(0)} × ${b[2].toFixed(0)}`, "mm, station"),
    stat(`≈ ${Math.round(total * G_PER_CM3)} g`, `PETG${nIns ? `, with ${nIns} insert${nIns > 1 ? "s" : ""}` : ""}`),
    stat(`≈ ${fmtTime(total * MIN_PER_CM3)}`, "print time (estimate)"),
  ].join("");
  const warn = [];
  if (b[0] > BED[0] || b[1] > BED[1]) warn.push(`The station is bigger than a ${BED[0]} × ${BED[1]} mm bed. Use fewer slots or a bigger printer.`);
  else if (!fits) warn.push("The station and inserts don't all fit on one 250 × 210 mm bed; the 3MF will need a second plate for some inserts.");
  if (p.inserts && !ins.ok) warn.push("The smaller bank isn't smaller than the slot (by at least 2 mm in width and thickness, and in height), so no insert is made.");
  if (params().depth < num("depth", 20, 90, 45)) warn.push(`Slot depth capped at ${p.depth.toFixed(0)} mm (bank height minus 15).`);
  $("warn").hidden = !warn.length; $("warn").textContent = warn.join(" ");
  $("dl-3mf").disabled = $("dl-stl").disabled = false; $("dl-ins").disabled = !ins.ok;
  console.debug(`generated in ${(performance.now() - t0).toFixed(0)} ms`);
}

const fmtTime = (min) => min < 60 ? `${Math.round(min)} min` : `${Math.floor(min / 60)} h ${String(Math.round(min % 60)).padStart(2, "0")} min`;

function show(keepView) {
  const { p, L, stTris, insTris, nIns } = current;
  const parts = [{ tris: stTris }], boxes = [];
  const ghost = $("ghost").checked;
  for (let i = 0; i < p.slots; i++) {
    const yc = L.y0 + i * L.pitch + L.st / 2;
    if (i < nIns) {
      const t = insTris.slice(); for (let k = 0; k < t.length; k += 3) { t[k + 1] += yc; t[k + 2] += p.floor; }
      parts.push({ tris: t, color: "#d9a066" });
      if (ghost) boxes.push({ size: [p.small.w, p.small.t, p.small.h], center: [0, yc, p.floor + p.bank.h - p.small.h / 2], color: "#b9bcc4" });
    } else if (ghost) boxes.push({ size: [p.bank.w, p.bank.t, p.bank.h], center: [0, yc, p.floor + p.bank.h / 2], color: "#8fb8de" });
  }
  viewer.show(parts, boxes, { keepView });
}

const fname = () => { const { p } = current; return `powerbank_station_${p.slots}slot`; };
$("dl-stl").onclick = () => current && download(stl(current.stTris, fname()), fname() + ".stl");
$("dl-ins").onclick = () => current && download(stl(current.insTris, "insert"), `powerbank_station_insert_${current.p.small.h.toFixed(0)}x${current.p.small.w.toFixed(0)}x${current.p.small.t.toFixed(0)}.stl`);
$("dl-3mf").onclick = () => current && download(threemf([
  { name: `station ${current.p.slots} slot`, tris: current.stTris, count: 1 },
  { name: "insert", tris: current.insTris, count: current.nIns },
], ini, BED), fname() + ".3mf");

async function boot() {
  schedule();
  try {
    const [wasm, cfg] = await Promise.all([Module(), fetch("printer.ini").then((r) => (r.ok ? r.text() : ""))]);
    wasm.setup();
    ini = cfg; geo = makeGeometry(wasm);
    status("Generating…");
    run();
  } catch (e) {
    console.error(e); status("Couldn't start the generator: " + e.message);
  }
}
boot();
