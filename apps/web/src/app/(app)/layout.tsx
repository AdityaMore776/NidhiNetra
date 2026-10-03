"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { MeContext } from "@/components/me";
import { api, ApiError, type Me } from "@/lib/api";
import { Denied, Loading } from "@/components/ui";

type MeState =
  | { kind: "loading" }
  | { kind: "ready"; me: Me }
  /** signed in, but this account has no DRISHTI role */
  | { kind: "forbidden"; why: string }
  /** not signed in, or the session ended */
  | { kind: "signed-out" };

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [state, setState] = useState<MeState>({ kind: "loading" });

  useEffect(() => {
    const ac = new AbortController();
    api<Me>("/me", undefined, ac.signal)
      .then((me) => setState({ kind: "ready", me }))
      .catch((e: unknown) => {
        if (e instanceof DOMException && e.name === "AbortError") return;
        const status = e instanceof ApiError ? e.status : 0;
        if (status === 401) router.replace("/login");
        else if (status === 403) setState({ kind: "forbidden", why: (e as Error).message });
        // any other failure is a fault on our side, not a reason to sign the officer out
        else setState({ kind: "signed-out" });
      });
    return () => ac.abort();
  }, [router]);

  if (state.kind === "loading") return <div className="grid min-h-screen place-items-center"><Loading label="Checking your access" /></div>;
  if (state.kind === "forbidden") return <Denied message={state.why} />;
  if (state.kind === "signed-out") {
    return (
      <div className="grid min-h-screen place-items-center p-6">
        <div className="panel max-w-md p-5 text-center">
          <h1 className="text-base font-semibold">DRISHTI could not reach the data</h1>
          <p className="mt-2 text-sm text-secondary">
            Your session may have ended, or the service is temporarily unreachable. Nothing you
            were looking at has been lost.
          </p>
          <button
            type="button"
            className="btn btn-primary mt-4"
            onClick={() => router.replace("/login")}
          >
            Go to sign in
          </button>
        </div>
      </div>
    );
  }

  return (
    <MeContext.Provider value={state.me}>
      <AppShell me={state.me}>{children}</AppShell>
    </MeContext.Provider>
  );
}