import * as React from "react";

import { Badge, type BadgeProps } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export type StatusTone =
  | "default"
  | "success"
  | "warning"
  | "destructive"
  | "info"
  | "secondary"
  | "accent";

const STATUS_VARIANT_MAP: Record<
  StatusTone,
  NonNullable<BadgeProps["variant"]>
> = {
  default: "default",
  success: "success",
  warning: "warning",
  destructive: "destructive",
  info: "info",
  secondary: "secondary",
  accent: "accent",
};

const STATUS_ALIASES: Record<string, StatusTone> = {
  active: "success",
  enabled: "success",
  healthy: "success",
  completed: "success",
  succeeded: "success",
  ready: "success",
  success: "success",
  running: "info",
  processing: "info",
  streaming: "info",
  pending: "warning",
  queued: "warning",
  uploaded: "warning",
  warning: "warning",
  degraded: "warning",
  failed: "destructive",
  error: "destructive",
  cancelled: "secondary",
  canceled: "secondary",
  disabled: "secondary",
  inactive: "secondary",
  draft: "secondary",
  archived: "secondary",
  deleted: "secondary",
  skipped: "secondary",
};

export interface StatusBadgeProps extends Omit<BadgeProps, "variant"> {
  status: string;
  label?: string;
  tone?: StatusTone;
  showDot?: boolean;
}

function resolveTone(status: string, tone?: StatusTone): StatusTone {
  if (tone) return tone;
  const key = status.trim().toLowerCase().replace(/[\s_]+/g, "-");
  return STATUS_ALIASES[key] ?? "default";
}

function StatusBadge({
  status,
  label,
  tone,
  showDot = true,
  className,
  ...props
}: StatusBadgeProps) {
  const resolvedTone = resolveTone(status, tone);
  const display = label ?? status;

  return (
    <Badge
      variant={STATUS_VARIANT_MAP[resolvedTone]}
      className={cn("gap-1.5 capitalize", className)}
      {...props}
    >
      {showDot ? (
        <span
          className="h-1.5 w-1.5 shrink-0 rounded-sm bg-current opacity-80"
          aria-hidden
        />
      ) : null}
      {display}
    </Badge>
  );
}

export { StatusBadge };
