"use client";

import Link from "next/link";
import { useEffect } from "react";

/**
 * A screen failed to render or its data could not be loaded.
 *
 * The message is deliberately about the work, not the software: an officer needs
 * to know their filters are still there and that nothing was recorded, and a
 * digest to quote if they report it. It never shows a raw stack trace.
 */
export default function AppError({
  error,
  retry,
}: {
  error: Error & { digest?: string };
  retry: () => void;
}) {
  useEffect(() => {
    // Kept local on purpose: no third-party error reporter is wired up, and the
    // engine logs what it needs on its side.
    console.error("DRISHTI screen failed:", error.message, error.digest ?? "");
  }, [error]);

  return (
    <div className="panel mx-auto max-w-lg p-5">
      <p className="eyebrow">Could not load this screen</p>
      <h1 className="mt-1 text-lg font-semibold text-foreground">
        DRISHTI could not finish loading this page
      </h1>
      <p className="mt-2 text-sm text-secondary">
        Nothing was changed and nothing was recorded. The works themselves are untouched. This is
        usually a temporary problem with the connection.
      </p>
      <div className="mt-4 flex items-center gap-2">
        <button type="button" className="btn btn-primary" onClick={() => retry()}>
          Try again
        </button>
        <Link href="/" className="btn btn-ghost">
          Back to the overview
        </Link>
      </div>
      {error.digest && (
        <p className="mt-4 border-t border-line pt-3 text-2xs text-muted">
          If you report this, quote reference <span className="tnum font-medium">{error.digest}</span>.
        </p>
      )}
    </div>
  );
}