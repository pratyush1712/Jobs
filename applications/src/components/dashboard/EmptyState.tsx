import Link from "next/link";
import { Upload } from "lucide-react";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  title?: string;
  description?: string;
  className?: string;
}

export function EmptyState({
  title = "No jobs yet",
  description = "Import your first batch of job postings to get started.",
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center py-20 px-8 text-center",
        className,
      )}
    >
      <div className="flex items-center justify-center w-12 h-12 rounded-full bg-violet-muted mb-4">
        <Upload className="h-5 w-5 text-violet" />
      </div>
      <h3 className="text-[15px] font-semibold text-text-primary mb-1.5">
        {title}
      </h3>
      <p className="text-[13px] text-text-tertiary max-w-[280px] leading-relaxed mb-5">
        {description}
      </p>
      <Link
        href="/import"
        className={cn(
          "inline-flex items-center gap-2 px-3.5 py-2 rounded-md",
          "text-[13px] font-medium",
          "bg-violet text-white",
          "hover:opacity-90 transition-opacity",
        )}
      >
        <Upload className="h-3.5 w-3.5" />
        Import jobs
      </Link>
    </div>
  );
}
