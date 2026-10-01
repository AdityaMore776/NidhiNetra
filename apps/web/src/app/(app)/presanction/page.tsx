"use client";

import { useEffect, useState } from "react";
import { useMe } from "@/components/me";
import { api, apiPost, type PreColour, type PreOptions, type PreSanction } from "@/lib/api";

const COLOUR: Record<PreColour, { label: string; color: string }> = {
  GREEN: { label: "Green: no question found", color: "var(--low)" },
  AMBER: { label: "Amber: check before sanction", color: "var(--medium)" },
  RED: { label: "Red: needs checking before sanction", color: "var(--critical)" },
};

export default function PreSanctionCheck() {
  const me = useMe();
  const [opts, setOpts] = useState<PreOptions | null>(null);
  const [district, setDistrict] = useState(me?.district_lgd ?? "");
  const [workType, setWorkType] = useState("");
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [outside, setOutside] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PreSanction | null>(null);

  useEffect(() => {
    api<PreOptions>("/presanction/options").then((o) => {
      setOpts(o);
      if (o.districts.length === 1) setDistrict(o.districts[0].district_lgd);
    });
  }, []);

  async function check(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const rupees = Number(amount) * 100_000;
      setResult(
        await apiPost<PreSanction>("/presanction", {
          district_lgd: district,
          work_type_code: workType || null,
          description,
          amount: rupees,
          is_outside_constituency: outside,
        }),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "The check could not run.");
    } finally {
      setBusy(false);
    }
  }

  const field = "w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm";

  return (
    <div className="space-y-5 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold">Pre-sanction check</h1>
        <p className="text-sm text-muted">
          Before sanctioning a recommendation, run it through the same checks as every work on eSAKSHI: guideline rules,
          cost against similar works, and repeats or splits in the district. The answer is Green, Amber or Red with the
          reasons. It never blocks a sanction and nothing you type is saved.
        </p>
      </div>

      <form onSubmit={check} className="space-y-4 rounded-xl border border-line bg-surface p-4">
        <label className="block space-y-1">
          <span className="text-sm font-medium">District</span>
          <select className={field} value={district} onChange={(e) => setDistrict(e.target.value)} required>
            <option value="">Choose a district</option>
            {opts?.districts.map((d) => (
              <option key={d.district_lgd} value={d.district_lgd}>
                {d.name}, {d.state_name}
              </option>
            ))}
          </select>
        </label>
        <label className="block space-y-1">
          <span className="text-sm font-medium">Work type</span>
          <select className={field} value={workType} onChange={(e) => setWorkType(e.target.value)}>
            <option value="">Not sure (some checks then cannot run)</option>
            {opts?.work_types.map((t) => (
              <option key={t.code} value={t.code}>
                {t.name}
              </option>
            ))}
          </select>
        </label>
        <label className="block space-y-1">
          <span className="text-sm font-medium">Description, as in the MP&apos;s recommendation</span>
          <textarea
            className={field}
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="e.g. Construction of CC road from the school to the panchayat office in village Sundarpur"
            required
            minLength={3}
          />
        </label>
        <div className="flex flex-wrap gap-4 items-end">
          <label className="block space-y-1">
            <span className="text-sm font-medium">Amount (Rs lakh)</span>
            <input
              className={`${field} w-40`}
              type="number"
              min="0.01"
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              required
            />
          </label>
          <label className="flex items-center gap-2 text-sm pb-2">
            <input type="checkbox" checked={outside} onChange={(e) => setOutside(e.target.checked)} />
            Outside the MP&apos;s constituency
          </label>
          <button
            type="submit"
            disabled={busy || !district}
            className="ml-auto rounded-lg bg-navy px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            {busy ? "Checking…" : "Check"}
          </button>
        </div>
      </form>

      {error && <p className="text-sm" style={{ color: "var(--critical)" }}>{error}</p>}

      {result && (
        <section className="space-y-3 rounded-xl border border-line bg-surface p-4">
          <div className="flex items-center gap-3">
            <span
              className="rounded-full px-3 py-1 text-sm font-semibold text-white"
              style={{ background: COLOUR[result.colour].color }}
            >
              {COLOUR[result.colour].label}
            </span>
            <span className="text-xs text-muted">
              {result.district_name} · checked against the data of {result.as_of}
            </span>
          </div>
          <p className="text-sm">{result.advice}</p>
          {result.reasons.length > 0 && (
            <ul className="space-y-2">
              {result.reasons.map((r, i) => (
                <li key={i} className="rounded-lg border border-line p-3 text-sm">
                  <span className="font-semibold">{r.engine}</span>
                  {r.serious && (
                    <span className="ml-2 text-xs font-semibold" style={{ color: "var(--critical)" }}>
                      serious rule
                    </span>
                  )}
                  <p className="mt-1">{r.text}</p>
                </li>
              ))}
            </ul>
          )}
          {result.not_checked.length > 0 && (
            <div className="text-xs text-muted space-y-1">
              <p className="font-medium">Could not check (not a pass):</p>
              {result.not_checked.map((n, i) => (
                <p key={i}>
                  {n.engine}: {n.why}
                </p>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
