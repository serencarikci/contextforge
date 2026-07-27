"use client";

import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { AdminNav, AdminPageShell, DataTable } from "@/components/admin";
import { StatusBadge } from "@/components/shared/status-badge";
import { Input } from "@/components/ui/input";
import { listOrganizations } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query-keys";
import { formatDate } from "@/lib/utils";
import { useSessionStore } from "@/stores/session-store";

export default function AdminOrganizationsPage() {
  const { t } = useTranslation();
  const organizationId = useSessionStore((s) => s.organizationId);
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(20);
  const [search, setSearch] = useState("");

  const params = useMemo(
    () => ({
      limit,
      offset: (page - 1) * limit,
    }),
    [limit, page],
  );

  const orgsQuery = useQuery({
    queryKey: queryKeys.organizations.list(params),
    queryFn: () => listOrganizations(params),
  });

  const rows = useMemo(() => {
    const items = orgsQuery.data?.items ?? [];
    if (!search.trim()) {
      return items;
    }
    const q = search.trim().toLowerCase();
    return items.filter(
      (org) =>
        org.name.toLowerCase().includes(q) || org.slug.toLowerCase().includes(q),
    );
  }, [orgsQuery.data?.items, search]);

  return (
    <AdminPageShell
      permission="admin:organizations"
      title={t("admin.organizations")}
      description={t("admin.organizationsHint")}
    >
      <AdminNav />
      <Input
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        placeholder={t("admin.searchOrganizations")}
        className="sm:max-w-sm"
      />
      <DataTable
        loading={orgsQuery.isLoading}
        rows={rows}
        rowKey={(row) => row.id}
        emptyTitle={t("admin.noOrganizations")}
        page={page}
        limit={limit}
        total={orgsQuery.data?.pagination.total ?? 0}
        onPageChange={(nextPage, nextLimit) => {
          setPage(nextPage);
          setLimit(nextLimit);
        }}
        columns={[
          {
            id: "name",
            header: t("admin.orgName"),
            cell: (row) => (
              <div>
                <div className="font-medium">
                  {row.name}
                  {row.id === organizationId ? (
                    <span className="ml-2 text-xs text-muted-foreground">
                      ({t("admin.currentOrg")})
                    </span>
                  ) : null}
                </div>
                <div className="font-mono text-xs text-muted-foreground">
                  {row.slug}
                </div>
              </div>
            ),
          },
          {
            id: "status",
            header: t("common.status"),
            cell: (row) => <StatusBadge status={row.status} />,
          },
          {
            id: "created",
            header: t("common.created"),
            cell: (row) => formatDate(row.created_at),
          },
          {
            id: "updated",
            header: t("common.updated"),
            cell: (row) => formatDate(row.updated_at),
          },
        ]}
      />
    </AdminPageShell>
  );
}
