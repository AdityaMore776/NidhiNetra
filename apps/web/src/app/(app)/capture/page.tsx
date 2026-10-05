"use client";

// Site capture (T123, plan docs/plans/T120-four-agents.md §9.3): film a site visit from the same
// fixed viewpoints every month. The page checks light, place and coverage while filming, so a
// poor video is fixed at the site, never flagged later; it seals the video (SHA-256 when filming
// ends) and uploads it with a capture token issued when filming started.
// Room for error (T136): only what makes a video useless stops the upload (too short, a viewpoint
// half marked, a first visit with fewer than two viewpoints). Everything else (a viewpoint that
// cannot be reached, weak GPS, poor light, walking fast) is shown as a tip and noted in the log;
// Site Progress forgives one poor video and asks only when the last two cannot show the work.

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { api, apiPost, ApiError, type SiteVisits, type VisitKind, type VisitStart } from "@/lib/api";
import {
  dropPending,
  insideSite,
  listPending,
  outsideBy,
  Recording,
  savePending,
  sha256Hex,
  type GpsFix,
  type Pending,
} from "@/lib/capture";

const KINDS: { id: VisitKind; label: string; help: string }[] = [
  { id: "baseline", label: "First visit", help: "Before work starts: sets the site's fixed viewpoints." },
  { id: "monthly", label: "Monthly visit", help: "The same viewpoints as last time, and what was done this month." },
  { id: "check", label: "Check visit", help: "Unannounced, by someone other than the agency." },
  { id: "final", label: "Final visit", help: "The finished work, from every viewpoint." },
];
const MIN_SECONDS = 20;
const MIN_VIEW_SECONDS = 2;
const MIN_BASE_VIEWS = 2; // a first visit needs at least this many viewpoints to compare with
const GOOD_BASE_VIEWS = 4;
const DARK = 40;
const FAST_MPS = 2.5;
const WEAK_GPS_M = 50; // a fix less accurate than this cannot place the phone (the engine's GPS_POOR_M)

interface Mark {
  id: string;
  t0: number;
  t1: number | null;
}

export default function CapturePage() {
  return (
    <Suspense fallback={<p className="text-muted-foreground text-sm">Loading…</p>}>
      <Capture />
    </Suspense>
  );
}

function Capture() {
  const workId = useSearchParams().get("work") ?? "";
  const [info, setInfo] = useState<SiteVisits | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [kind, setKind] = useState<VisitKind | null>(null);
  const [claim, setClaim] = useState("");
  const [visit, setVisit] = useState<VisitStart | null>(null);
  const [filming, setFilming] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [marks, setMarks] = useState<Mark[]>([]);
  const [skipped, setSkipped] = useState<string[]>([]);
  const [at, setAt] = useState<string | null>(null);
  const [dark, setDark] = useState(false);
  const [gps, setGps] = useState<GpsFix | null>(null);
  const [pending, setPending] = useState<Pending[]>([]);
  const [status, setStatus] = useState<string | null>(null);

  const video = useRef<HTMLVideoElement>(null);
  const recording = useRef<Recording | null>(null);

  useEffect(() => {
    if (!workId) return;
    api<SiteVisits>(`/site-visits/${workId}`)
      .then(setInfo)
      .catch((e: ApiError) =>
        setError(
          e.status === 404
            ? "This work is not in your area, or does not exist."
            : e.status === 401
              ? "Filming a site visit needs a staff sign-in (Staff sign in, top right)."
              : e.message,
        ),
      );
    listPending(workId).then(setPending);
  }, [workId]);

  useEffect(() => () => recording.current?.release(), []);

  const chosen = kind ?? info?.next_kind ?? "baseline";
  const expected = (visit?.viewpoints ?? info?.viewpoints ?? []).map((v) => v.id);
  const site = visit?.site ?? info?.site ?? null;

  async function start() {
    setError(null);
    if (chosen !== "baseline" && !claim.trim()) {
      setError("Write what was done since the last visit (for example: walls up to lintel level).");
      return;
    }
    if (!video.current) return;
    const rec = new Recording();
    try {
      const v = await apiPost<VisitStart>("/site-visits/start", { work_id: workId, kind: chosen });
      await rec.start(
        video.current,
        {
          tick: setSeconds,
          dark: setDark,
          fix: setGps,
          noGps: () => setStatus("Location is off: turn it on, the visit needs it."),
        },
        DARK,
      );
      recording.current = rec;
      setVisit(v);
      setMarks([]);
      setSkipped([]);
      setAt(null);
      setFilming(true);
    } catch (e) {
      rec.release();
      setError(e instanceof Error ? e.message : "The camera could not start.");
    }
  }

  function markStart(id: string) {
    const t0 = recording.current?.now() ?? 0;
    setMarks((m) => [...m.filter((x) => x.id !== id), { id, t0, t1: null }]);
    setSkipped((s) => s.filter((x) => x !== id));
    setAt(id);
  }

  function skip(id: string) {
    setSkipped((s) => (s.includes(id) ? s : [...s, id]));
  }

  function markEnd() {
    const now = recording.current?.now() ?? 0;
    setMarks((m) => m.map((x) => (x.id === at && x.t1 === null ? { ...x, t1: now } : x)));
    setAt(null);
  }

  const done = marks.filter((m) => m.t1 !== null && m.t1 - m.t0 >= MIN_VIEW_SECONDS);
  const missing =
    chosen === "baseline" ? [] : expected.filter((id) => !done.some((m) => m.id === id) && !skipped.includes(id));
  const outside = site && gps ? outsideBy(site, gps.lat, gps.lon) : null;
  const weakGps = gps !== null && gps.accuracy > WEAK_GPS_M;
  // only these stop the upload: the video would be useless
  const blockers = [
    seconds < MIN_SECONDS && `Keep filming: at least ${MIN_SECONDS} seconds.`,
    chosen === "baseline" && done.length < MIN_BASE_VIEWS && `Mark at least ${MIN_BASE_VIEWS} viewpoints around the site (a fixed object at each: a tree, a pole, a wall).`,
    at && "Finish the viewpoint you are at.",
  ].filter(Boolean) as string[];
  // these are tips: the video can still be uploaded, and they are noted with it
  const tips = [
    chosen === "baseline" && done.length >= MIN_BASE_VIEWS && done.length < GOOD_BASE_VIEWS && `${GOOD_BASE_VIEWS} or more viewpoints are better, if the site allows.`,
    missing.length > 0 && `Viewpoint${missing.length > 1 ? "s" : ""} ${missing.join(", ")} not filmed yet: walk there, line up the faint picture and mark it, or tap "Can't reach" if it is blocked.`,
    dark && "Too dark: film in daylight if you can. A dark video cannot show the work.",
    weakGps && `GPS is weak (±${Math.round(gps?.accuracy ?? 0)} m): stand in the open for a moment. The views still show where you are.`,
    !weakGps && site && gps && outside !== null && outside - gps.accuracy > site.gps_margin_m && !insideSite(site, gps.lat, gps.lon) &&
      `The phone puts you ${Math.round(outside)} m from the site's map pin. If you are at the site, carry on: the views decide.`,
    gps?.speed != null && gps.speed > FAST_MPS && "Walk more slowly.",
  ].filter(Boolean) as string[];

  async function stop() {
    const rec = recording.current;
    if (!rec || !visit) return;
    const { blob, seconds: duration } = await rec.stop();
    recording.current = null;
    setFilming(false);
    setStatus("Sealing the video…");
    const sha = await sha256Hex(blob);
    const p: Pending = {
      visit_id: visit.visit_id,
      work_id: workId,
      token: visit.token,
      claim: claim.trim() || null,
      captured_at: rec.startedAt,
      sha256: sha,
      log: {
        in_app: true,
        duration_s: duration,
        viewpoints: done.map((m) => ({ id: m.id, t0: m.t0, t1: m.t1 })),
        skipped: skipped.map((id) => ({ id, reason: "could not reach (blocked or unsafe)" })),
        tips,
        gps: rec.gps,
        motion: rec.motion,
        user_agent: navigator.userAgent.slice(0, 200),
      },
      video: blob,
    };
    await savePending(p);
    setVisit(null);
    await upload(p);
  }

  async function upload(p: Pending) {
    setStatus("Uploading…");
    try {
      const { upload_url } = await apiPost<{ upload_url: string }>(`/site-visits/${p.visit_id}/upload`, { token: p.token });
      const res = await fetch(upload_url, {
        method: "PUT",
        headers: { "Content-Type": p.video.type || "video/webm", "x-upsert": "false" },
        body: p.video,
      });
      if (!res.ok) throw new Error(`the video did not upload (${res.status})`);
      await apiPost(`/site-visits/${p.visit_id}/done`, {
        token: p.token,
        sha256: p.sha256,
        captured_at: p.captured_at,
        claim: p.claim,
        log: p.log,
      });
      await dropPending(p.visit_id);
      setStatus("Uploaded. The video is read once, then deleted; its findings appear on the work page.");
      setPending(await listPending(workId));
      api<SiteVisits>(`/site-visits/${workId}`).then(setInfo).catch(() => undefined);
    } catch (e) {
      setStatus(
        `Not uploaded yet: ${e instanceof Error ? e.message : "no connection"}. It is kept on this phone; ` +
          "upload it from here within 7 days.",
      );
      setPending(await listPending(workId));
    }
  }

  if (!workId) return <p className="text-sm">Open this page from a work (Film a site visit).</p>;
  if (error && !info) return <p className="text-sm text-high">{error}</p>;
  if (!info) return <p className="text-muted-foreground text-sm">Loading…</p>;

  const ghost = (visit?.viewpoints ?? info.viewpoints).find((v) => v.id === at)?.frame_url;

  return (
    <div className="space-y-5 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold">Film a site visit</h1>
        <p className="text-sm text-muted-foreground">
          Work <Link href={`/work?id=${encodeURIComponent(workId)}`} className="underline">{workId}</Link>. Film at the site,
          in this page: a video from the gallery is not accepted. Start at the first fixed viewpoint, walk the site, stop at
          each viewpoint, and come back to the first.
        </p>
      </div>

      {!info.site && (
        <p className="card p-4 text-sm">
          This work has no submitted cost estimate form with a map pin yet, so the page cannot check you are at the site.
          The video is still read and compared with the site&apos;s other visits.
        </p>
      )}

      {pending.length > 0 && !filming && (
        <section className="card p-4 space-y-2">
          <h2 className="font-semibold text-sm">Waiting to upload on this phone</h2>
          {pending.map((p) => (
            <div key={p.visit_id} className="flex items-center justify-between text-sm">
              <span>
                {new Date(p.captured_at).toLocaleString("en-IN")} · {(p.video.size / 1e6).toFixed(1)} MB
              </span>
              <button className="rounded-lg border border-line px-3 py-1" onClick={() => upload(p)}>
                Upload now
              </button>
            </div>
          ))}
        </section>
      )}

      {!filming && (
        <section className="card p-5 space-y-4">
          <div className="grid sm:grid-cols-2 gap-2">
            {KINDS.map((k) => (
              <label key={k.id} className={`rounded-lg border p-3 text-sm ${chosen === k.id ? "border-ink" : "border-line"}`}>
                <input type="radio" name="kind" className="mr-2" checked={chosen === k.id} onChange={() => setKind(k.id)} />
                <span className="font-semibold">{k.label}</span>
                <span className="block text-xs text-muted-foreground">{k.help}</span>
              </label>
            ))}
          </div>
          {chosen !== "baseline" && (
            <label className="block text-sm">
              What was done since the last visit (the agency&apos;s claim, judged against the video)
              <input
                className="mt-1 w-full rounded-lg border border-line bg-surface px-3 py-2"
                value={claim}
                maxLength={500}
                onChange={(e) => setClaim(e.target.value)}
                placeholder="e.g. walls up to lintel level in all rooms"
              />
            </label>
          )}
          {chosen !== "baseline" && expected.length > 0 && (
            <p className="text-xs text-muted-foreground">
              {expected.length} viewpoints from the last visit: {expected.join(", ")}. Each one must be filmed again.
            </p>
          )}
          {error && <p className="text-sm text-high">{error}</p>}
          <button className="rounded-lg bg-ink px-4 py-2 text-sm font-semibold text-white" onClick={start}>
            Start filming
          </button>
        </section>
      )}

      <div className={filming ? "space-y-3" : "hidden"}>
        <div className="relative overflow-hidden rounded-xl bg-black">
          <video ref={video} className="w-full" playsInline muted />
          {ghost && (
            // last visit's view, faint, to line up the same viewpoint
            // eslint-disable-next-line @next/next/no-img-element
            <img src={ghost} alt="" className="pointer-events-none absolute inset-0 h-full w-full object-cover opacity-35" />
          )}
          <span className="absolute left-2 top-2 rounded bg-black/60 px-2 py-0.5 text-xs text-white">
            ● {seconds}s{at ? ` · at ${at}` : ""}
          </span>
        </div>
        <div className="flex flex-wrap gap-2">
          {(chosen === "baseline" ? [...done.map((m) => m.id), `v${done.length + 1}`] : expected).map((id) => {
            const ok = done.some((m) => m.id === id);
            const off = skipped.includes(id);
            return (
              <span key={id} className="inline-flex gap-1">
                <button
                  disabled={Boolean(at)}
                  className={`rounded-lg border px-3 py-2 text-sm ${ok ? "border-low" : "border-line"}`}
                  onClick={() => markStart(id)}
                >
                  {ok ? "✓ " : ""}At viewpoint {id}
                </button>
                {chosen !== "baseline" && !ok && (
                  <button
                    disabled={Boolean(at) || off}
                    aria-label={`Can't reach viewpoint ${id}`}
                    className="rounded-lg border border-line px-2 py-2 text-xs text-muted-foreground disabled:opacity-60"
                    onClick={() => skip(id)}
                  >
                    {off ? "Skipped" : "Can't reach"}
                  </button>
                )}
              </span>
            );
          })}
          {at && (
            <button className="rounded-lg bg-ink px-3 py-2 text-sm font-semibold text-white" onClick={markEnd}>
              Done at {at}
            </button>
          )}
        </div>
        <ul className="space-y-1 text-sm">
          {blockers.map((p) => (
            <li key={p} className="text-high">• {p}</li>
          ))}
          {tips.map((p) => (
            <li key={p} className="text-medium">• {p}</li>
          ))}
          {blockers.length === 0 && tips.length === 0 && (
            <li className="text-low">Everything needed is filmed. Stop when you are back at the first viewpoint.</li>
          )}
          {blockers.length === 0 && tips.length > 0 && (
            <li className="text-muted-foreground">
              You can still stop and upload: the tips are noted with the video, and one imperfect visit is never held against the work.
            </li>
          )}
        </ul>
        <button
          disabled={blockers.length > 0}
          className="rounded-lg bg-ink px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
          onClick={stop}
        >
          Stop and upload
        </button>
      </div>

      {status && <p className="text-sm">{status}</p>}

      {info.visits.length > 0 && (
        <section className="card p-5 space-y-2">
          <h2 className="font-semibold text-sm">Visits so far</h2>
          <ul className="space-y-1 text-sm">
            {info.visits.map((v) => (
              <li key={v.visit_id}>
                {v.captured_at ? new Date(v.captured_at).toLocaleDateString("en-IN") : "—"} · {v.kind} · {v.status}
                {v.note ? ` · ${v.note}` : ""}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
