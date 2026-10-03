"use client";

import { Environment, Lightformer } from "@react-three/drei";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { gsap } from "gsap";
import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import type { Band } from "@/lib/api";
import { useOnScreen } from "./useOnScreen";

/**
 * The review funnel as a 3D vortex. Each particle stands for works: the wide pale disc is the
 * Low band; Medium, High and Critical rise in tighter rings around the NidhiNetra eye. Particle
 * counts are a sample (small bands are given a minimum so they can be seen); the legend beside
 * the scene carries the exact numbers.
 */
const TOTAL = 2600;
const MIN: Record<Band, number> = { CRITICAL: 28, HIGH: 80, MEDIUM: 150, LOW: 0 };
const RING: Record<Band, { r0: number; r1: number; y: number; spread: number; speed: number; size: number; color: string }> = {
  LOW: { r0: 2.35, r1: 4.25, y: -0.62, spread: 0.1, speed: 0.05, size: 0.028, color: "#9cc4ee" },
  MEDIUM: { r0: 1.55, r1: 2.1, y: -0.12, spread: 0.08, speed: 0.11, size: 0.036, color: "#d97706" },
  HIGH: { r0: 0.98, r1: 1.32, y: 0.36, spread: 0.06, speed: 0.19, size: 0.045, color: "#e11d48" },
  CRITICAL: { r0: 0.56, r1: 0.74, y: 0.8, spread: 0.04, speed: 0.32, size: 0.058, color: "#9f1239" },
};

type P = { band: Band; r: number; a0: number; y: number; from: THREE.Vector3; delay: number; size: number };

function seeded(seed: number) {
  let s = seed >>> 0;
  return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
}

function particles(bands: Record<Band, number>): P[] {
  const rnd = seeded(7);
  const total = Math.max(1, bands.CRITICAL + bands.HIGH + bands.MEDIUM + bands.LOW);
  const n: Record<Band, number> = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
  for (const b of ["CRITICAL", "HIGH", "MEDIUM"] as Band[]) n[b] = bands[b] > 0 ? Math.max(MIN[b], Math.round((TOTAL * bands[b]) / total)) : 0;
  n.LOW = Math.max(0, TOTAL - n.CRITICAL - n.HIGH - n.MEDIUM);
  const out: P[] = [];
  for (const b of ["LOW", "MEDIUM", "HIGH", "CRITICAL"] as Band[]) {
    const g = RING[b];
    for (let i = 0; i < n[b]; i++) {
      const r = g.r0 + (g.r1 - g.r0) * Math.sqrt(rnd());
      const dir = new THREE.Vector3(rnd() - 0.5, rnd() - 0.5, rnd() - 0.5).normalize().multiplyScalar(6 + rnd() * 4);
      out.push({ band: b, r, a0: rnd() * Math.PI * 2, y: g.y + (rnd() - 0.5) * g.spread * 2, from: dir, delay: rnd() * 0.35, size: g.size * (0.75 + rnd() * 0.5) });
    }
  }
  return out;
}

function Swarm({ bands }: { bands: Record<Band, number> }) {
  const list = useMemo(() => particles(bands), [bands]);
  const mesh = useRef<THREE.InstancedMesh>(null);
  const progress = useRef({ p: 0 });
  const tmp = useMemo(() => new THREE.Object3D(), []);
  const at = useMemo(() => new THREE.Vector3(), []);

  useEffect(() => {
    const m = mesh.current;
    if (!m) return;
    const c = new THREE.Color();
    list.forEach((p, i) => m.setColorAt(i, c.set(RING[p.band].color)));
    if (m.instanceColor) m.instanceColor.needsUpdate = true;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    progress.current.p = reduce ? 1 : 0;
    const tw = gsap.to(progress.current, { p: 1, duration: reduce ? 0 : 2.6, ease: "expo.out", delay: 0.2 });
    return () => {
      tw.kill();
    };
  }, [list]);

  useFrame(({ clock }) => {
    const m = mesh.current;
    if (!m) return;
    const t = clock.getElapsedTime();
    const pr = progress.current.p;
    for (let i = 0; i < list.length; i++) {
      const p = list[i];
      const g = RING[p.band];
      // inner rings turn faster, like a vortex
      const a = p.a0 + t * g.speed * (1.4 - p.r / 5);
      at.set(Math.cos(a) * p.r, p.y + Math.sin(t * 0.8 + p.a0 * 3) * 0.025, Math.sin(a) * p.r);
      const k = THREE.MathUtils.clamp((pr - p.delay) / (1 - p.delay), 0, 1);
      tmp.position.lerpVectors(p.from, at, k);
      tmp.scale.setScalar(p.size * (0.4 + 0.6 * k));
      tmp.updateMatrix();
      m.setMatrixAt(i, tmp.matrix);
    }
    m.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh ref={mesh} args={[undefined, undefined, list.length]} frustumCulled={false}>
      <icosahedronGeometry args={[1, 1]} />
      <meshStandardMaterial roughness={0.35} metalness={0.05} />
    </instancedMesh>
  );
}

function Guides() {
  return (
    <group>
      {(["MEDIUM", "HIGH", "CRITICAL"] as Band[]).map((b) => {
        const g = RING[b];
        const r = (g.r0 + g.r1) / 2;
        return (
          <mesh key={b} position={[0, g.y, 0]} rotation={[Math.PI / 2, 0, 0]}>
            <torusGeometry args={[r, 0.004, 8, 160]} />
            <meshBasicMaterial color={g.color} transparent opacity={0.25} />
          </mesh>
        );
      })}
      <mesh position={[0, -0.62, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[2.3, 4.35, 128]} />
        <meshBasicMaterial color="#cfe2f7" transparent opacity={0.22} side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
}

const EYE_R = 0.42;

/** A flat disc bent onto the eyeball's front, so a radial texture keeps its planar mapping. */
function onSphere(radius: number, lift: number): THREE.BufferGeometry {
  const g = new THREE.RingGeometry(0.0001, radius, 72, 10);
  const pos = g.attributes.position as THREE.BufferAttribute;
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i);
    const y = pos.getY(i);
    pos.setZ(i, Math.sqrt(Math.max(0, EYE_R * EYE_R - x * x - y * y)) + lift);
  }
  g.computeVertexNormals();
  return g;
}

/** The NidhiNetra eye at the centre, its iris following the pointer. */
function Eye() {
  const iris = useRef<THREE.Group>(null);
  const { pointer } = useThree();
  const irisTex = useMemo(() => {
    const c = document.createElement("canvas");
    c.width = c.height = 256;
    const g = c.getContext("2d")!;
    const grd = g.createRadialGradient(128, 128, 20, 128, 128, 128);
    grd.addColorStop(0, "#0ab4a8");
    grd.addColorStop(0.45, "#0a9cb6");
    grd.addColorStop(0.8, "#0a66c2");
    grd.addColorStop(1, "#12337f");
    g.fillStyle = grd;
    g.fillRect(0, 0, 256, 256);
    g.globalAlpha = 0.18;
    for (let i = 0; i < 90; i++) {
      const a = (i / 90) * Math.PI * 2;
      g.strokeStyle = i % 2 ? "#ffffff" : "#061537";
      g.beginPath();
      g.moveTo(128 + Math.cos(a) * 40, 128 + Math.sin(a) * 40);
      g.lineTo(128 + Math.cos(a) * 124, 128 + Math.sin(a) * 124);
      g.stroke();
    }
    const t = new THREE.CanvasTexture(c);
    t.colorSpace = THREE.SRGBColorSpace;
    return t;
  }, []);

  const [irisGeo, pupilGeo] = useMemo(() => [onSphere(0.2, 0.002), onSphere(0.085, 0.004)], []);

  useFrame(() => {
    const g = iris.current;
    if (!g) return;
    g.rotation.y = THREE.MathUtils.lerp(g.rotation.y, pointer.x * 0.55, 0.08);
    g.rotation.x = THREE.MathUtils.lerp(g.rotation.x, -pointer.y * 0.4, 0.08);
  });

  return (
    <group position={[0, 0.02, 0]}>
      <mesh>
        <sphereGeometry args={[0.42, 64, 64]} />
        <meshPhysicalMaterial color="#ffffff" roughness={0.12} clearcoat={1} clearcoatRoughness={0.08} />
      </mesh>
      <group ref={iris}>
        <mesh geometry={irisGeo}>
          <meshPhysicalMaterial map={irisTex} roughness={0.18} clearcoat={1} clearcoatRoughness={0.05} />
        </mesh>
        <mesh geometry={pupilGeo}>
          <meshPhysicalMaterial color="#061537" roughness={0.1} clearcoat={1} />
        </mesh>
        <mesh position={[0.055, 0.06, 0.418]}>
          <sphereGeometry args={[0.026, 16, 16]} />
          <meshBasicMaterial color="#ffffff" />
        </mesh>
      </group>
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.5, 0.012, 16, 128]} />
        <meshStandardMaterial color="#0a9cb6" emissive="#0a9cb6" emissiveIntensity={0.25} />
      </mesh>
    </group>
  );
}

function Rig() {
  useFrame(({ camera, pointer }) => {
    camera.position.x = THREE.MathUtils.lerp(camera.position.x, pointer.x * 0.9, 0.03);
    camera.position.y = THREE.MathUtils.lerp(camera.position.y, 2.5 + pointer.y * 0.45, 0.03);
    camera.lookAt(0, 0, 0);
  });
  return null;
}

export default function RiskVortex({ bands }: { bands: Record<Band, number> }) {
  const [box, on] = useOnScreen<HTMLDivElement>();
  return (
    <div ref={box} className="size-full">
    <Canvas frameloop={on ? "always" : "never"} dpr={[1, 1.8]} camera={{ position: [0, 2.5, 7.4], fov: 36 }} gl={{ antialias: true, alpha: true }} style={{ background: "transparent" }}>
      <ambientLight intensity={0.7} />
      <directionalLight position={[3, 6, 4]} intensity={1.6} />
      <directionalLight position={[-4, 2, -3]} intensity={0.5} color="#bcdcf7" />
      <Environment resolution={128}>
        <Lightformer form="rect" intensity={2} position={[0, 4, 3]} scale={[8, 2, 1]} />
        <Lightformer form="ring" intensity={1.2} color="#bcdcf7" position={[-4, 1, -2]} scale={3} />
      </Environment>
      <Guides />
      <Swarm bands={bands} />
      <Eye />
      <Rig />
    </Canvas>
    </div>
  );
}
