"use client";

import * as maplibregl from "maplibre-gl";
import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";
import type { DistrictRow } from "@/lib/api";

// See scripts/copy-maplibre.mjs: the worker is served from public/ because the bundler does not emit it.
maplibregl.setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");

/**
 * District map of India, coloured by the share of works needing review.
 *
 * Drawn on a plain background from the Local Government Directory's own
 * outlines (data/boundaries.py), so the national boundary shown is the
 * official one and no third-party border layer is involved.
 */
export function IndiaMap({ rows }: { rows: DistrictRow[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    if (!ref.current) return;
    const byLgd = new Map(rows.map((r) => [r.district_lgd, r]));
    const map = new maplibregl.Map({
      container: ref.current,
      style: { version: 8, sources: {}, layers: [{ id: "bg", type: "background", paint: { "background-color": "#eef1f7" } }] },
      bounds: [
        [67.5, 6.2],
        [97.8, 37.4],
      ],
      fitBoundsOptions: { padding: 12 },
      attributionControl: false,
      dragRotate: false,
    });
    if (process.env.NODE_ENV === "development") (window as unknown as { __map: unknown }).__map = map;
    map.on("error", (e) => console.error("map error", e.error?.message ?? e));
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.addControl(new maplibregl.AttributionControl({ customAttribution: "Boundaries: Local Government Directory (LGD 2024)" }));

    const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false });

    map.on("load", async () => {
      const [districts, states] = await Promise.all([
        fetch("/geo/districts.json").then((r) => r.json()),
        fetch("/geo/states.json").then((r) => r.json()),
      ]);
      for (const f of districts.features) {
        const r = byLgd.get(f.properties.lgd);
        f.properties.share = r ? r.share : -1;
        f.properties.works = r ? r.works : 0;
        f.properties.review = r ? r.review : 0;
      }
      map.addSource("districts", { type: "geojson", data: districts });
      map.addSource("states", { type: "geojson", data: states });
      map.addLayer({
        id: "districts-fill",
        type: "fill",
        source: "districts",
        paint: {
          "fill-color": [
            "case",
            ["<", ["get", "share"], 0],
            "#dfe3ea",
            ["interpolate", ["linear"], ["get", "share"], 0, "#e8f5ee", 0.004, "#fde9b8", 0.012, "#f7a35c", 0.03, "#d6344a"],
          ],
          "fill-opacity": 0.95,
        },
      });
      map.addLayer({ id: "districts-line", type: "line", source: "districts", paint: { "line-color": "#ffffff", "line-width": 0.4 } });
      map.addLayer({ id: "states-line", type: "line", source: "states", paint: { "line-color": "#5d6475", "line-width": 0.9 } });

      map.on("mousemove", "districts-fill", (e) => {
        const p = e.features?.[0]?.properties;
        if (!p) return;
        map.getCanvas().style.cursor = "pointer";
        const share = p.share >= 0 ? `${(p.share * 100).toFixed(2)}% need review` : "no works recorded";
        popup
          .setLngLat(e.lngLat)
          .setHTML(`<div style="font:12px Inter,sans-serif"><b>${p.name}</b>, ${p.state}<br/>${Number(p.works).toLocaleString("en-IN")} works · ${share}</div>`)
          .addTo(map);
      });
      map.on("mouseleave", "districts-fill", () => {
        map.getCanvas().style.cursor = "";
        popup.remove();
      });
      map.on("click", "districts-fill", (e) => {
        const lgd = e.features?.[0]?.properties?.lgd;
        if (lgd) router.push(`/works?district=${lgd}`);
      });
    });
    return () => map.remove();
  }, [rows, router]);

  return (
    <div className="relative">
      <div ref={ref} className="h-[460px] w-full rounded-xl overflow-hidden" />
      <div className="absolute left-3 bottom-3 rounded-lg bg-surface/90 px-3 py-2 text-[11px] text-muted space-y-1">
        <div className="font-medium text-foreground">Share of works needing review</div>
        <div className="flex items-center gap-1">
          {["#e8f5ee", "#fde9b8", "#f7a35c", "#d6344a"].map((c) => (
            <span key={c} className="h-2.5 w-6 rounded-sm" style={{ background: c }} />
          ))}
        </div>
        <div className="flex justify-between">
          <span>0%</span>
          <span>3%+</span>
        </div>
      </div>
    </div>
  );
}
