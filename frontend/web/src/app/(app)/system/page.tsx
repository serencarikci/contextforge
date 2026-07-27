"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { ConfirmAction, DataTable, StatCards } from "@/components/admin";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { adminApi, ingestionApi, systemApi } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query-keys";
import { formatDate, formatNumber } from "@/lib/utils";

export default function SystemPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(20);
  const [status, setStatus] = useState("all");

  const liveQuery = useQuery({
    queryKey: queryKeys.system.live,
    queryFn: () => systemApi.liveness(),
    refetchInterval: 15_000,
  });

  const readyQuery = useQuery({
    queryKey: queryKeys.system.ready,
    queryFn: () => systemApi.readiness(),
    refetchInterval: 15_000,
  });

  const infoQuery = useQuery({
    queryKey: queryKeys.system.info,
    queryFn: () => systemApi.info(),
  });

  const opsQuery = useQuery({
    queryKey: queryKeys.admin.opsOverview,
    queryFn: () => adminApi.opsOverview(),
    refetchInterval: 20_000,
  });

  const ingestionOverviewQuery = useQuery({
    queryKey: queryKeys.admin.ingestionOverview,
    queryFn: () => adminApi.ingestionOverview(),
    refetchInterval: 20_000,
  });

  const jobsParams = useMemo(
    () => ({
      limit,
      offset: (page - 1) * limit,
      status: status === "all" ? undefined : status,
    }),
    [limit, page, status],
  );

  const jobsQuery = useQuery({
    queryKey: queryKeys.system.ingestionJobs(jobsParams),
    queryFn: () => ingestionApi.list(jobsParams),
    refetchInterval: 10_000,
  });

  const retryMutation = useMutation({
    mutationFn: ingestionApi.retry,
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["system", "ingestion-jobs"],
      });
      toast.success(t("common.success"));
    },
    onError: () => toast.error(t("common.error")),
  });

  const cancelMutation = useMutation({
    mutationFn: adminApi.cancelIngestionJob,
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["system", "ingestion-jobs"],
      });
      toast.success(t("common.success"));
    },
    onError: () => toast.error(t("common.error")),
  });

  const refreshAll = async () => {
    await Promise.all([
      liveQuery.refetch(),
      readyQuery.refetch(),
      infoQuery.refetch(),
      opsQuery.refetch(),
      ingestionOverviewQuery.refetch(),
      jobsQuery.refetch(),
    ]);
  };

  const dependencyEntries = Object.entries(readyQuery.data?.checks ?? {});

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("system.title")}
        description={t("system.description")}
        actions={
          <Button variant="outline" onClick={() => void refreshAll()}>
            <RefreshCw className="h-4 w-4" />
            {t("common.refresh")}
          </Button>
        }
      />

      <StatCards
        items={[
          {
            label: t("system.liveness"),
            value: liveQuery.data?.status ?? "—",
          },
          {
            label: t("system.readiness"),
            value: readyQuery.data?.status ?? "—",
          },
          {
            label: t("system.queues"),
            value:
              opsQuery.data?.queue_depth ??
              ingestionOverviewQuery.data?.queue_depth,
          },
          {
            label: t("system.version"),
            value: infoQuery.data?.version ?? liveQuery.data?.version ?? "—",
          },
        ]}
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>{t("system.health")}</CardTitle>
            <CardDescription>{t("system.healthHint")}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {dependencyEntries.length === 0 ? (
              <p className="text-sm text-muted-foreground">{t("common.loading")}</p>
            ) : (
              dependencyEntries.map(([name, check]) => (
                <div
                  key={name}
                  className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm"
                >
                  <div>
                    <div className="font-medium capitalize">{name}</div>
                    <div className="text-xs text-muted-foreground">
                      {formatNumber(check.latency_ms)} ms
                    </div>
                  </div>
                  <StatusBadge
                    status={check.status === "up" ? "healthy" : "failed"}
                  />
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("system.opsOverview")}</CardTitle>
            <CardDescription>{t("system.opsHint")}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">
                {t("system.environment")}
              </span>
              <span className="font-medium">
                {infoQuery.data?.environment ?? "—"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">{t("admin.llm")}</span>
              <StatusBadge
                status={opsQuery.data?.llm_configured ? "enabled" : "disabled"}
              />
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">{t("admin.retention")}</span>
              <StatusBadge
                status={
                  opsQuery.data?.retention_enabled ? "enabled" : "disabled"
                }
              />
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">{t("common.pending")}</span>
              <span className="tabular-nums">
                {formatNumber(opsQuery.data?.ingestion_pending ?? 0)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">{t("common.failed")}</span>
              <span className="tabular-nums">
                {formatNumber(opsQuery.data?.ingestion_failed ?? 0)}
              </span>
            </div>
            <div className="pt-2">
              <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {t("system.capabilities")}
              </h4>
              <div className="flex flex-wrap gap-2">
                {Object.entries(infoQuery.data?.capabilities ?? {})
                  .filter(([, enabled]) => enabled)
                  .map(([key]) => (
                    <StatusBadge
                      key={key}
                      status={key}
                      tone="info"
                      showDot={false}
                    />
                  ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle>{t("system.ingestion")}</CardTitle>
            <CardDescription>{t("system.ingestionHint")}</CardDescription>
          </div>
          <Select
            value={status}
            onValueChange={(value) => {
              setStatus(value);
              setPage(1);
            }}
          >
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t("common.all")}</SelectItem>
              <SelectItem value="pending">{t("common.pending")}</SelectItem>
              <SelectItem value="queued">queued</SelectItem>
              <SelectItem value="running">{t("common.running")}</SelectItem>
              <SelectItem value="succeeded">succeeded</SelectItem>
              <SelectItem value="failed">{t("common.failed")}</SelectItem>
              <SelectItem value="cancelled">cancelled</SelectItem>
            </SelectContent>
          </Select>
        </CardHeader>
        <CardContent>
          <DataTable
            loading={jobsQuery.isLoading}
            rows={jobsQuery.data?.items ?? []}
            rowKey={(row) => row.id}
            emptyTitle={t("system.noJobs")}
            page={page}
            limit={limit}
            total={jobsQuery.data?.pagination.total ?? 0}
            onPageChange={(nextPage, nextLimit) => {
              setPage(nextPage);
              setLimit(nextLimit);
            }}
            columns={[
              {
                id: "id",
                header: t("system.jobId"),
                cell: (row) => (
                  <span className="font-mono text-xs">
                    {row.id.slice(0, 8)}…
                  </span>
                ),
              },
              {
                id: "status",
                header: t("common.status"),
                cell: (row) => <StatusBadge status={row.status} />,
              },
              {
                id: "step",
                header: t("system.step"),
                cell: (row) => row.current_step,
              },
              {
                id: "attempts",
                header: t("system.attempts"),
                cell: (row) => `${row.attempt_count}/${row.max_attempts}`,
              },
              {
                id: "queued",
                header: t("system.queuedAt"),
                cell: (row) => formatDate(row.queued_at),
              },
              {
                id: "actions",
                header: t("common.actions"),
                cell: (row) => (
                  <div className="flex gap-1">
                    {row.status === "failed" || row.status === "cancelled" ? (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => retryMutation.mutate(row.id)}
                      >
                        {t("common.retry")}
                      </Button>
                    ) : null}
                    {row.status === "pending" ||
                    row.status === "queued" ||
                    row.status === "running" ? (
                      <ConfirmAction
                        title={t("system.cancelJob")}
                        destructive
                        confirmLabel={t("common.confirm")}
                        onConfirm={async () => {
                          await cancelMutation.mutateAsync(row.id);
                        }}
                        trigger={
                          <Button size="sm" variant="ghost">
                            {t("common.cancel")}
                          </Button>
                        }
                      />
                    ) : null}
                  </div>
                ),
              },
            ]}
          />
        </CardContent>
      </Card>
    </div>
  );
}
