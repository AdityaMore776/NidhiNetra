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
    // Works carry the Census-2011 district code (named district_lgd); the outlines carry the
    // real LGD code. data/district_crosswalk.py writes the works' code onto each outline as
    // `code` - join on that, never on `lgd`, or the wrong district is painted.
    const byCode = new Map(rows.map((r) => [r.district_lgd, r]));
    const map = new maplibregl.Map({
      container: ref.current,
      style: { version: 8, sources: {}, layers: [{ id: "bg", type: "background", paint: { "background-color": "#f5f5f2" } }] },
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
        const r = f.properties.code ? byCode.get(f.properties.code) : undefined;
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
            "#e3e3df",
            ["interpolate", ["linear"], ["get", "share"], 0, "#e7f3ea", 0.004, "#fbf0e3", 0.012, "#e79a4a", 0.03, "#b42318"],
          ],
          "fill-opacity": 1,
        },
      });
      map.addLayer({ id: "districts-line", type: "line", source: "districts", paint: { "line-color": "#ffffff", "line-width": 0.4 } });
      map.addLayer({ id: "states-line", type: "line", source: "states", paint: { "line-color": "#767671", "line-width": 0.8 } });

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
        const code = e.features?.[0]?.properties?.code;
        if (code) router.push(`/works?district=${code}`);
      });
    });
    return () => map.remove();
  }, [rows, router]);

  return (
    <div className="relative border border-line">
      <div ref={ref} className="h-[380px] w-full overflow-hidden sm:h-[460px]" />
      <div className="absolute bottom-3 left-3 space-y-1 border border-strong bg-surface px-3 py-2 text-[11px] text-muted">
        <div className="label">Share of works needing review</div>
        <div className="flex items-center gap-0.5">
          {["#e7f3ea", "#fbf0e3", "#e79a4a", "#b42318"].map((c) => (
            <span key={c} className="h-2.5 w-6" style={{ background: c }} />
          ))}
        </div>
        <div className="tnum flex justify-between">
          <span>0%</span>
          <span>3%+</span>
        </div>
      </div>
    </div>
  );
}
