"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { DataTable } from "@/components/admin/data-table";
import { PermissionGuard } from "@/components/providers/permission-guard";
import { LoadingBlock } from "@/components/shared/loading-block";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/ui/empty-state";
import { projectsApi } from "@/lib/api/endpoints";

export default function ProjectsPage() {
  const { t } = useTranslation();
  const query = useQuery({
    queryKey: ["projects"],
    queryFn: () => projectsApi.list({ limit: 50, offset: 0 }),
  });

  return (
    <PermissionGuard permission="project:read">
      <div className="space-y-6">
        <PageHeader title={t("nav.projects")} />
        {query.isLoading ? <LoadingBlock variant="table" /> : null}
        {query.isError ? <EmptyState title={t("common.error")} /> : null}
        {query.data ? (
          <DataTable
            columns={[
              { id: "key", header: "Key", cell: (row) => row.key },
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
