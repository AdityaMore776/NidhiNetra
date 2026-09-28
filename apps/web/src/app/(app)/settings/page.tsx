"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button, Panel, PanelHeader, StatusLabel } from "@/components/kit";
import { useMe } from "@/components/me";
import { api, type Summary } from "@/lib/api";
import { supabase } from "@/lib/supabase";

const ROLE_DESC: Record<NonNullable<ReturnType<typeof useMe>>["role"], string> = {
  MINISTRY: "Full national scope — works across every district.",
  DISTRICT: "Scoped to a single district — works within your assigned district only.",
  FIELD: "Scoped to a single district — works within your assigned district only.",
};

export default function SettingsPage() {
  const me = useMe();
  const router = useRouter();
  const [snapshot, setSnapshot] = useState<string | null>(null);

  useEffect(() => {
    api<Summary>("/dashboard/summary")
      .then((s) => setSnapshot(s.snapshot_date))
      .catch(() => setSnapshot(null));
  }, []);

  async function signOut() {
    await supabase()?.auth.signOut();
    router.replace("/login");
  }

  if (!me) return null;

  const rows: { label: string; value: React.ReactNode }[] = [
    { label: "Signed-in name", value: me.name || "—" },
    { label: "Role", value: <StatusLabel tone="info">{me.role}</StatusLabel> },
    { label: "District scope", value: me.district_lgd ? <span className="tnum">{me.district_lgd}</span> : "All districts" },
    { label: "User ID", value: <span className="tnum text-xs">{me.user_id}</span> },
    { label: "Data snapshot", value: snapshot ? <span className="tnum">{snapshot}</span> : "—" },
  ];

  return (
    <div className="max-w-3xl space-y-6">
      <header className="border-b-2 border-strong pb-4">
        <h1 className="text-2xl font-bold tracking-tight md:text-3xl">Settings</h1>
        <p className="mt-1.5 text-sm leading-relaxed text-muted">
          Your account and access. Visibility is enforced by the server according to your role — it cannot be changed from
          here.
        </p>
      </header>

      <Panel as="section">
        <PanelHeader title="Account" desc="Read-only session details" />
        <dl className="divide-y divide-line">
          {rows.map((r) => (
            <div key={r.label} className="flex items-center justify-between gap-4 px-4 py-3">
              <dt className="label">{r.label}</dt>
              <dd className="text-sm">{r.value}</dd>
            </div>
          ))}
        </dl>
      </Panel>

      <Panel as="section">
        <PanelHeader title="Access scope" />
        <div className="space-y-3 p-4 text-sm">
          <p>{ROLE_DESC[me.role]}</p>
          <p className="text-muted">
            Every query you make is filtered on the server to this scope. The interface never relies on hiding to protect
            data.
          </p>
        </div>
      </Panel>

      <Panel as="section">
        <PanelHeader title="Session" />
        <div className="flex flex-wrap items-center justify-between gap-3 p-4">
          <p className="text-sm text-muted">Sign out of this device.</p>
          <Button variant="danger" onClick={signOut}>
            Sign out
          </Button>
        </div>
      </Panel>

      <p className="text-[11px] text-muted">
        DRISHTI · Risk-intelligence layer for MPLADS. SIH 2026 · SIH26102 · Team NeuralNexus.
      </p>
    </div>
  );
}
