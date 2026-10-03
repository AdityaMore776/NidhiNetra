import { Loading } from "@/components/ui";

/** The instant state shown while a screen's data is on its way. */
export default function LoadingScreen() {
  return (
    <div className="space-y-4">
      <div className="skeleton h-7 w-72" />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="skeleton h-24" />
        ))}
      </div>
      <div className="skeleton h-72" />
      <span className="sr-only">
        <Loading label="Loading" />
      </span>
    </div>
  );
}