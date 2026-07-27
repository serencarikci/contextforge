import * as React from "react";

import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";

export interface LoadingBlockProps extends React.HTMLAttributes<HTMLDivElement> {
  rows?: number;
  showHeader?: boolean;
  variant?: "list" | "card" | "table";
  label?: string;
}

function LoadingBlock({
  rows = 4,
  showHeader = true,
  variant = "list",
  label,
  className,
  ...props
}: LoadingBlockProps) {
  if (label) {
    return (
      <div
        className={cn(
          "flex min-h-[12rem] flex-col items-center justify-center gap-3 text-sm text-muted-foreground",
          className,
        )}
        role="status"
        aria-live="polite"
        {...props}
      >
        <Skeleton className="h-8 w-8 rounded-full" />
        <p>{label}</p>
      </div>
    );
  }
  if (variant === "card") {
    return (
      <div
        className={cn(
          "grid gap-4 sm:grid-cols-2 lg:grid-cols-3",
          className
        )}
        {...props}
      >
        {Array.from({ length: rows }).map((_, index) => (
          <div
            key={index}
            className="space-y-3 rounded-md border border-border bg-card p-4"
          >
            <Skeleton className="h-4 w-2/3" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-4/5" />
            <Skeleton className="h-8 w-24" />
          </div>
        ))}
      </div>
    );
  }

  if (variant === "table") {
    return (
      <div
        className={cn(
          "overflow-hidden rounded-md border border-border",
          className
        )}
        {...props}
      >
        {showHeader ? (
          <div className="flex gap-4 border-b border-border bg-muted/40 px-4 py-3">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-4 w-20" />
            <Skeleton className="ml-auto h-4 w-16" />
          </div>
        ) : null}
        <div className="divide-y divide-border">
          {Array.from({ length: rows }).map((_, index) => (
            <div key={index} className="flex gap-4 px-4 py-3">
              <Skeleton className="h-4 w-28" />
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-4 w-24" />
              <Skeleton className="ml-auto h-4 w-16" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className={cn("space-y-3", className)} {...props}>
      {showHeader ? (
        <div className="space-y-2">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-72" />
        </div>
      ) : null}
      {Array.from({ length: rows }).map((_, index) => (
        <Skeleton key={index} className="h-10 w-full" />
      ))}
    </div>
  );
}

export { LoadingBlock };
