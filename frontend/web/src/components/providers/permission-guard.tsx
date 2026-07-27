"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";
import type { Permission } from "@/lib/constants";
import { useSessionStore } from "@/stores/session-store";

export type PermissionRequirement = Permission | `${string}:*` | string;

function permissionAllowed(
  hasPermission: (permission: Permission | string) => boolean,
  held: readonly string[],
  required: PermissionRequirement,
): boolean {
  if (required.endsWith(":*")) {
    const prefix = required.slice(0, -1);
    return held.some((item) => item.startsWith(prefix));
  }
  return hasPermission(required);
}

export function PermissionGuard({
  permission,
  children,
  fallback,
}: {
  permission: PermissionRequirement | PermissionRequirement[];
  children: ReactNode;
  fallback?: ReactNode;
}) {
  const { t } = useTranslation();
  const hasPermission = useSessionStore((s) => s.hasPermission);
  const held = useSessionStore((s) => s.permissions);
  const required = Array.isArray(permission) ? permission : [permission];
  const allowed = required.some((item) =>
    permissionAllowed(hasPermission, held, item),
  );

  if (!allowed) {
    if (fallback) {
      return <>{fallback}</>;
    }
    return (
      <EmptyState
        title={t("auth.unauthorized")}
        description={t("auth.unauthorizedHint")}
        action={
          <Button asChild variant="outline">
            <Link href="/chat">{t("nav.chat")}</Link>
          </Button>
        }
      />
    );
  }

  return <>{children}</>;
}
