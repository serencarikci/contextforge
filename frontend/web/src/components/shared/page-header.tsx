import * as React from "react";

import { cn } from "@/lib/utils";
import { Separator } from "@/components/ui/separator";

export interface PageHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  breadcrumbs?: React.ReactNode;
  showSeparator?: boolean;
}

function PageHeader({
  title,
  description,
  actions,
  breadcrumbs,
  showSeparator = false,
  className,
  ...props
}: PageHeaderProps) {
  return (
    <div className={cn("space-y-4", className)} {...props}>
      {breadcrumbs ? <div className="text-sm">{breadcrumbs}</div> : null}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            {title}
          </h1>
          {description ? (
            <p className="max-w-2xl text-sm text-muted-foreground">
              {description}
            </p>
          ) : null}
        </div>
        {actions ? (
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            {actions}
          </div>
        ) : null}
      </div>
      {showSeparator ? <Separator /> : null}
    </div>
  );
}

export { PageHeader };
