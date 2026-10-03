"use client";

import { ContactShadows, Environment, Float, Lightformer, useGLTF } from "@react-three/drei";
import { Canvas, useFrame } from "@react-three/fiber";
import { gsap } from "gsap";
import { Suspense, useEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { useOnScreen } from "./useOnScreen";

const MODEL = "/models/nidhinetra-emblem.glb";

/**
 * The NidhiNetra emblem in 3D, modelled in Blender (public/models/nidhinetra-emblem.glb): the
 * Sansad dome and colonnade, the eye, the sweep and the circuit traces. Materials are set here so
 * the brand colours live in one place; the iris follows the pointer; `scroll` (0..1) turns it.
 */

const C = {
  navy: "#0b2560",
  navy2: "#173f94",
  wall: "#eef4fc",
  white: "#ffffff",
  pupil: "#061537",
  teal: "#0ab4a8",
};

function gradientColors(geo: THREE.BufferGeometry, stops: [number, string][], axis: (p: THREE.Vector3) => number) {
  const pos = geo.attributes.position as THREE.BufferAttribute;
  const v = new THREE.Vector3();
  let lo = Infinity;
  let hi = -Infinity;
  const ts: number[] = [];
  for (let i = 0; i < pos.count; i++) {
    v.fromBufferAttribute(pos, i);
    const t = axis(v);
    ts.push(t);
    lo = Math.min(lo, t);
    hi = Math.max(hi, t);
  }
  const cols = stops.map(([s, c]) => [s, new THREE.Color(c)] as const);
  const out = new Float32Array(pos.count * 3);
  const c = new THREE.Color();
  ts.forEach((t, i) => {
    const u = (t - lo) / Math.max(1e-6, hi - lo);
    let k = 0;
    while (k < cols.length - 2 && u > cols[k + 1][0]) k++;
    const [s0, c0] = cols[k];
    const [s1, c1] = cols[k + 1];
    c.copy(c0).lerp(c1, THREE.MathUtils.clamp((u - s0) / Math.max(1e-6, s1 - s0), 0, 1));
    out.set([c.r, c.g, c.b], i * 3);
  });
  geo.setAttribute("color", new THREE.BufferAttribute(out, 3));
}

function Emblem({ scroll }: { scroll: React.RefObject<number> }) {
  const { scene } = useGLTF(MODEL, false, true);
  const root = useRef<THREE.Group>(null);

  // the model with the brand materials; its parts are reached through `root` once mounted
  const model = useMemo(() => {
    const s = scene.clone(true);
    const physical = (color: string, extra: Partial<THREE.MeshPhysicalMaterialParameters> = {}) =>
      new THREE.MeshPhysicalMaterial({ color, roughness: 0.32, metalness: 0.08, clearcoat: 0.55, clearcoatRoughness: 0.2, ...extra });
    const navy = physical(C.navy);
    const navy2 = physical(C.navy2);
    s.traverse((o) => {
      const m = o as THREE.Mesh;
      if (!m.isMesh) return;
      m.castShadow = true;
      const n = m.name.replace(/\.\d+$/, "");
      const parentName = m.parent?.name ?? "";
      const key = n.startsWith("NN_") ? n : parentName;
      if (["NN_Dome", "NN_Drum", "NN_Entablature", "NN_Plinth", "NN_Columns", "NN_Lantern", "NN_LanternDome", "NN_LidUpper", "NN_Pole"].includes(key)) m.material = navy;
      else if (["NN_Architrave", "NN_Cornice", "NN_Step", "NN_LanternBase", "NN_Ribs"].includes(key)) m.material = navy2;
      else if (key === "NN_InnerWall") m.material = physical(C.wall, { roughness: 0.6, clearcoat: 0, emissive: new THREE.Color("#dbeafe"), emissiveIntensity: 0.25 });
      else if (key === "NN_Sclera") m.material = physical(C.white, { roughness: 0.18, clearcoat: 1, clearcoatRoughness: 0.06 });
      else if (key === "NN_LidLower") {
        gradientColors(m.geometry, [[0, "#0a66c2"], [1, "#0a9cb6"]], (p) => p.x);
        m.material = physical("#ffffff", { vertexColors: true });
      } else if (key === "NN_Iris") {
        gradientColors(m.geometry, [[0, "#0ab4a8"], [0.5, "#0a9cb6"], [0.85, "#0a66c2"], [1, "#12337f"]], (p) => Math.hypot(p.x, p.y));
        m.material = physical("#ffffff", { vertexColors: true, roughness: 0.15, clearcoat: 1, clearcoatRoughness: 0.04 });
      } else if (key === "NN_Pupil") m.material = physical(C.pupil, { roughness: 0.08, clearcoat: 1 });
      else if (key === "NN_Shine") m.material = new THREE.MeshBasicMaterial({ color: "#ffffff" });
      else if (key === "NN_Swoosh") {
        gradientColors(m.geometry, [[0, "#12337f"], [0.35, "#0a66c2"], [0.7, "#1f86d6"], [1, "#0ab4a8"]], (p) => p.x * 0.6 - p.y);
        m.material = physical("#ffffff", { vertexColors: true, roughness: 0.2, clearcoat: 0.9 });
      } else if (key === "NN_Tail") {
        gradientColors(m.geometry, [[0, "#0a9cb6"], [1, "#0ab4a8"]], (p) => p.x);
        m.material = physical("#ffffff", { vertexColors: true, roughness: 0.22, clearcoat: 0.9 });
      } else if (key === "NN_Circuits" || key === "NN_Nodes")
        m.material = physical(C.teal, { roughness: 0.25, emissive: new THREE.Color(C.teal), emissiveIntensity: 0.18 });
      else if (m.material instanceof THREE.MeshStandardMaterial) m.material.roughness = 0.5; // the flag keeps its three colours
    });
    return s;
  }, [scene]);

  // the arrival: the dome settles, the eye opens, the sweep and the traces draw in
  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const g = root.current;
    if (reduce || !g) return;
    const get = (n: string) => g.getObjectByName(n);
    const building = get("NN_Building");
    const eye = get("NN_Eye");
    const accents = get("NN_Accents");
    const circuits = [get("NN_Circuits"), get("NN_Nodes")].filter(Boolean) as THREE.Object3D[];
    const tl = gsap.timeline({ delay: 0.15 });
    if (building) tl.from(building.position, { y: building.position.y + 1.6, duration: 1.4, ease: "expo.out" }, 0);
    if (eye) tl.from(eye.scale, { y: 0.02, duration: 1.1, ease: "elastic.out(1, 0.55)" }, 0.45);
    if (accents) tl.from(accents.rotation, { y: -1.2, duration: 1.8, ease: "expo.out" }, 0.2).from(accents.scale, { x: 0.6, y: 0.6, z: 0.6, duration: 1.6, ease: "expo.out" }, 0.2);
    circuits.forEach((c, i) => tl.from(c.scale, { x: 0.001, y: 0.001, z: 0.001, duration: 0.8, ease: "back.out(2)" }, 1.0 + i * 0.12));
    tl.from(g.rotation, { y: -0.9, duration: 2.2, ease: "expo.out" }, 0);
    return () => {
      tl.kill();
    };
  }, [model]);

  useFrame(({ pointer }) => {
    const g = root.current;
    if (!g) return;
    const sc = scroll.current ?? 0;
    g.rotation.y = THREE.MathUtils.lerp(g.rotation.y, pointer.x * 0.28 + sc * Math.PI * 0.9, 0.05);
    g.rotation.x = THREE.MathUtils.lerp(g.rotation.x, -pointer.y * 0.12 + sc * 0.25, 0.05);
    const pv = g.getObjectByName("NN_IrisPivot");
    if (pv) {
      pv.rotation.y = THREE.MathUtils.lerp(pv.rotation.y, pointer.x * 0.5, 0.1);
      pv.rotation.x = THREE.MathUtils.lerp(pv.rotation.x, -pointer.y * 0.35, 0.1);
    }
  });

  return (
    <group ref={root} scale={0.86} position={[0, -0.05, 0]}>
      <primitive object={model} />
    </group>
  );
}

export default function EmblemScene({ scroll }: { scroll: React.RefObject<number> }) {
  const [box, on] = useOnScreen<HTMLDivElement>();
  return (
    <div ref={box} className="size-full">
    <Canvas frameloop={on ? "always" : "never"} dpr={[1, 2]} camera={{ position: [0, 0.3, 12.6], fov: 32 }} gl={{ antialias: true, alpha: true }} shadows style={{ background: "transparent" }}>
      <ambientLight intensity={0.55} />
      <directionalLight position={[4, 6, 5]} intensity={2.1} castShadow shadow-mapSize={[1024, 1024]} />
      <directionalLight position={[-5, 2, 3]} intensity={0.7} color="#bcdcf7" />
      <Environment resolution={256}>
        <Lightformer form="rect" intensity={2.4} position={[0, 5, 4]} scale={[10, 3, 1]} />
        <Lightformer form="rect" intensity={1.2} color="#bcdcf7" position={[-6, 1, 2]} scale={[3, 6, 1]} />
        <Lightformer form="ring" intensity={1.6} color="#e3f0fc" position={[5, 2, -3]} scale={4} />
      </Environment>
      <Suspense fallback={null}>
        <Float speed={1.4} rotationIntensity={0.18} floatIntensity={0.55} floatingRange={[-0.08, 0.08]}>
          <Emblem scroll={scroll} />
        </Float>
      </Suspense>
      <ContactShadows position={[0, -2.55, 0]} opacity={0.22} scale={9} blur={2.8} far={4} color="#0b2560" />
    </Canvas>
    </div>
  );
}

useGLTF.preload(MODEL, false, true);
