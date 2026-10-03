"use client";

import * as maplibregl from "maplibre-gl";
import { Box, Globe2, LocateFixed, Square } from "lucide-react";
import { motion } from "motion/react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import type { DistrictRow } from "@/lib/api";
import { inr } from "@/lib/format";
import { cn } from "@/lib/utils";

// See scripts/copy-maplibre.mjs: the worker is served from public/ because the bundler does not emit it.
maplibregl.setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");

export type GlobeMetric = "share" | "review" | "amount";

export const METRICS: Record<GlobeMetric, { label: string; short: string; legendLo: string; legendHi: (max: number) => string }> = {
  share: { label: "Share of works needing review", short: "Share", legendLo: "0%", legendHi: (m) => `${(m * 100).toFixed(1)}%` },
  review: { label: "Works needing review", short: "Count", legendLo: "0", legendHi: (m) => m.toLocaleString("en-IN") },
  amount: { label: "Money recommended", short: "Money", legendLo: "₹0", legendHi: (m) => inr(m) },
};

// one hue, light to dark (sequential): pale sky -> brand blue -> navy
const RAMP = ["#dcebfb", "#9cc9f2", "#4ea3e6", "#0a66c2", "#12337f", "#061537"];
const NO_DATA = "#e8ecf3";
const HOVER = "#0ab4a8";
const MAX_HEIGHT_M = 300_000;
const HOME = { center: [80.6, 20.6] as [number, number], zoom: 3.1 };

function rampExpr(key: string): maplibregl.ExpressionSpecification {
  return [
    "case",
    ["<", ["get", "works"], 1],
    NO_DATA,
    ["interpolate", ["linear"], ["get", key], 0, RAMP[0], 0.12, RAMP[1], 0.3, RAMP[2], 0.55, RAMP[3], 0.8, RAMP[4], 1, RAMP[5]],
  ];
}

function graticule(): GeoJSON.FeatureCollection {
  const features: GeoJSON.Feature[] = [];
  for (let lon = -180; lon < 180; lon += 15)
    features.push({ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: Array.from({ length: 37 }, (_, i) => [lon, -90 + i * 5]) } });
  for (let lat = -75; lat <= 75; lat += 15)
    features.push({ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: Array.from({ length: 73 }, (_, i) => [-180 + i * 5, lat]) } });
  return { type: "FeatureCollection", features };
}

const esc = (s: unknown) => String(s ?? "").replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);

/**
 * India's districts on a 3D globe: each district rises by the chosen measure. Hover for its
 * numbers, click to open its works. Drawn only from the Local Government Directory's outlines
 * (data/boundaries.py), so the national boundary is the official one and no third-party border
 * layer is involved.
 */
export function IndiaGlobe({
  rows,
  metric,
  focus,
  onMetric,
  className,
}: {
  rows: DistrictRow[];
  metric: GlobeMetric;
  focus?: string | null;
  onMetric?: (m: GlobeMetric) => void;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const centres = useRef(new Map<string, [number, number]>());
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [three, setThree] = useState(true);
  const metricRef = useRef(metric);

  const max = useMemo(
    () => ({
      share: Math.max(1e-9, ...rows.map((r) => r.share)),
      review: Math.max(1, ...rows.map((r) => r.review)),
      amount: Math.max(1, ...rows.map((r) => r.amount)),
    }),
    [rows],
  );

  // build once per data set
  useEffect(() => {
    if (!ref.current) return;
    // Works carry the Census-2011 district code (named district_lgd); the outlines carry the
    // real LGD code. data/district_crosswalk.py writes the works' code onto each outline as
    // `code` - join on that, never on `lgd`, or the wrong district is painted.
    const byCode = new Map(rows.map((r) => [r.district_lgd, r]));
    const map = new maplibregl.Map({
      container: ref.current,
      style: {
        version: 8,
        projection: { type: "globe" },
        sky: {
          "sky-color": "#ffffff",
          "horizon-color": "#d9ebfb",
          "fog-color": "#ffffff",
          "atmosphere-blend": ["interpolate", ["linear"], ["zoom"], 0, 1, 4, 0.75, 7, 0.2],
        },
        light: { anchor: "viewport", color: "#ffffff", intensity: 0.42, position: [1.3, 205, 35] },
        sources: {},
        layers: [{ id: "bg", type: "background", paint: { "background-color": "#f3f7fd" } }],
      },
      center: [79, 21],
      zoom: 1.35,
      pitch: 0,
      bearing: 0,
      attributionControl: false,
      cooperativeGestures: true,
      maxPitch: 70,
    });
    mapRef.current = map;
    if (process.env.NODE_ENV === "development") (window as unknown as { __map: unknown }).__map = map;
    map.on("error", (e) => console.error("map error", e.error?.message ?? e));
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
    map.addControl(new maplibregl.AttributionControl({ compact: true, customAttribution: "Boundaries: Local Government Directory (LGD 2024)" }));

    const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 14, maxWidth: "280px" });
    let hovered: number | string | undefined;

    map.on("load", async () => {
      const [districts, states] = await Promise.all([
        fetch("/geo/districts.json").then((r) => r.json()),
        fetch("/geo/states.json").then((r) => r.json()),
      ]);
      for (const f of districts.features) {
        const r = f.properties.code ? byCode.get(f.properties.code) : undefined;
        f.properties.share = r ? r.share : 0;
        f.properties.works = r ? r.works : 0;
        f.properties.review = r ? r.review : 0;
        f.properties.amount = r ? r.amount : 0;
        f.properties.t_share = r ? Math.min(1, r.share / max.share) : 0;
        f.properties.t_review = r ? Math.sqrt(r.review / max.review) : 0;
        f.properties.t_amount = r ? Math.sqrt(r.amount / max.amount) : 0;
        if (f.properties.code) {
          const b = new maplibregl.LngLatBounds();
          const walk = (c: unknown): void => {
            if (Array.isArray(c) && typeof c[0] === "number") b.extend(c as [number, number]);
            else if (Array.isArray(c)) c.forEach(walk);
          };
          walk(f.geometry.coordinates);
          const ctr = b.getCenter();
          centres.current.set(f.properties.code, [ctr.lng, ctr.lat]);
        }
      }
      map.addSource("graticule", { type: "geojson", data: graticule() });
      map.addSource("districts", { type: "geojson", data: districts, generateId: true });
      map.addSource("states", { type: "geojson", data: states });
      map.addLayer({ id: "graticule", type: "line", source: "graticule", paint: { "line-color": "#c9d9ee", "line-width": 0.6, "line-opacity": 0.8 } });
      map.addLayer({
        id: "districts-fill",
        type: "fill",
        source: "districts",
        paint: { "fill-color": rampExpr(`t_${metricRef.current}`), "fill-opacity": 0.95 },
      });
      map.addLayer({
        id: "districts-3d",
        type: "fill-extrusion",
        source: "districts",
        paint: {
          "fill-extrusion-color": ["case", ["boolean", ["feature-state", "hover"], false], HOVER, rampExpr(`t_${metricRef.current}`)],
          "fill-extrusion-height": 0,
          "fill-extrusion-base": 0,
          "fill-extrusion-opacity": 0.96,
          "fill-extrusion-vertical-gradient": true,
          "fill-extrusion-height-transition": { duration: 1400, delay: 0 },
        },
      });
      map.addLayer({ id: "districts-line", type: "line", source: "districts", paint: { "line-color": "#ffffff", "line-width": 0.35, "line-opacity": 0.8 } });
      map.addLayer({ id: "states-line", type: "line", source: "states", paint: { "line-color": "#0b2560", "line-width": 0.8, "line-opacity": 0.45 } });

      const onMove = (e: maplibregl.MapLayerMouseEvent) => {
        const f = e.features?.[0];
        if (!f) return;
        map.getCanvas().style.cursor = f.properties.works > 0 ? "pointer" : "";
        if (hovered !== undefined) map.setFeatureState({ source: "districts", id: hovered }, { hover: false });
        hovered = f.id;
        if (hovered !== undefined) map.setFeatureState({ source: "districts", id: hovered }, { hover: true });
        const p = f.properties;
        const body =
          p.works > 0
            ? `<div style="display:grid;grid-template-columns:auto auto;gap:2px 14px;margin-top:6px;font-size:12px">
                 <span style="color:#5b6478">Works</span><b style="text-align:right">${Number(p.works).toLocaleString("en-IN")}</b>
                 <span style="color:#5b6478">Need review</span><b style="text-align:right;color:#e11d48">${Number(p.review).toLocaleString("en-IN")}</b>
                 <span style="color:#5b6478">Share</span><b style="text-align:right">${(p.share * 100).toFixed(2)}%</b>
                 <span style="color:#5b6478">Money</span><b style="text-align:right">${esc(inr(p.amount))}</b>
               </div><div style="margin-top:6px;font-size:11px;color:#0a66c2">Click to open its works →</div>`
            : `<div style="margin-top:4px;font-size:12px;color:#5b6478">No works recorded</div>`;
        popup
          .setLngLat(e.lngLat)
          .setHTML(`<div style="font-size:13px;font-weight:600;color:#061537">${esc(p.name)}</div><div style="font-size:11px;color:#5b6478">${esc(p.state)}</div>${body}`)
          .addTo(map);
      };
      const onLeave = () => {
        map.getCanvas().style.cursor = "";
        if (hovered !== undefined) map.setFeatureState({ source: "districts", id: hovered }, { hover: false });
        hovered = undefined;
        popup.remove();
      };
      const onClick = (e: maplibregl.MapLayerMouseEvent) => {
        const code = e.features?.[0]?.properties?.code;
        if (code && e.features?.[0]?.properties?.works > 0) router.push(`/works?district=${code}`);
      };
      for (const layer of ["districts-3d", "districts-fill"]) {
        map.on("mousemove", layer, onMove);
        map.on("mouseleave", layer, onLeave);
        map.on("click", layer, onClick);
      }

      // the arrival: from the whole Earth into India, then the districts rise
      map.flyTo({ center: HOME.center, zoom: HOME.zoom, pitch: 44, bearing: -12, duration: 3200, curve: 1.5, essential: true });
      map.once("moveend", () => {
        map.setPaintProperty("districts-3d", "fill-extrusion-height", ["*", ["get", `t_${metricRef.current}`], MAX_HEIGHT_M]);
        setReady(true);
      });
    });
    return () => {
      popup.remove();
      map.remove();
      mapRef.current = null;
    };
  }, [rows, router, max]);

  // the measure changes: colours and heights glide to the new values
  useEffect(() => {
    metricRef.current = metric;
    const map = mapRef.current;
    if (!map || !map.getLayer("districts-3d")) return;
    map.setPaintProperty("districts-fill", "fill-color", rampExpr(`t_${metric}`));
    map.setPaintProperty("districts-3d", "fill-extrusion-color", ["case", ["boolean", ["feature-state", "hover"], false], HOVER, rampExpr(`t_${metric}`)]);
    if (three && ready) map.setPaintProperty("districts-3d", "fill-extrusion-height", ["*", ["get", `t_${metric}`], MAX_HEIGHT_M]);
  }, [metric, three, ready]);

  // a district picked elsewhere on the page: glide to it
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !focus || !ready) return;
    const c = centres.current.get(focus);
    if (c) map.easeTo({ center: c, zoom: 5.3, pitch: three ? 55 : 0, duration: 1200 });
  }, [focus, ready, three]);

  function setMode(next: boolean) {
    setThree(next);
    const map = mapRef.current;
    if (!map || !map.getLayer("districts-3d")) return;
    map.setPaintProperty("districts-3d", "fill-extrusion-height", next ? ["*", ["get", `t_${metric}`], MAX_HEIGHT_M] : 0);
    map.easeTo({ pitch: next ? 44 : 0, bearing: next ? -12 : 0, duration: 900 });
  }

  function reset() {
    mapRef.current?.flyTo({ center: HOME.center, zoom: HOME.zoom, pitch: three ? 44 : 0, bearing: three ? -12 : 0, duration: 1600 });
  }

  return (
    <div className={cn("relative overflow-hidden rounded-2xl", className)}>
      <div
        className="absolute inset-0"
        style={{ background: "radial-gradient(120% 90% at 50% 40%, #ffffff 0%, #eef5fd 55%, #e1edfb 100%)" }}
      />
      <div ref={ref} className="relative h-full w-full" />

      {/* controls */}
      <div className="absolute left-3 top-3 flex flex-col gap-2">
        <div className="glass flex rounded-xl p-1 shadow-card">
          {(Object.keys(METRICS) as GlobeMetric[]).map((m) => (
            <button
              key={m}
              onClick={() => onMetric?.(m)}
              className={cn(
                "relative rounded-lg px-3 py-1.5 text-xs font-medium transition-colors",
                metric === m ? "text-white" : "text-muted-foreground hover:text-foreground",
              )}
            >
              {metric === m && (
                <motion.span layoutId="globe-metric" className="absolute inset-0 rounded-lg bg-brand-gradient" transition={{ type: "spring", stiffness: 400, damping: 32 }} />
              )}
              <span className="relative">{METRICS[m].short}</span>
            </button>
          ))}
        </div>
        <div className="glass flex w-fit rounded-xl p-1 shadow-card">
          <button
            onClick={() => setMode(true)}
            className={cn("flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium", three ? "bg-white text-brand-900 shadow-sm" : "text-muted-foreground")}
          >
            <Box className="size-3.5" /> 3D
          </button>
          <button
            onClick={() => setMode(false)}
            className={cn("flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium", !three ? "bg-white text-brand-900 shadow-sm" : "text-muted-foreground")}
          >
            <Square className="size-3.5" /> Flat
          </button>
          <button onClick={reset} title="Back to all of India" className="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground">
            <LocateFixed className="size-3.5" />
          </button>
        </div>
      </div>

      {/* legend */}
      <div className="glass absolute bottom-3 left-3 w-60 rounded-xl px-3.5 py-3 shadow-card">
        <div className="flex items-center gap-1.5 text-[11px] font-semibold text-brand-950">
          <Globe2 className="size-3.5 text-brand-600" />
          {METRICS[metric].label}
        </div>
        <div className="mt-2 h-2 rounded-full" style={{ background: `linear-gradient(90deg, ${RAMP.join(",")})` }} />
        <div className="num mt-1 flex justify-between text-[10px] text-muted-foreground">
          <span>{METRICS[metric].legendLo}</span>
          <span>{METRICS[metric].legendHi(max[metric])}</span>
        </div>
        <div className="mt-1.5 text-[10px] leading-snug text-muted-foreground">
          {metric === "share" ? "Height and colour: the share." : "Height and colour: square root, so big districts don't hide the rest."} Grey: no works.
        </div>
      </div>

      {!ready && (
        <div className="pointer-events-none absolute inset-x-0 bottom-16 flex justify-center">
          <span className="glass rounded-full px-3 py-1 text-[11px] text-muted-foreground shadow-card">Arriving over India…</span>
        </div>
      )}
    </div>
  );
}
