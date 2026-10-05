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
  for (const id of ["boqBody", "milestoneBody"]) {
    const body = doc.getElementById(id);
    if (body) body.innerHTML = "";
  }
  for (let i = 0; i < rowsIn(data, "boq_desc"); i++) w.addBoqRow?.();
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
