"use client";

import { ClipboardList, ExternalLink, FlaskConical, HardDrive } from "lucide-react";
import { motion } from "motion/react";
import { PageHeader } from "@/components/nn/layout-bits";
import { Button } from "@/components/ui/button";
import FORM_HTML from "@/lib/forms/pre-sanction-work-intelligence-form";

/**
 * The Pre-Sanction Work Intelligence Form (forms/pre-sanction-work-intelligence-form.html), open to
 * everyone as a mock: it is shown exactly as written, in a frame, so the site's styles never touch it;
 * its own toolbar saves drafts in this browser, validates, exports JSON and prints. Nothing is sent.
 */
export default function WorkFormPage() {
  function openInNewTab() {
    // a blob page has this site's origin, so the drafts saved here are there too
    const url = URL.createObjectURL(new Blob([FORM_HTML], { type: "text/html" }));
    window.open(url, "_blank", "noopener");
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Act · Before sanction"
        title="Work intelligence"
        accent="form."
        lead="The work's facts, collected once at sanction and in a form the agents can read: identity, site and map, duplicates and splits, the estimate line by line, timeline, clearances and the site-progress baseline."
        actions={
          <Button variant="outline" className="rounded-xl" onClick={openInNewTab}>
            <ExternalLink /> Open in a new tab
          </Button>
        }
      />

      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1.5 rounded-full border bg-white px-3 py-1">
          <FlaskConical className="size-3.5 text-brand-600" />
          Mock form: try it freely, nothing is sent to NidhiNetra
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full border bg-white px-3 py-1">
          <HardDrive className="size-3.5 text-brand-600" />
          Drafts are saved in this browser only
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full border bg-white px-3 py-1">
          <ClipboardList className="size-3.5 text-brand-600" />
          Use the form&apos;s own toolbar to save, validate, export or print
        </span>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
        className="panel overflow-hidden"
      >
        <iframe
          title="NidhiNetra — Pre-Sanction Work Intelligence Form"
          srcDoc={FORM_HTML}
          className="block h-[calc(100svh-6rem)] min-h-[640px] w-full border-0 bg-[#eef2f7]"
        />
      </motion.div>
    </div>
  );
}
