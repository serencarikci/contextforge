"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import {
  AdminNav,
  AdminPageShell,
  ConfirmAction,
  DataTable,
} from "@/components/admin";
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
import { adminApi } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query-keys";
import { formatDate } from "@/lib/utils";

export default function AdminUsersPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(20);
  const [status, setStatus] = useState("all");
  const [search, setSearch] = useState("");

  const params = useMemo(
    () => ({
      limit,
      offset: (page - 1) * limit,
      status: status === "all" ? undefined : status,
    }),
    [limit, page, status],
  );

  const usersQuery = useQuery({
    queryKey: queryKeys.admin.users(params),
    queryFn: () => adminApi.listUsers(params),
  });

  const activateMutation = useMutation({
    mutationFn: (userId: string) => adminApi.activateUser(userId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      toast.success(t("common.success"));
    },
    onError: () => toast.error(t("common.error")),
  });

  const deactivateMutation = useMutation({
    mutationFn: (userId: string) => adminApi.deactivateUser(userId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      toast.success(t("common.success"));
    },
    onError: () => toast.error(t("common.error")),
  });

  const rows = useMemo(() => {
    const items = usersQuery.data?.items ?? [];
    if (!search.trim()) {
      return items;
    }
    const q = search.trim().toLowerCase();
    return items.filter(
      (user) =>
        user.email.toLowerCase().includes(q) ||
        user.display_name.toLowerCase().includes(q),
    );
  }, [search, usersQuery.data?.items]);

  return (
    <AdminPageShell
      permission="admin:users"
      title={t("admin.users")}
      description={t("admin.usersHint")}
    >
      <AdminNav />
      <div className="flex flex-col gap-3 sm:flex-row">
        <Input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder={t("admin.searchUsers")}
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
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t("common.all")}</SelectItem>
            <SelectItem value="active">{t("common.active")}</SelectItem>
            <SelectItem value="suspended">{t("common.suspended")}</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <DataTable
        loading={usersQuery.isLoading}
        rows={rows}
        rowKey={(row) => row.id}
        emptyTitle={t("admin.noUsers")}
        page={page}
        limit={limit}
        total={usersQuery.data?.pagination.total ?? 0}
        onPageChange={(nextPage, nextLimit) => {
          setPage(nextPage);
          setLimit(nextLimit);
        }}
        columns={[
          {
            id: "name",
            header: t("admin.displayName"),
            cell: (row) => (
              <div>
                <div className="font-medium">{row.display_name}</div>
                <div className="text-xs text-muted-foreground">{row.email}</div>
              </div>
            ),
          },
          {
            id: "status",
            header: t("common.status"),
            cell: (row) => <StatusBadge status={row.status} />,
          },
          {
            id: "membership",
            header: t("admin.membership"),
            cell: (row) => <StatusBadge status={row.membership_status} />,
          },
          {
            id: "language",
            header: t("common.language"),
            cell: (row) => row.preferred_language,
          },
          {
            id: "updated",
            header: t("common.updated"),
            cell: (row) => formatDate(row.updated_at),
          },
          {
            id: "actions",
            header: t("common.actions"),
            cell: (row) => (
              <div className="flex gap-1">
                {row.status !== "active" ? (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => activateMutation.mutate(row.id)}
                    disabled={activateMutation.isPending}
                  >
                    {t("admin.activate")}
                  </Button>
                ) : (
                  <ConfirmAction
                    title={t("admin.deactivateUser")}
                    description={row.email}
                    destructive
                    confirmLabel={t("admin.deactivate")}
                    onConfirm={async () => { await deactivateMutation.mutateAsync(row.id); }}
                    trigger={
                      <Button size="sm" variant="ghost">
                        {t("admin.deactivate")}
                      </Button>
                    }
                  />
                )}
              </div>
            ),
          },
        ]}
      />
    </AdminPageShell>
  );
}
