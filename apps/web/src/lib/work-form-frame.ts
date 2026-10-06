/**
 * The Pre-Sanction Work Intelligence Form (lib/forms/pre-sanction-work-intelligence-form) shown in a
 * frame: filling it with a filing through the form's own functions. Shared by /work-form and
 * /end-to-end, so both show the one form the agency fills.
 */

// the form's own functions (declared in its script, so global in the frame)
export type FormWindow = Window & {
  restore?: (d: Record<string, unknown>) => void;
  serialize?: () => Record<string, unknown>;
  addBoqRow?: () => void;
  addLabourRow?: () => void;
  addMilestoneRow?: () => void;
};

function rowsIn(data: Record<string, unknown>, prefix: string): number {
  const re = new RegExp(`^${prefix}_(\\d+)$`);
  return Math.max(1, ...Object.keys(data).map((k) => Number(re.exec(k)?.[1] ?? 0)));
}

/** Fill the framed form with a filing, through the form's own functions; false if it is not ready. */
export function fillForm(frame: HTMLIFrameElement | null, data: Record<string, unknown>): boolean {
  const w = frame?.contentWindow as FormWindow | null | undefined;
  const doc = frame?.contentDocument;
  if (!w || !doc || typeof w.restore !== "function") return false;
  (doc.getElementById("nidhinetraForm") as HTMLFormElement | null)?.reset();
  for (const id of ["boqBody", "labourBody", "milestoneBody"]) {
    const body = doc.getElementById(id);
    if (body) body.innerHTML = "";
  }
  for (let i = 0; i < rowsIn(data, "boq_desc"); i++) w.addBoqRow?.();
  for (let i = 0; i < rowsIn(data, "lab_trade"); i++) w.addLabourRow?.();
  for (let i = 0; i < rowsIn(data, "milestone_name"); i++) w.addMilestoneRow?.();
  w.restore({
    ...data,
    __meta: { work_id: String(data.recommendation_ref ?? "EXAMPLE") },
  });
  const status = doc.getElementById("headerStatus");
  if (status) status.textContent = "EXAMPLE FILING";
  w.scrollTo({ top: 0 });
  return true;
}

/**
 * Below `wide` (a CSS media query) the frame takes its form's full height, so a phone scrolls one
 * page instead of a box inside a page (T143); "Show in form" still scrolls the page to the field.
 * Returns a cleanup. At `wide` and above the frame keeps its own height and scrolls inside.
 */
export function fitFrame(frame: HTMLIFrameElement | null, wide: string): () => void {
  const doc = frame?.contentDocument;
  if (!frame || !doc?.documentElement) return () => {};
  const mq = window.matchMedia(wide);
  const fit = () => {
    // the body's own height (the page's scrollHeight never drops below the frame), plus the form's
    // margin above and below it
    const r = doc.body.getBoundingClientRect();
    const margin = Math.max(0, r.top + (doc.defaultView?.scrollY ?? 0));
    frame.style.height = mq.matches ? "" : `${Math.ceil(r.height + 2 * margin)}px`;
  };
  const ro = new ResizeObserver(fit);
  ro.observe(doc.body);
  mq.addEventListener("change", fit);
  fit();
  return () => {
    ro.disconnect();
    mq.removeEventListener("change", fit);
  };
}
