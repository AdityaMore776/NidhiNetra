"use client";

import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef } from "react";
import type { Plan } from "@/lib/api";
import { cn } from "@/lib/utils";

maplibregl.setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");

const BAND_FILL: Record<string, string> = { CRITICAL: "var(--critical)", HIGH: "var(--high)" };

/** A stop's marker: its number; filled for a flagged work, ringed for a spot check; a dashed ring
 *  when its place is only the district's start point (not found by name). */
function stopEl(n: number, kind: string, band: string | null, rough: boolean, selected: boolean): HTMLElement {
  const el = document.createElement("button");
  el.type = "button";
  el.textContent = String(n);
  el.setAttribute("aria-label", `Stop ${n}`);
  const fill = kind === "spot" ? "#ffffff" : (BAND_FILL[band ?? ""] ?? "var(--brand-600)");
  Object.assign(el.style, {
    width: selected ? "34px" : "28px",
    height: selected ? "34px" : "28px",
    borderRadius: "999px",
    display: "grid",
    placeItems: "center",
    font: "600 13px/1 var(--font-sans, system-ui)",
    color: kind === "spot" ? "var(--teal, #0ab4a8)" : "#ffffff",
    background: fill,
    border: `2.5px ${rough ? "dashed" : "solid"} ${kind === "spot" ? "var(--teal, #0ab4a8)" : "#ffffff"}`,
    boxShadow: selected ? "0 0 0 4px rgb(10 102 194 / 0.35), 0 6px 16px -4px rgb(6 21 55 / 0.45)" : "0 3px 10px -3px rgb(6 21 55 / 0.45)",
    cursor: "pointer",
    transition: "width .15s, height .15s",
  });
  return el;
}

function startEl(): HTMLElement {
  const el = document.createElement("div");
  el.textContent = "Start";
  Object.assign(el.style, {
    padding: "4px 8px",
    borderRadius: "8px",
    font: "600 11px/1 var(--font-sans, system-ui)",
    color: "#ffffff",
    background: "#0b2560",
    boxShadow: "0 3px 10px -3px rgb(6 21 55 / 0.45)",
  });
  return el;
}

/**
 * One day's route on the district's official outline (LGD, as the dashboard map): the start point,
 * the numbered stops and the drive between them. No street map: places are approximate, and the
 * outline is drawn from the same LGD file as every other map in the app.
 */
export function PlanMap({
  plan,
  selected,
  onSelect,
  className,
}: {
  plan: Plan;
  selected: number | null;
  onSelect: (order: number) => void;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markers = useRef<maplibregl.Marker[]>([]);
  // the outline loads after the map: a route drawn before then waits here
  const ready = useRef(false);
  const pending = useRef<(() => void) | null>(null);
  const onSelectRef = useRef(onSelect);
  useEffect(() => {
    onSelectRef.current = onSelect;
  }, [onSelect]);

  // the map and the district outline: once per district
  useEffect(() => {
    if (!ref.current) return;
    const map = new maplibregl.Map({
      container: ref.current,
      style: { version: 8, sources: {}, layers: [{ id: "bg", type: "background", paint: { "background-color": "#f3f7fd" } }] },
      center: [plan.start.lon, plan.start.lat],
      zoom: 8,
      attributionControl: false,
      cooperativeGestures: true,
    });
    mapRef.current = map;
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.addControl(new maplibregl.AttributionControl({ compact: true, customAttribution: "Boundaries: LGD 2024 · Places: India Post offices" }));
    map.on("load", async () => {
      const all = await fetch("/geo/districts.json").then((r) => r.json());
      const outline = {
        type: "FeatureCollection",
        // works carry the census code; the outline file carries it as `code` (never join on `lgd`)
        features: all.features.filter((f: GeoJSON.Feature) => f.properties?.code === plan.district.code),
      } as GeoJSON.FeatureCollection;
      map.addSource("district", { type: "geojson", data: outline });
      map.addLayer({ id: "district-fill", type: "fill", source: "district", paint: { "fill-color": "#dcebfb", "fill-opacity": 0.75 } });
      map.addLayer({ id: "district-line", type: "line", source: "district", paint: { "line-color": "#0a66c2", "line-width": 1.4 } });
      map.addSource("route", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addLayer({
        id: "route",
        type: "line",
        source: "route",
        layout: { "line-join": "round", "line-cap": "round" },
        paint: { "line-color": "#0b2560", "line-width": 2.4, "line-opacity": 0.8, "line-dasharray": [2, 1.2] },
      });
      const b = new maplibregl.LngLatBounds();
      for (const f of outline.features) {
        const g = f.geometry as GeoJSON.Polygon | GeoJSON.MultiPolygon;
        const polys = g.type === "Polygon" ? [g.coordinates] : g.coordinates;
        for (const ring of polys.flatMap((p) => p)) for (const c of ring) b.extend(c as [number, number]);
      }
      if (!b.isEmpty()) map.fitBounds(b, { padding: 36, duration: 0 });
      ready.current = true;
      pending.current?.();
      pending.current = null;
    });
    return () => {
      markers.current.forEach((m) => m.remove());
      markers.current = [];
      map.remove();
      mapRef.current = null;
      ready.current = false;
    };
  }, [plan.district.code, plan.start.lat, plan.start.lon]);

  // the route and markers: whenever the plan or the selected stop changes
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const draw = () => {
      const pts: [number, number][] = [[plan.start.lon, plan.start.lat], ...plan.stops.map((s) => [s.location.lon, s.location.lat] as [number, number])];
      if (plan.stops.length) pts.push([plan.start.lon, plan.start.lat]);
      (map.getSource("route") as maplibregl.GeoJSONSource | undefined)?.setData({
        type: "Feature",
        properties: {},
        geometry: { type: "LineString", coordinates: pts },
      });
      markers.current.forEach((m) => m.remove());
      markers.current = [new maplibregl.Marker({ element: startEl() }).setLngLat([plan.start.lon, plan.start.lat]).addTo(map)];
      // stops at one place (often the district's start point) fan out so each number shows
      const seen = new Map<string, number>();
      for (const s of plan.stops) {
        const k = `${s.location.lat},${s.location.lon}`;
        const i = seen.get(k) ?? 0;
        seen.set(k, i + 1);
        const atStart = s.location.lat === plan.start.lat && s.location.lon === plan.start.lon;
        const j = i + (atStart ? 1 : 0);
        const offset: [number, number] = j === 0 ? [0, 0] : [Math.cos(j * 1.3) * (16 + 6 * j), Math.sin(j * 1.3) * (16 + 6 * j)];
        const el = stopEl(s.order, s.kind, s.band, s.location.precision === "district", selected === s.order);
        el.addEventListener("click", () => onSelectRef.current(s.order));
        markers.current.push(new maplibregl.Marker({ element: el, offset }).setLngLat([s.location.lon, s.location.lat]).addTo(map));
      }
    };
    if (ready.current) draw();
    else pending.current = draw;
  }, [plan, selected]);

  return <div ref={ref} className={cn("overflow-hidden rounded-2xl border bg-[#f3f7fd]", className)} />;
}
