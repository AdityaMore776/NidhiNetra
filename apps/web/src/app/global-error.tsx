"use client";

import { useEffect } from "react";

/**
 * The last line of defence: a crash in the root layout itself, or in an error
 * boundary's own render, would otherwise leave a blank page. Here it shows the
 * officer what happened and what to do next.
 *
 * Says "needs checking", never a name and never a blame: an officer reading this
 * at 6pm should be able to copy it into a ticket without embarrassment.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // nothing sensitive: the message and the digest, never a work or a person
    console.error("drishti: unhandled error", error.digest ?? "");
  }, [error]);

  return (
    <html lang="en">
      <body style={{ margin: 0, background: "var(--background, #fff)", color: "var(--foreground, #111)" }}>
        <main
          style={{
            maxWidth: "34rem",
            margin: "0 auto",
            padding: "4rem 1.5rem",
            fontFamily:
              "ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
          }}
        >
          <p
            style={{
              margin: 0,
              fontSize: "0.75rem",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "#6b6b6b",
            }}
          >
            DRISHTI
          </p>
          <h1 style={{ margin: "0.5rem 0 0", fontSize: "1.25rem", lineHeight: 1.3 }}>
            This page stopped working
          </h1>
          <p style={{ marginTop: "0.75rem", fontSize: "0.875rem", color: "#3f3f3f" }}>
            Nothing you were looking at has been changed or deleted. Nothing was scored either: this is a
            problem with the page, not with any work.
          </p>
          <div style={{ marginTop: "1.25rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            <button
              type="button"
              onClick={reset}
              style={{
                border: "1px solid #111",
                background: "#111",
                color: "#fff",
                borderRadius: "0.375rem",
                padding: "0.5rem 0.875rem",
                fontSize: "0.875rem",
                cursor: "pointer",
              }}
            >
              Try again
            </button>
            <a
              href="/queue"
              style={{
                border: "1px solid #c9c9c9",
                background: "#fff",
                color: "#111",
                borderRadius: "0.375rem",
                padding: "0.5rem 0.875rem",
                fontSize: "0.875rem",
                textDecoration: "none",
              }}
            >
              Go to the review queue
            </a>
          </div>
          {error.digest && (
            <p style={{ marginTop: "1.5rem", fontSize: "0.75rem", color: "#6b6b6b" }}>
              Quote this if you report it: <code>{error.digest}</code>
            </p>
          )}
        </main>
      </body>
    </html>
  );
}