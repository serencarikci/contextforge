"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { DataTable } from "@/components/admin/data-table";
import { PermissionGuard } from "@/components/providers/permission-guard";
import { LoadingBlock } from "@/components/shared/loading-block";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/ui/empty-state";
import { customersApi } from "@/lib/api/endpoints";

export default function CustomersPage() {
  const { t } = useTranslation();
  const query = useQuery({
    queryKey: ["customers"],
    queryFn: () => customersApi.list({ limit: 50, offset: 0 }),
  });

  return (
    <PermissionGuard permission="customer:read">
      <div className="space-y-6">
        <PageHeader title={t("nav.customers")} />
        {query.isLoading ? <LoadingBlock variant="table" /> : null}
        {query.isError ? <EmptyState title={t("common.error")} /> : null}
        {query.data ? (
          <DataTable
            columns={[
              { id: "code", header: "Code", cell: (row) => row.code },
              { id: "name", header: "Name", cell: (row) => row.name },
              { id: "status", header: t("common.status"), cell: (row) => row.status },
            ]}
            rows={query.data.items}
            rowKey={(row) => row.id}
          />
        ) : null}
      </div>
    </PermissionGuard>
  );
}
