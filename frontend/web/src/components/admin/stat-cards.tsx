"use client";

import type { ReactNode } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn, formatNumber } from "@/lib/utils";

export interface StatCardItem {
  label: string;
  value: string | number | null | undefined;
  hint?: string;
  icon?: ReactNode;
}

export function StatCards({
  items,
  loading = false,
  className,
}: {
  items: StatCardItem[];
  loading?: boolean;
  className?: string;
}) {
  if (loading) {
    return (
      <div className={cn("grid gap-4 sm:grid-cols-2 xl:grid-cols-4", className)}>
        {Array.from({ length: Math.max(items.length, 4) }).map((_, index) => (
          <Card key={index}>
            <CardHeader className="pb-2">
              <Skeleton className="h-4 w-24" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-8 w-16" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className={cn("grid gap-4 sm:grid-cols-2 xl:grid-cols-4", className)}>
      {items.map((item) => (
        <Card key={item.label}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {item.label}
            </CardTitle>
            {item.icon ? (
              <div className="text-muted-foreground">{item.icon}</div>
            ) : null}
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold tabular-nums">
              {typeof item.value === "number"
                ? formatNumber(item.value)
                : (item.value ?? "—")}
            </div>
            {item.hint ? (
              <p className="mt-1 text-xs text-muted-foreground">{item.hint}</p>
            ) : null}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
