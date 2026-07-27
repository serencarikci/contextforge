"use client";

import type { ReactNode } from "react";

import {
  PermissionGuard,
  type PermissionRequirement,
} from "@/components/providers/permission-guard";
import { PageHeader } from "@/components/shared/page-header";

export function AdminPageShell({
  permission = "admin:*",
  title,
  description,
  actions,
  children,
}: {
  permission?: PermissionRequirement | PermissionRequirement[];
  title: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <PermissionGuard permission={permission}>
      <div className="space-y-6">
        <PageHeader title={title} description={description} actions={actions} />
        {children}
      </div>
    </PermissionGuard>
  );
}
