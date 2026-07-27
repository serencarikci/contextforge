"use client";

import { useQuery } from "@tanstack/react-query";
import { Library, Plus } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { DataTable } from "@/components/admin/data-table";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { knowledgeSpacesApi } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query-keys";
import { formatDate } from "@/lib/utils";

export default function KnowledgeSpacesPage() {
  const { t } = useTranslation();
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(20);
  const [status, setStatus] = useState<string>("all");
  const [search, setSearch] = useState("");

  const params = useMemo(
    () => ({
      limit,
      offset: (page - 1) * limit,
      status: status === "all" ? undefined : status,
    }),
    [limit, page, status],
  );

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: queryKeys.knowledgeSpaces.list(params),
    queryFn: () => knowledgeSpacesApi.list(params),
  });

  const rows = useMemo(() => {
    const items = data?.items ?? [];
    if (!search.trim()) {
      return items;
    }
    const q = search.trim().toLowerCase();
    return items.filter(
      (item) =>
        item.name.toLowerCase().includes(q) ||
        item.slug.toLowerCase().includes(q) ||
        (item.description ?? "").toLowerCase().includes(q),
    );
  }, [data?.items, search]);

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("knowledgeSpaces.title")}
        description={t("knowledgeSpaces.description")}
        actions={
          <Button asChild>
            <Link href="/knowledge-spaces/new">
              <Plus className="h-4 w-4" />
              {t("knowledgeSpaces.create")}
            </Link>
          </Button>
        }
      />

      <div className="flex flex-col gap-3 sm:flex-row">
        <Input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder={t("knowledgeSpaces.searchPlaceholder")}
          className="sm:max-w-sm"
        />
        <Select
          value={status}
          onValueChange={(value) => {
            setStatus(value);
            setPage(1);
          }}
        >
          <SelectTrigger className="sm:w-44">
            <SelectValue placeholder={t("common.status")} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t("common.all")}</SelectItem>
            <SelectItem value="active">{t("common.active")}</SelectItem>
            <SelectItem value="archived">{t("common.archived")}</SelectItem>
          </SelectContent>
        </Select>
        {isError ? (
          <Button variant="outline" onClick={() => void refetch()}>
            {t("common.retry")}
          </Button>
        ) : null}
      </div>

      <DataTable
        loading={isLoading}
        rows={rows}
        rowKey={(row) => row.id}
        emptyTitle={t("knowledgeSpaces.empty")}
        emptyDescription={t("knowledgeSpaces.emptyHint")}
        emptyAction={
          <Button asChild>
            <Link href="/knowledge-spaces/new">
              <Library className="h-4 w-4" />
              {t("knowledgeSpaces.create")}
            </Link>
          </Button>
        }
        page={page}
        limit={limit}
        total={data?.pagination.total ?? 0}
        onPageChange={(nextPage, nextLimit) => {
          setPage(nextPage);
          setLimit(nextLimit);
        }}
        columns={[
          {
            id: "name",
            header: t("knowledgeSpaces.name"),
            cell: (row) => (
              <Link
                href={`/knowledge-spaces/${row.id}`}
                className="font-medium text-primary hover:underline"
              >
                {row.name}
              </Link>
            ),
          },
          {
            id: "slug",
            header: t("knowledgeSpaces.slug"),
            cell: (row) => (
              <span className="font-mono text-xs text-muted-foreground">
                {row.slug}
              </span>
            ),
          },
          {
            id: "visibility",
            header: t("knowledgeSpaces.visibility"),
            cell: (row) => <StatusBadge status={row.visibility} />,
          },
          {
            id: "status",
            header: t("common.status"),
            cell: (row) => <StatusBadge status={row.status} />,
          },
          {
            id: "updated",
            header: t("common.updated"),
            cell: (row) => formatDate(row.updated_at),
          },
        ]}
      />
    </div>
  );
}
