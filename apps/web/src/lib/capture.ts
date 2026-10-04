// Helpers for the site capture page (T123, plan T120 §9.3): the site map in the browser, the seal
// (SHA-256 of the video when filming ends) and the queue of visits waiting to upload (offline).

import type { SiteMap } from "./api";

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
  startedAt = "";
  gps: { t: number; lat: number; lon: number; accuracy: number }[] = [];
  motion: { t: number; rot: number }[] = [];

  /** Seconds since filming started. */
  now(): number {
    return Math.round(((performance.now() - this.t0) / 1000) * 100) / 100;
  }

  async start(
    video: HTMLVideoElement,
    on: { tick: (s: number) => void; dark: (d: boolean) => void; fix: (g: GpsFix) => void; noGps: () => void },
    darkBelow: number,
  ): Promise<void> {
    // iPhone asks permission for the motion sensors from a tap
    const DM = DeviceMotionEvent as unknown as { requestPermission?: () => Promise<string> };
    if (typeof DM.requestPermission === "function") await DM.requestPermission().catch(() => "denied");
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
    this.stream?.getTracks().forEach((tr) => tr.stop());
    this.stream = null;
  }
}
