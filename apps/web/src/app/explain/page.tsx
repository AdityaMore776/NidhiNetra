import type { Metadata } from "next";
import Explainer from "./Explainer";
import "./explain.css";

// Public on purpose: judges and visitors see the built-in examples without signing in. A
// visitor's own example goes to the live engine (POST /api/v1/explain), which needs sign-in.
export const metadata: Metadata = {
  title: "DRISHTI Visualization Engine: one work, step by step",
  description:
    "Watch an MPLADS work go through DRISHTI: private details hidden, the description read, every check at once, the score added up, and what the officer sees.",
};

export default function ExplainPage() {
  return <Explainer />;
}
