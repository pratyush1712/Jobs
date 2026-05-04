import { cn } from "@/lib/utils";

interface PageHeaderProps {
  title: string;
  description?: string;
  children?: React.ReactNode;
  className?: string;
}

export function PageHeader({
  title,
  description,
  children,
  className,
}: PageHeaderProps) {
  return (
    <header
      className={cn(
        "flex items-center justify-between px-6 h-14 shrink-0",
        "border-b border-border bg-background/90 backdrop-blur-sm",
        className,
      )}
    >
      <div className="flex items-center gap-3">
        <h1 className="text-base font-semibold text-foreground tracking-tight">
          {title}
        </h1>
        {description && (
          <>
            <span className="text-border text-sm">/</span>
            <span className="text-sm text-muted-foreground">{description}</span>
          </>
        )}
      </div>
      {children && <div className="flex items-center gap-2">{children}</div>}
    </header>
  );
}
