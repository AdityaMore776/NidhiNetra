"use client";

import { CheckCircle2, CircleSlash, FileSearch, Loader2, type LucideIcon, OctagonAlert, ShieldCheck, TriangleAlert } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";
import AITextLoading from "@/components/kokonutui/ai-text-loading";
import { useMe } from "@/components/me";
import { PageHeader } from "@/components/nn/layout-bits";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { api, apiPost, type PreColour, type PreOptions, type PreSanction } from "@/lib/api";
import { cn } from "@/lib/utils";

const NOT_SURE = "NOT_SURE";

const COLOUR: Record<PreColour, { label: string; short: string; color: string; soft: string; icon: LucideIcon }> = {
  GREEN: { label: "Green: no question found", short: "Green", color: "var(--low)", soft: "var(--low-soft)", icon: CheckCircle2 },
  AMBER: { label: "Amber: check before sanction", short: "Amber", color: "var(--medium)", soft: "var(--medium-soft)", icon: TriangleAlert },
  RED: { label: "Red: needs checking before sanction", short: "Red", color: "var(--critical)", soft: "var(--critical-soft)", icon: OctagonAlert },
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

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Act · Before money moves"
        title="Pre-sanction"
        accent="check."
        lead="Before sanctioning a recommendation, run it through the same checks as every work on eSAKSHI: guideline rules, cost against similar works, and repeats or splits in the district. The answer is Green, Amber or Red with the reasons. It never blocks a sanction and nothing you type is saved."
      />

      <div className="grid gap-6 lg:grid-cols-12">
        <form onSubmit={check} className="panel space-y-5 p-5 sm:p-6 lg:col-span-6">
          <div className="flex items-center gap-3">
            <span className="grid size-10 place-items-center rounded-xl bg-brand-50 text-brand-700">
              <FileSearch className="size-5" />
            </span>
            <div>
              <div className="font-semibold text-brand-950">The recommendation</div>
              <div className="text-xs text-muted-foreground">As the MP sent it</div>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">District</Label>
            <Select value={district} onValueChange={setDistrict} required>
              <SelectTrigger className="h-11 w-full rounded-xl bg-white">
                <SelectValue placeholder={opts ? "Choose a district" : "Loading districts…"} />
              </SelectTrigger>
              <SelectContent className="max-h-80 rounded-xl" data-lenis-prevent>
                {opts?.districts.map((d) => (
                  <SelectItem key={d.district_lgd} value={d.district_lgd}>
                    {d.name}, {d.state_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">Work type</Label>
            <Select value={workType || NOT_SURE} onValueChange={(v) => setWorkType(v === NOT_SURE ? "" : v)}>
              <SelectTrigger className="h-11 w-full rounded-xl bg-white">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="max-h-80 rounded-xl" data-lenis-prevent>
                <SelectItem value={NOT_SURE}>Not sure (some checks then cannot run)</SelectItem>
                {opts?.work_types.map((t) => (
                  <SelectItem key={t.code} value={t.code}>
                    {t.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="desc" className="text-xs text-muted-foreground">
              Description, as in the MP&apos;s recommendation
            </Label>
            <Textarea
              id="desc"
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. Construction of CC road from the school to the panchayat office in village Sundarpur"
              required
              minLength={3}
              className="rounded-xl bg-white"
            />
          </div>

          <div className="flex flex-wrap items-end gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="amount" className="text-xs text-muted-foreground">
                Amount (₹ lakh)
              </Label>
              <Input
                id="amount"
                className="h-11 w-44 rounded-xl bg-white"
                type="number"
                min="0.01"
                step="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                required
              />
            </div>
            <label className="flex h-11 items-center gap-2.5 rounded-xl border bg-white px-3 text-sm">
              <Checkbox checked={outside} onCheckedChange={(v) => setOutside(v === true)} />
              Outside the MP&apos;s constituency
            </label>
          </div>

          <Button type="submit" disabled={busy || !district} className="h-11 w-full rounded-xl bg-brand-gradient text-[15px] font-semibold">
            {busy ? (
              <>
                <Loader2 className="animate-spin" /> Checking…
              </>
            ) : (
              <>
                <ShieldCheck /> Run the check
              </>
            )}
          </Button>
          {error && <p className="rounded-lg px-3 py-2 text-sm text-critical" style={{ background: "var(--critical-soft)" }}>{error}</p>}
        </form>

        <div className="lg:col-span-6">
          <AnimatePresence mode="wait">
            {busy ? (
              <motion.div key="busy" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="panel grid h-full min-h-80 place-items-center p-8">
                <AITextLoading texts={["Reading the description…", "Checking the guideline rules…", "Comparing the cost…", "Looking for repeats and splits…"]} interval={900} />
              </motion.div>
            ) : result ? (
              <motion.section
                key="result"
                initial={{ opacity: 0, y: 16, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
                className="panel overflow-hidden"
              >
                <Verdict result={result} />
                <div className="space-y-4 p-5 sm:p-6">
                  <p className="text-[15px] leading-relaxed">{result.advice}</p>
                  {result.reasons.length > 0 && (
                    <ul className="space-y-2">
                      {result.reasons.map((r, i) => (
                        <motion.li
                          key={i}
                          initial={{ opacity: 0, x: -8 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: 0.3 + i * 0.08 }}
                          className="rounded-xl border bg-white p-3.5 text-sm"
                        >
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-brand-950">{r.engine}</span>
                            {r.serious && (
                              <span className="rounded-full px-2 py-0.5 text-[10px] font-semibold text-critical" style={{ background: "var(--critical-soft)" }}>
                                serious rule
                              </span>
                            )}
                          </div>
                          <p className="mt-1 leading-relaxed text-foreground/85">{r.text}</p>
                        </motion.li>
                      ))}
                    </ul>
                  )}
                  {result.not_checked.length > 0 && (
                    <div className="rounded-xl border border-dashed p-3.5 text-xs text-muted-foreground">
                      <p className="mb-1.5 flex items-center gap-1.5 font-semibold text-foreground">
                        <CircleSlash className="size-3.5" /> Could not check (not a pass)
                      </p>
                      {result.not_checked.map((n, i) => (
                        <p key={i} className="leading-relaxed">
                          <span className="font-medium text-foreground">{n.engine}:</span> {n.why}
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              </motion.section>
            ) : (
              <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="panel relative grid h-full min-h-80 place-items-center overflow-hidden p-8 text-center">
                <div className="absolute inset-0 dot-bg opacity-60 [mask-image:radial-gradient(ellipse_at_center,black,transparent_70%)]" />
                <div className="relative">
                  <div className="mx-auto flex w-fit gap-3">
                    {(["GREEN", "AMBER", "RED"] as PreColour[]).map((c, i) => (
                      <motion.span
                        key={c}
                        className="size-5 rounded-full"
                        style={{ background: COLOUR[c].color }}
                        animate={{ opacity: [0.25, 1, 0.25] }}
                        transition={{ duration: 2.4, repeat: Infinity, delay: i * 0.8 }}
                      />
                    ))}
                  </div>
                  <div className="mt-4 font-semibold text-brand-950">The answer appears here</div>
                  <p className="mt-1 max-w-xs text-sm text-muted-foreground">Green, Amber or Red, with the reasons and anything that could not be checked.</p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

function Verdict({ result }: { result: PreSanction }) {
  const c = COLOUR[result.colour];
  return (
    <div className="relative flex items-center gap-5 overflow-hidden p-5 sm:p-6" style={{ background: c.soft }}>
      <div className="relative grid size-16 shrink-0 place-items-center">
        <motion.span
          className="absolute inset-0 rounded-full"
          style={{ background: c.color }}
          initial={{ scale: 0.6, opacity: 0.5 }}
          animate={{ scale: [1, 1.5, 1], opacity: [0.35, 0, 0.35] }}
          transition={{ duration: 2.2, repeat: Infinity }}
        />
        <motion.span
          className={cn("relative grid size-14 place-items-center rounded-full text-white shadow-lg")}
          style={{ background: c.color }}
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 260, damping: 16 }}
        >
          <c.icon className="size-7" />
        </motion.span>
      </div>
      <div>
        <div className="text-xl font-semibold tracking-[-0.02em]" style={{ color: c.color }}>
          {c.label}
        </div>
        <div className="mt-1 text-xs text-muted-foreground">
          {result.district_name} · checked against the data of <span className="num">{result.as_of}</span>
        </div>
      </div>
    </div>
  );
}
