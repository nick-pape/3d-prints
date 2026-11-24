// three.js preview: the station (Z up, mm) on a print bed, optionally with ghost power banks in the slots.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();

export class Viewer {
  constructor(el) {
    this.el = el;
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    el.appendChild(this.renderer.domElement);
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(35, 1, 1, 5000);
    this.camera.up.set(0, 0, 1);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.scene.add(new THREE.HemisphereLight(0xffffff, 0x445566, 1.5));
    const sun = new THREE.DirectionalLight(0xffffff, 1.7); sun.position.set(-250, -400, 600); this.scene.add(sun);
    const fill = new THREE.DirectionalLight(0xffffff, 0.5); fill.position.set(300, 200, -100); this.scene.add(fill);
    this.group = new THREE.Group(); this.bed = new THREE.Group();
    this.scene.add(this.group, this.bed);
    new ResizeObserver(() => this.resize()).observe(el);
    this.resize();
    const loop = () => { this.controls.update(); this.renderer.render(this.scene, this.camera); requestAnimationFrame(loop); };
    loop();
  }

  resize() {
    const w = this.el.clientWidth, h = this.el.clientHeight || 1;
    this.renderer.setSize(w, h, false); this.camera.aspect = w / h; this.camera.updateProjectionMatrix();
  }

  mesh(tris, color, opacity = 1, edges = true) {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(tris, 3));
    g.computeVertexNormals();
    const m = new THREE.MeshStandardMaterial({ color, roughness: 0.55, metalness: 0, flatShading: true,
      transparent: opacity < 1, opacity, depthWrite: opacity >= 1 });
    const out = new THREE.Group(); out.add(new THREE.Mesh(g, m));
    if (edges) out.add(new THREE.LineSegments(new THREE.EdgesGeometry(g, 30),
      new THREE.LineBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.16 })));
    return out;
  }

  // parts: [{tris, color?, opacity?}], boxes: [{size:[x,y,z], center:[x,y,z], color}] (ghost banks)
  show(parts, boxes = [], { keepView = false } = {}) {
    this.group.clear();
    const part = css("--part") || "#e8892f";
    for (const p of parts) this.group.add(this.mesh(p.tris, p.color || part, p.opacity ?? 1));
    for (const b of boxes) {
      const geo = new THREE.BoxGeometry(...b.size);
      const m = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color: b.color, roughness: 0.4, transparent: true, opacity: 0.55, depthWrite: false }));
      m.position.set(...b.center); this.group.add(m);
      const e = new THREE.LineSegments(new THREE.EdgesGeometry(geo), new THREE.LineBasicMaterial({ color: b.color }));
      e.position.copy(m.position); this.group.add(e);
    }
    const box = new THREE.Box3().setFromObject(this.group), size = box.getSize(new THREE.Vector3());
    this.bed.clear();
    const bed = new THREE.Mesh(new THREE.BoxGeometry(250, 210, 2),
      new THREE.MeshStandardMaterial({ color: css("--wall") || "#8a9099", roughness: 0.9, transparent: true, opacity: 0.35 }));
    const c = box.getCenter(new THREE.Vector3());
    bed.position.set(c.x, c.y, -1.05); this.bed.add(bed);
    const grid = new THREE.GridHelper(250, 25, 0x888888, 0x777777); grid.rotation.x = Math.PI / 2;
    grid.scale.z = 210 / 250; grid.position.set(c.x, c.y, 0.02); this.bed.add(grid);
    const r = size.length();
    const same = this.frameR && Math.abs(r / this.frameR - 1) < 0.25;
    if (!(keepView && same)) this.frame();
  }

  frame() {
    const b = new THREE.Box3().setFromObject(this.group), c = b.getCenter(new THREE.Vector3()), r = b.getSize(new THREE.Vector3()).length();
    this.frameR = r;
    this.camera.position.copy(c).add(new THREE.Vector3(-0.9, -1.25, 0.95).normalize().multiplyScalar(r * 1.55));
    this.controls.target.copy(c); this.controls.update();
  }
}
