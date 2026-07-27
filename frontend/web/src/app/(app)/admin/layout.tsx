"use client";

import type { ReactNode } from "react";

import { PermissionGuard } from "@/components/providers/permission-guard";

export default function AdminLayout({ children }: { children: ReactNode }) {
  return <PermissionGuard permission="admin:*">{children}</PermissionGuard>;
}
