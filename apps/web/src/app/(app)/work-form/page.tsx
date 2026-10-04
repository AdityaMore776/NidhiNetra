"use client";

import { ClipboardList, ExternalLink, HardDrive, Lock, LogIn } from "lucide-react";
import { motion } from "motion/react";
import Link from "next/link";
import { useMe } from "@/components/me";
import { PageHeader } from "@/components/nn/layout-bits";
import { Button } from "@/components/ui/button";
import FORM_HTML from "@/lib/forms/pre-sanction-work-intelligence-form";

/**
 * The Pre-Sanction Work Intelligence Form (forms/pre-sanction-work-intelligence-form.html), for
 * signed-in staff only. It is shown exactly as written, in a frame, so the site's styles never touch
 * it; its own toolbar saves drafts in this browser, validates, exports JSON and prints.
 */
export default function WorkFormPage() {
  const me = useMe();
  if (!me) return null;
  if (me.role === "PUBLIC") return <SignInFirst />;
  return <WorkForm />;
}

function WorkForm() {
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

function SignInFirst() {
  return (
    <div className="grid min-h-[60vh] place-items-center">
      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        className="panel relative max-w-md overflow-hidden p-8 text-center"
      >
        <div className="tricolor-rule absolute inset-x-0 top-0" />
        <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-brand-50 text-brand-700">
          <Lock className="size-5" />
        </span>
        <h1 className="mt-4 text-xl font-semibold tracking-[-0.02em] text-brand-950">Sign in to fill the work intelligence form</h1>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          The form is for implementing agencies and officers. The public view can see works and checks, but not this form.
        </p>
        <Button asChild className="mt-6 rounded-xl bg-brand-gradient">
          <Link href="/login">
            <LogIn /> Sign in
          </Link>
        </Button>
      </motion.div>
    </div>
  );
}
