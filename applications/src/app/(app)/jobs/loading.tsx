/**
 * Skeleton shown while the Jobs page chunk loads.
 * Mimics the real layout so there's minimal layout shift.
 */
export default function JobsLoading() {
  return (
    <div className="flex-1 flex flex-col overflow-hidden animate-pulse">
      {/* Header placeholder */}
      <div className="flex items-center justify-between px-6 h-14 border-b border-border shrink-0">
        <div className="h-5 w-24 rounded bg-surface-3" />
        <div className="h-8 w-20 rounded-lg bg-surface-3" />
      </div>

      {/* Filter bar placeholder */}
      <div className="px-5 py-3 border-b border-border shrink-0">
        <div className="h-10 w-full rounded-lg bg-surface-3" />
      </div>

      {/* Sort bar placeholder */}
      <div className="flex items-center gap-2 px-5 py-2.5 border-b border-border shrink-0">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-7 w-24 rounded-md bg-surface-3" />
        ))}
      </div>

      {/* Rows placeholder */}
      <div className="flex-1 overflow-hidden">
        {Array.from({ length: 12 }).map((_, i) => (
          <div
            key={i}
            className="flex items-center gap-4 px-5 py-3.5 border-b border-divider"
          >
            <div className="h-9 w-9 rounded-lg bg-surface-3 shrink-0" />
            <div className="flex-1 space-y-2">
              <div className="h-4 w-48 rounded bg-surface-3" />
              <div className="h-3 w-32 rounded bg-surface-3" />
            </div>
            <div className="h-5 w-16 rounded bg-surface-3" />
          </div>
        ))}
      </div>
    </div>
  );
}
