/**
 * Skeleton shown while the job detail page chunk loads.
 * Mimics the two-column layout to avoid layout shift.
 */
export default function JobDetailLoading() {
  return (
    <div className="flex-1 flex flex-col overflow-hidden animate-pulse">
      {/* Header */}
      <div className="flex items-center gap-3 px-6 h-12 border-b border-border shrink-0">
        <div className="h-4 w-4 rounded bg-surface-3" />
        <div className="h-4 w-48 rounded bg-surface-3" />
      </div>

      {/* Body: two columns */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left content */}
        <div className="flex-1 p-6 space-y-6">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-surface-3" />
            <div className="space-y-2">
              <div className="h-5 w-56 rounded bg-surface-3" />
              <div className="h-3 w-36 rounded bg-surface-3" />
            </div>
          </div>
          <div className="space-y-2">
            <div className="h-3 w-full rounded bg-surface-3" />
            <div className="h-3 w-full rounded bg-surface-3" />
            <div className="h-3 w-3/4 rounded bg-surface-3" />
          </div>
          <div className="flex flex-wrap gap-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-6 w-20 rounded-md bg-surface-3" />
            ))}
          </div>
        </div>

        {/* Right panel */}
        <div className="w-[300px] shrink-0 border-l border-border p-4 space-y-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="space-y-1.5">
              <div className="h-3 w-16 rounded bg-surface-3" />
              <div className="h-8 w-full rounded-md bg-surface-3" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
