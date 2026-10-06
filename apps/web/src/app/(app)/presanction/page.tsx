"use client";

import { ArrowRight, ClipboardList } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Button } from "@/components/ui/button";

/**
 * T142: the pre-sanction check rated a recommendation from its bare details (district, type, words,
 * amount), with no form. The owner: "we are currently grading forms", so the check before sanction is
 * the work intelligence form (/work-form): the agency's whole filing, read by the four checks. This
 * address now opens the form. (The engine's POST /presanction stays for the API.)
 */
export default function PreSanctionMoved() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/work-form");
  }, [router]);
  return (
    <div className="panel mx-auto max-w-lg space-y-3 p-8 text-center">
      <ClipboardList className="mx-auto size-8 text-brand-600" />
      <p className="text-sm">
        The check before sanction is now the work intelligence form: the agency&apos;s whole filing, read by the four checks.
      </p>
      <Button asChild className="rounded-xl">
        <Link href="/work-form">
          Open the form <ArrowRight />
        </Link>
      </Button>
    </div>
  );
}
