// STL and PrusaSlicer 3MF writers for triangle soups (Float32Array, xyz per vertex, mm, Z up).

export function stl(tris, name = "part") {
  const n = tris.length / 9, buf = new ArrayBuffer(84 + 50 * n), dv = new DataView(buf);
  new TextEncoder().encodeInto(name.slice(0, 79), new Uint8Array(buf, 0, 80));
  dv.setUint32(80, n, true);
  for (let t = 0; t < n; t++) {
    const o = 84 + 50 * t, v = tris.subarray(9 * t, 9 * t + 9);
    const ux = v[3] - v[0], uy = v[4] - v[1], uz = v[5] - v[2], wx = v[6] - v[0], wy = v[7] - v[1], wz = v[8] - v[2];
    let nx = uy * wz - uz * wy, ny = uz * wx - ux * wz, nz = ux * wy - uy * wx; const l = Math.hypot(nx, ny, nz) || 1;
    [nx / l, ny / l, nz / l, ...v].forEach((x, k) => dv.setFloat32(o + 4 * k, x, true));
  }
  return new Blob([buf], { type: "model/stl" });
}

export function bounds(tris) {
  const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
  for (let i = 0; i < tris.length; i += 3) for (let k = 0; k < 3; k++) { const x = tris[i + k]; if (x < lo[k]) lo[k] = x; if (x > hi[k]) hi[k] = x; }
  return { lo, hi, size: [hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]] };
}

function indexed(tris) {
  const key = new Map(), verts = [], faces = [];
  for (let i = 0; i < tris.length; i += 9) {
    const f = [];
    for (let k = 0; k < 9; k += 3) {
      const x = tris[i + k], y = tris[i + k + 1], z = tris[i + k + 2], s = `${x.toFixed(4)},${y.toFixed(4)},${z.toFixed(4)}`;
      let id = key.get(s); if (id === undefined) { id = verts.length; key.set(s, id); verts.push([x, y, z]); }
      f.push(id);
    }
    if (f[0] !== f[1] && f[1] !== f[2] && f[0] !== f[2]) faces.push(f);
  }
  return { verts, faces };
}

const CRC = (() => { const t = new Uint32Array(256); for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
const crc32 = (b) => { let c = 0xffffffff; for (const x of b) c = CRC[(c ^ x) & 255] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; };

function zip(files) {                                       // stored (no compression) zip
  const enc = new TextEncoder(), parts = [], central = []; let off = 0;
  for (const [name, text] of files) {
    const n = enc.encode(name), d = typeof text === "string" ? enc.encode(text) : text, c = crc32(d);
    const h = new DataView(new ArrayBuffer(30));
    h.setUint32(0, 0x04034b50, true); h.setUint16(4, 20, true); h.setUint32(14, c, true);
    h.setUint32(18, d.length, true); h.setUint32(22, d.length, true); h.setUint16(26, n.length, true);
    parts.push(h.buffer, n, d);
    const e = new DataView(new ArrayBuffer(46));
    e.setUint32(0, 0x02014b50, true); e.setUint16(4, 20, true); e.setUint16(6, 20, true); e.setUint32(16, c, true);
    e.setUint32(20, d.length, true); e.setUint32(24, d.length, true); e.setUint16(28, n.length, true); e.setUint32(42, off, true);
    central.push(e.buffer, n);
    off += 30 + n.length + d.length;
  }
  const size = central.reduce((s, x) => s + x.byteLength, 0), end = new DataView(new ArrayBuffer(22));
  end.setUint32(0, 0x06054b50, true); end.setUint16(8, files.length, true); end.setUint16(10, files.length, true);
  end.setUint32(12, size, true); end.setUint32(16, off, true);
  return new Blob([...parts, ...central, end.buffer], { type: "model/3mf" });
}

// Shelf-pack footprints [w, d] onto the bed with a gap; returns centres, or null if they don't fit.
export function pack(sizes, bed = [250, 210], gap = 6) {
  const order = sizes.map((s, i) => i).sort((a, b) => sizes[b][1] - sizes[a][1]);
  const pos = []; let x = gap, y = gap, row = 0;
  for (const i of order) {
    const [w, d] = sizes[i];
    if (x + w > bed[0] - gap) { x = gap; y += row + gap; row = 0; }
    pos[i] = [x + w / 2, y + d / 2]; x += w + gap; row = Math.max(row, d);
  }
  if (y + row > bed[1] - gap || sizes.some(([w, d]) => w > bed[0] - 2 * gap || d > bed[1] - 2 * gap)) return null;
  const dy = (bed[1] - (y + row + gap)) / 2;
  return pos.map(([cx, cy]) => [cx, cy + dy]);
}

// objects: [{name, tris, count}] -> a PrusaSlicer project with each object instanced `count` times, packed on the bed.
// ini: PrusaSlicer config ("key = value" lines), embedded so the project opens with those print settings.
export function threemf(objects, ini, bed = [250, 210]) {
  const objs = objects.filter((o) => o.count > 0).map((o) => {
    const b = bounds(o.tris), c = [(b.lo[0] + b.hi[0]) / 2, (b.lo[1] + b.hi[1]) / 2, b.lo[2]];
    return { ...o, b, c, mesh: indexed(o.tris) };
  });
  const sizes = objs.flatMap((o) => Array(o.count).fill([o.b.size[0], o.b.size[1]]));
  const where = pack(sizes, bed) || sizes.map((_, i) => [bed[0] / 2 + i * 10, bed[1] / 2]);
  const esc = (s) => s.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
  let res = "", items = "", cfg = '<?xml version="1.0" encoding="UTF-8"?>\n<config>', k = 0;
  objs.forEach((o, j) => {
    const id = j + 1, [cx, cy, z0] = o.c;
    const vx = o.mesh.verts.map(([x, y, z]) => `<vertex x="${(x - cx).toFixed(4)}" y="${(y - cy).toFixed(4)}" z="${(z - z0).toFixed(4)}"/>`).join("");
    const tr = o.mesh.faces.map(([a, b, c]) => `<triangle v1="${a}" v2="${b}" v3="${c}"/>`).join("");
    res += `<object id="${id}" name="${esc(o.name)}" type="model"><mesh><vertices>${vx}</vertices><triangles>${tr}</triangles></mesh></object>`;
    for (let n = 0; n < o.count; n++, k++) items += `<item objectid="${id}" transform="1 0 0 0 1 0 0 0 1 ${where[k][0].toFixed(3)} ${where[k][1].toFixed(3)} 0" printable="1"/>`;
    cfg += `<object id="${id}" instances_count="${o.count}"><metadata type="object" key="name" value="${esc(o.name)}"/>`
      + `<volume firstid="0" lastid="${o.mesh.faces.length - 1}"><metadata type="volume" key="name" value="${esc(o.name)}"/>`
      + '<metadata type="volume" key="volume_type" value="ModelPart"/></volume></object>';
  });
  cfg += "</config>";
  const model = '<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" xmlns:slic3rpe="http://schemas.slic3r.org/3mf/2017/06">'
    + `<metadata name="slic3rpe:Version3mf">1</metadata><resources>${res}</resources><build>${items}</build></model>`;
  const conf = "; generated by the powerbank-station web generator\n" + ini.split(/\r?\n/).filter((l) => l && !l.startsWith("#")).map((l) => `; ${l}\n`).join("");
  return zip([
    ["[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>'],
    ["_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'],
    ["3D/3dmodel.model", model],
    ["Metadata/Slic3r_PE.config", conf],
    ["Metadata/Slic3r_PE_model.config", cfg],
  ]);
}

export function download(blob, filename) {
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = filename;
  document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 5000);
}
