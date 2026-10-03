import Link from "next/link";

export default function NotFound() {
  return (
    <div className="panel mx-auto max-w-lg p-5">
      <p className="eyebrow">Not found</p>
      <h1 className="mt-1 text-lg font-semibold text-foreground">There is nothing at this address</h1>
      <p className="mt-2 text-sm text-secondary">
        If you followed a link to a work, it may be outside the area you are cleared to see. DRISHTI
        never shows an officer another district&rsquo;s works, so a work you expected but cannot open
        is usually a sign you are signed in with a narrower role.
      </p>
      <div className="mt-4 flex items-center gap-2">
        <Link href="/" className="btn btn-primary">
          Go to the overview
        </Link>
        <Link href="/queue" className="btn btn-ghost">
          Open the review queue
        </Link>
      </div>
    </div>
  );
}