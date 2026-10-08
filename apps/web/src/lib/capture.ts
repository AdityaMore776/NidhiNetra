// Helpers for the site capture page (T123, plan T120 §9.3): the site map in the browser, the seal
// (SHA-256 of the video when filming ends) and the queue of visits waiting to upload (offline).

import type { Anchor, Facing, SiteMap } from "./api";

const EARTH_M = 6_371_000;

export function metres(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const r = Math.PI / 180;
  const a =
    Math.sin(((lat2 - lat1) * r) / 2) ** 2 +
    Math.cos(lat1 * r) * Math.cos(lat2 * r) * Math.sin(((lon2 - lon1) * r) / 2) ** 2;
  return 2 * EARTH_M * Math.asin(Math.min(1, Math.sqrt(a)));
}

/** How far a point is outside the site, in metres (0 inside), before the GPS margin. Mirrors
 * apps/engine/drishti/agents/site_progress/sitemap.py. */
export function outsideBy(site: SiteMap, lat: number, lon: number): number {
  if (site.kind === "linear" && site.end_lat !== null && site.end_lon !== null) {
    const k = Math.cos((site.lat * Math.PI) / 180);
    const ex = (site.end_lon - site.lon) * k, ey = site.end_lat - site.lat;
    const px = (lon - site.lon) * k, py = lat - site.lat;
    const len2 = ex * ex + ey * ey || 1e-12;
    const t = Math.max(0, Math.min(1, (px * ex + py * ey) / len2));
    const d = metres(lat, lon, site.lat + t * ey, site.lon + (t * ex) / k);
    return Math.max(0, d - site.radius_m);
  }
  return Math.max(0, metres(site.lat, site.lon, lat, lon) - site.radius_m);
}

export function insideSite(site: SiteMap, lat: number, lon: number): boolean {
  return outsideBy(site, lat, lon) <= site.gps_margin_m;
}

/** The stretch of a linear site a point is on ("s1", ...), or null. Mirrors sitemap.stretch_of. */
export function stretchOf(site: SiteMap, lat: number, lon: number): string | null {
  if (site.kind !== "linear" || site.end_lat === null || site.end_lon === null || !insideSite(site, lat, lon)) return null;
  const k = Math.cos((site.lat * Math.PI) / 180);
  const ex = (site.end_lon - site.lon) * k, ey = site.end_lat - site.lat;
  const px = (lon - site.lon) * k, py = lat - site.lat;
  const t = Math.max(0, ((px * ex + py * ey) / (ex * ex + ey * ey || 1e-12)) * site.length_m);
  const n = site.stretches.length;
  return `s${Math.min(n, Math.max(1, Math.floor(t / site.stretch_m) + 1))}`;
}

// ---- the same spot every month (T158): mirrors apps/engine/drishti/agents/site_progress/spots.py ----

export const FACING_TOL_DEG = 20;
export const COVER_GOOD = 0.7;
const BIN_DEG = 5;

/** Compass bearing from one point to another, in degrees (0 = north, 90 = east). */
export function bearing(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const r = Math.PI / 180;
  const y = Math.sin((lon2 - lon1) * r) * Math.cos(lat2 * r);
  const x = Math.cos(lat1 * r) * Math.sin(lat2 * r) - Math.sin(lat1 * r) * Math.cos(lat2 * r) * Math.cos((lon2 - lon1) * r);
  return (Math.atan2(y, x) / r + 360) % 360;
}

/** The turn from one heading to another, -180..180 degrees (positive: turn right). */
export function turnBy(from: number, to: number): number {
  return ((((to - from) % 360) + 540) % 360) - 180;
}

function angleDiff(a: number, b: number): number {
  const d = Math.abs(a - b) % 360;
  return Math.min(d, 360 - d);
}

/** The share of an earlier arc these headings panned across (spots.covered); null without an arc
 * or without any heading. */
export function arcCovered(first: Facing | null | undefined, degs: number[]): number | null {
  if (!first) return null;
  if (!degs.length) return null; // no compass: can't tell, which is not 0%
  if (first.width < 2 * BIN_DEG) return degs.some((d) => angleDiff(d, first.mid) <= FACING_TOL_DEG) ? 1 : 0;
  const n = Math.ceil(first.width / BIN_DEG);
  let hit = 0;
  for (let k = 0; k < n; k++) {
    const c = (first.from + BIN_DEG * (k + 0.5)) % 360;
    if (degs.some((d) => angleDiff(d, c) <= BIN_DEG)) hit++;
  }
  return Math.round((hit / n) * 1000) / 1000;
}

/** How far the phone is from a viewpoint's box, and whether it is in it (give or take its own GPS
 * accuracy: the box is about 12 m across, phone GPS about 5 m). */
export function toBox(anchor: Anchor, fix: GpsFix): { metres: number; bearing: number; inside: boolean } {
  const m = metres(fix.lat, fix.lon, anchor.lat, anchor.lon);
  return { metres: m, bearing: bearing(fix.lat, fix.lon, anchor.lat, anchor.lon), inside: m - fix.accuracy <= anchor.box_m };
}

/** The direction the back camera faces, from the phone's orientation (the W3C DeviceOrientation
 * spec's compass-heading example; iPhone Safari gives it directly as webkitCompassHeading). */
export function cameraHeading(alpha: number, beta: number, gamma: number): number {
  const r = Math.PI / 180;
  const cY = Math.cos(gamma * r), cZ = Math.cos(alpha * r);
  const sX = Math.sin(beta * r), sY = Math.sin(gamma * r), sZ = Math.sin(alpha * r);
  const vx = -cZ * sY - sZ * sX * cY;
  const vy = -sZ * sY + cZ * sX * cY;
  let h = Math.atan2(vx, vy) / r;
  if (h < 0) h += 360;
  return h;
}

export async function sha256Hex(blob: Blob): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", await blob.arrayBuffer());
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}

/** A recorder format the phone supports (WebM on Android Chrome, MP4 on iPhone Safari). */
export function recorderType(): string {
  const types = ["video/webm;codecs=vp9", "video/webm;codecs=vp8", "video/webm", "video/mp4"];
  return types.find((t) => typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(t)) ?? "";
}

// ---- visits waiting to upload, kept in this browser (IndexedDB) so filming works offline ----

export interface Pending {
  visit_id: string;
  work_id: string;
  token: string;
  claim: string | null;
  captured_at: string;
  sha256: string;
  log: Record<string, unknown>;
  video: Blob;
}

const DB = "drishti-capture";
const STORE = "pending";

function open(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(STORE, { keyPath: "visit_id" });
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function tx<T>(mode: IDBTransactionMode, run: (s: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  const db = await open();
  return new Promise((resolve, reject) => {
    const req = run(db.transaction(STORE, mode).objectStore(STORE));
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function savePending(p: Pending): Promise<void> {
  try {
    await tx("readwrite", (s) => s.put(p));
  } catch {
    // storage blocked (private window): the visit stays in memory until uploaded
  }
}

export async function listPending(workId: string): Promise<Pending[]> {
  try {
    const all = await tx<Pending[]>("readonly", (s) => s.getAll() as IDBRequest<Pending[]>);
    return all.filter((p) => p.work_id === workId);
  } catch {
    return [];
  }
}

export async function dropPending(visitId: string): Promise<void> {
  try {
    await tx("readwrite", (s) => s.delete(visitId));
  } catch {
    // nothing kept, nothing to drop
  }
}

// ---- one recording: camera, recorder, clock, GPS and motion logs (outside React's render) ----

export interface GpsFix {
  lat: number;
  lon: number;
  accuracy: number;
  speed: number | null;
}

export class Recording {
  private stream: MediaStream | null = null;
  private recorder: MediaRecorder | null = null;
  private chunks: Blob[] = [];
  private t0 = 0;
  private watchId: number | null = null;
  private timers: number[] = [];
  private motionHandler = (e: DeviceMotionEvent) => this.onMotion(e);
  private orientHandler = (e: DeviceOrientationEvent) => this.onOrient(e);
  private onHeading: ((h: number) => void) | null = null;
  startedAt = "";
  gps: { t: number; lat: number; lon: number; accuracy: number }[] = [];
  motion: { t: number; rot: number }[] = [];
  /** The compass (T158): which way the back camera faced, 4 times a second; p = tilt. */
  heading: { t: number; h: number; p: number }[] = [];

  /** Seconds since filming started. */
  now(): number {
    return Math.round(((performance.now() - this.t0) / 1000) * 100) / 100;
  }

  async start(
    video: HTMLVideoElement,
    on: {
      tick: (s: number) => void;
      dark: (d: boolean) => void;
      fix: (g: GpsFix) => void;
      noGps: () => void;
      heading?: (h: number) => void;
    },
    darkBelow: number,
  ): Promise<void> {
    // iPhone asks permission for the motion sensors from a tap
    const DM = DeviceMotionEvent as unknown as { requestPermission?: () => Promise<string> };
    if (typeof DM.requestPermission === "function") await DM.requestPermission().catch(() => "denied");
    // ... and for the compass, from the same tap (T158)
    const DO = DeviceOrientationEvent as unknown as { requestPermission?: () => Promise<string> };
    if (typeof DO.requestPermission === "function") await DO.requestPermission().catch(() => "denied");
    this.stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: false,
    });
    video.srcObject = this.stream;
    await video.play();
    const type = recorderType();
    this.recorder = new MediaRecorder(this.stream, type ? { mimeType: type } : undefined);
    this.recorder.ondataavailable = (e) => {
      if (e.data.size) this.chunks.push(e.data);
    };
    this.t0 = performance.now();
    this.startedAt = new Date().toISOString();
    this.recorder.start(1000);
    window.addEventListener("devicemotion", this.motionHandler);
    this.onHeading = on.heading ?? null;
    window.addEventListener("deviceorientationabsolute", this.orientHandler as EventListener);
    window.addEventListener("deviceorientation", this.orientHandler);
    this.watchId =
      navigator.geolocation?.watchPosition(
        (p) => {
          const g = { lat: p.coords.latitude, lon: p.coords.longitude, accuracy: p.coords.accuracy, speed: p.coords.speed };
          this.gps.push({ t: Math.round(this.now() * 10) / 10, lat: g.lat, lon: g.lon, accuracy: g.accuracy });
          on.fix(g);
        },
        () => on.noGps(),
        { enableHighAccuracy: true, maximumAge: 0 },
      ) ?? null;
    const canvas = document.createElement("canvas");
    canvas.width = 32;
    canvas.height = 18;
    this.timers.push(
      window.setInterval(() => on.tick(Math.floor(this.now())), 500),
      window.setInterval(() => {
        const ctx = canvas.getContext("2d");
        if (!ctx) return;
        ctx.drawImage(video, 0, 0, 32, 18);
        const px = ctx.getImageData(0, 0, 32, 18).data;
        let sum = 0;
        for (let i = 0; i < px.length; i += 4) sum += 0.299 * px[i] + 0.587 * px[i + 1] + 0.114 * px[i + 2];
        on.dark(sum / (px.length / 4) < darkBelow);
      }, 1000),
    );
  }

  private onMotion(e: DeviceMotionEvent) {
    const r = e.rotationRate;
    if (!r) return;
    const t = this.now();
    const last = this.motion[this.motion.length - 1];
    if (!last || t - last.t >= 0.2) this.motion.push({ t, rot: Math.hypot(r.alpha ?? 0, r.beta ?? 0, r.gamma ?? 0) });
  }

  private onOrient(e: DeviceOrientationEvent) {
    // iPhone: the heading the back camera faces; Android: computed from the absolute orientation
    // (a relative one, absolute = false, has no north and is left out)
    const ios = (e as DeviceOrientationEvent & { webkitCompassHeading?: number }).webkitCompassHeading;
    let h: number | null = null;
    if (typeof ios === "number" && Number.isFinite(ios)) h = ios;
    else if (e.absolute && e.alpha !== null && e.beta !== null && e.gamma !== null) h = cameraHeading(e.alpha, e.beta, e.gamma);
    if (h === null) return;
    const t = this.now();
    const last = this.heading[this.heading.length - 1];
    if (!last || t - last.t >= 0.25) {
      // 4 times a second: enough to log a pan, and the page redraws no faster
      this.heading.push({ t, h: Math.round(h * 10) / 10, p: Math.round((e.beta ?? 0) * 10) / 10 });
      this.onHeading?.(h);
    }
  }

  /** Stop filming; the video as one file. */
  async stop(): Promise<{ blob: Blob; seconds: number }> {
    const seconds = Math.round(this.now());
    const rec = this.recorder;
    if (rec && rec.state !== "inactive") {
      const ended = new Promise<void>((resolve) => (rec.onstop = () => resolve()));
      rec.stop();
      await ended;
    }
    this.release();
    return { blob: new Blob(this.chunks, { type: rec?.mimeType || "video/webm" }), seconds };
  }

  /** Let go of the camera, GPS, sensors and timers. */
  release() {
    this.timers.forEach((id) => window.clearInterval(id));
    this.timers = [];
    if (this.watchId !== null) navigator.geolocation?.clearWatch(this.watchId);
    this.watchId = null;
    window.removeEventListener("devicemotion", this.motionHandler);
    window.removeEventListener("deviceorientationabsolute", this.orientHandler as EventListener);
    window.removeEventListener("deviceorientation", this.orientHandler);
    this.onHeading = null;
    this.stream?.getTracks().forEach((tr) => tr.stop());
    this.stream = null;
  }
}
