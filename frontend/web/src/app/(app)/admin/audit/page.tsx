"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { AdminPageShell } from "@/components/admin/admin-page-shell";
import { DataTable } from "@/components/admin/data-table";
import { LoadingBlock } from "@/components/shared/loading-block";
import { EmptyState } from "@/components/ui/empty-state";
import { auditApi } from "@/lib/api/endpoints";

export default function AdminAuditPage() {
  const { t } = useTranslation();
  const query = useQuery({
    queryKey: ["audit", "list"],
    queryFn: () => auditApi.list({ limit: 50, offset: 0 }),
  });

  return (
    <AdminPageShell permission="admin:audit" title={t("admin.audit")}>
      {query.isLoading ? <LoadingBlock variant="table" /> : null}
      {query.isError ? <EmptyState title={t("common.error")} /> : null}
      {query.data ? (
        <DataTable
          columns={[
            { id: "occurred_at", header: "When", cell: (row) => String(row.occurred_at) },
            { id: "action", header: "Action", cell: (row) => row.action },
            { id: "resource_type", header: "Resource", cell: (row) => row.resource_type },
            {
              id: "actor_user_id",
              header: "Actor",
              cell: (row) => row.actor_user_id ?? "—",
            },
          ]}
          rows={query.data.items}
          rowKey={(row) => row.id}
        />
      ) : null}
    </AdminPageShell>
  );
}
