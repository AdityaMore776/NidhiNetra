"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { api, type SearchResults } from "@/lib/api";
import { inr, workHref, workType } from "@/lib/format";
import { BandBadge, Pill } from "./ui";

/** Every result says where it lives, so an officer never follows a dead end. */
type Group =
  | { key: "works"; label: string; rows: Row[] }
  | { key: "districts"; label: string; rows: Row[] }
  | { key: "offices"; label: string; rows: Row[] }
  | { key: "checks"; label: string; rows: Row[] }
  | { key: "hint"; label: string; rows: Row[] };

type Row = { id: string; title: string; sub: string; right?: string; go: string; badge?: React.ReactNode };

const MIN = 2;

export function SearchCommand({ onClose }: { onClose: () => void }) {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [held, setHeld] = useState<{ q: string; data: SearchResults | null }>({ q: "", data: null });
  const [hit, setHit] = useState(0);
  const box = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  // Mounted only while open (the shell owns that), so it starts empty every time
  // and needs no reset effect.
  useEffect(() => {
    const t = window.setTimeout(() => box.current?.focus(), 30);
    return () => window.clearTimeout(t);
  }, []);

  const asked = q.trim();
  const key = asked.toLowerCase();
  const longEnough = key.length >= MIN;

  // Debounced, and keyed: an answer is only shown when it belongs to the text now
  // in the box, so results never flicker in from an earlier keystroke.
  useEffect(() => {
    if (!longEnough) return;
    const ac = new AbortController();
    const t = window.setTimeout(() => {
      api<SearchResults>("/search", { q: asked }, ac.signal)
        .then((data) => setHeld({ q: key, data }))
        .catch(() => {
          /* an aborted or failed search simply leaves the last answer on screen */
        });
    }, 220);
    return () => {
      ac.abort();
      window.clearTimeout(t);
    };
  }, [key, longEnough]);   // eslint-disable-line react-hooks/exhaustive-deps

  const data = held.q === key ? held.data : null;
  const busy = longEnough && !data;
  const groups = useMemo<Group[]>(() => buildGroups(data, asked), [data, asked]);

  const go = (row: Row) => {
    onClose();
    router.push(row.go);
  };

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Escape") {
      e.preventDefault();
      onClose();
      return;
    }
    const flat = groups.flatMap((g) => g.rows);
    if (!flat.length) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHit((h) => (h + 1) % flat.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHit((h) => (h - 1 + flat.length) % flat.length);
    } else if (e.key === "Enter") {
      e.preventDefault();
      go(flat[hit]);
    }
  }

  useEffect(() => {
    const active = listRef.current?.querySelector('[data-active="true"]');
    active?.scrollIntoView({ block: "nearest" });
  }, [hit, groups]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-navy/30 p-4 pt-[8vh]"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Search works, districts, offices and checks"
        className="w-full max-w-2xl overflow-hidden rounded-lg border border-line-strong bg-surface shadow-lg"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={onKeyDown}
      >
        <div className="flex items-center gap-2 border-b border-line px-3">
          <span aria-hidden className="text-muted">
            ⌕
          </span>
          <input
            ref={box}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Work ID, what it built, a district, an office, a question…"
            className="flex-1 bg-transparent py-3 text-sm outline-none placeholder:text-muted"
            aria-describedby="search-help"
          />
          {busy && <span className="text-2xs text-muted">searching…</span>}
          <kbd className="rounded border border-line-strong px-1 text-2xs text-muted">Esc</kbd>
        </div>
        <p id="search-help" className="sr-only">
          Results appear as you type. Use the up and down arrows to move and Enter to open.
        </p>

        <ul ref={listRef} className="max-h-[52vh] overflow-y-auto">
          {q.trim().length < MIN ? (
            <li className="px-3 py-6 text-center text-xs text-muted">
              Type at least {MIN} characters.
            </li>
          ) : groups.every((g) => !g.rows.length) ? (
            <li className="px-3 py-6 text-center text-xs text-muted">
              Nothing found for &ldquo;{asked}&rdquo;.
              <span className="block mt-1 text-muted">
                DRISHTI searches work IDs, what the work says it built, its district and its office.
              </span>
            </li>
          ) : (
            groups.map((g) =>
              g.rows.length === 0 ? null : (
                <li key={g.key}>
                  <div className="eyebrow sticky top-0 bg-surface px-3 py-1">{g.label}</div>
                  <ul>
                    {g.rows.map((r) => {
                      const i = groups.flatMap((x) => x.rows).indexOf(r);
                      return (
                        <li key={r.id}>
                          <button
                            type="button"
                            data-active={i === hit}
                            onMouseEnter={() => setHit(i)}
                            onClick={() => go(r)}
                            className={`flex w-full items-center gap-2 px-3 py-2 text-left text-sm ${
                              i === hit ? "bg-sunken" : ""
                            }`}
                          >
                            <span className="min-w-0 flex-1">
                              <span className="block truncate font-medium text-foreground">{r.title}</span>
                              <span className="block truncate text-2xs text-muted">{r.sub}</span>
                            </span>
                            {r.badge}
                            {r.right && <span className="tnum shrink-0 text-2xs text-muted">{r.right}</span>}
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                </li>
              ),
            )
          )}
        </ul>

        <p className="border-t border-line px-3 py-1.5 text-2xs text-muted">
          ↑ ↓ to move · Enter to open · Esc to close
        </p>
      </div>
    </div>
  );
}

function buildGroups(data: SearchResults | null, q: string): Group[] {
  const hint: Group = {
    key: "hint",
    label: "Try",
    rows: [
      { id: "h-queue", title: "The review queue", sub: "works an officer should look at first", go: "/queue" },
      { id: "h-plan", title: "The inspection planner", sub: "works to verify on the ground", go: "/inspections" },
      { id: "h-works", title: "All works", sub: "every work in your area", go: "/works" },
    ],
  };
  if (!data) return q.length ? [hint] : [];

  const works: Row[] = data.works.items.slice(0, 8).map((w) => ({
    id: `w-${w.work_id}`,
    title: `${workType(w.work_type_code)}${w.description ? ` — ${w.description}` : ""}`,
    sub: [w.work_id, w.district_name, w.state_name].filter(Boolean).join(" · "),
    right: inr(w.amount),
    badge: <BandBadge band={w.band} limited={w.limited} size="sm" />,
    go: workHref(w.work_id),
  }));

  const districts: Row[] = data.districts.map((d) => ({
    id: `d-${d.district_lgd}`,
    title: d.name,
    sub: `${d.state ?? "state not recorded"} · ${d.works.toLocaleString("en-IN")} works`,
    right: d.review ? `${d.review.toLocaleString("en-IN")} to review` : undefined,
    go: `/works?district=${encodeURIComponent(d.district_lgd)}`,
  }));

  const offices: Row[] = data.offices.map((o) => ({
    id: `o-${o.agency_name}`,
    title: o.agency_name,
    sub: [o.district_name, o.state_name].filter(Boolean).join(" · "),
    right: `${o.works.toLocaleString("en-IN")} works`,
    go: `/works?q=${encodeURIComponent(o.agency_name)}`,
  }));

  const checks: Row[] = data.checks.map((c) => {
    // A check is not a filter on its own: the works list filters by finding code,
    // so link to the code this check raises most often, and say what it is.
    const top = c.codes[0];
    return {
      id: `c-${c.id}`,
      title: c.name,
      sub: c.codes.length
        ? `${c.question} · ${c.codes.length} finding${c.codes.length === 1 ? "" : "s"}`
        : c.question,
      right: c.built ? undefined : "in development",
      badge: c.built ? undefined : (
        <Pill glyph="◌" title="Not built yet.">
          in development
        </Pill>
      ),
      go: top ? `/works?finding=${encodeURIComponent(top)}` : "/works",
    };
  });

  return [
    { key: "works", label: `Works (${data.works.total.toLocaleString("en-IN")})`, rows: works },
    { key: "districts", label: "Districts", rows: districts },
    { key: "offices", label: "Offices", rows: offices },
    { key: "checks", label: "Checks", rows: checks },
  ].filter((g) => g.rows.length) as Group[];
}