// MapLibre 6 runs its tile work in an ES-module worker that bundlers do not
// emit, so the worker and the module it imports are copied into public/ and
// the map is pointed at them with setWorkerUrl (src/components/IndiaMap.tsx).
import { copyFileSync, mkdirSync } from "node:fs";

const out = "public/maplibre";
mkdirSync(out, { recursive: true });
for (const f of ["maplibre-gl-worker.mjs", "maplibre-gl-shared.mjs"]) {
  copyFileSync(`node_modules/maplibre-gl/dist/${f}`, `${out}/${f}`);
}
console.log("copied MapLibre worker to", out);
