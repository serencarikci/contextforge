"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  FileText,
  MessageSquare,
  Users,
} from "lucide-react";
import Link from "next/link";
import { useTranslation } from "react-i18next";

import { AdminNav, AdminPageShell, StatCards } from "@/components/admin";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { adminApi } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query-keys";
import { formatNumber } from "@/lib/utils";

export default function AdminDashboardPage() {
  const { t } = useTranslation();

  const dashboardQuery = useQuery({
    queryKey: queryKeys.admin.dashboard,
    queryFn: () => adminApi.dashboard(),
  });

  const opsQuery = useQuery({
    queryKey: queryKeys.admin.opsOverview,
    queryFn: () => adminApi.opsOverview(),
  });

  const data = dashboardQuery.data;

  return (
    <AdminPageShell
      permission="admin:dashboard"
      title={t("admin.dashboard")}
      description={t("admin.dashboardHint")}
    >
      <AdminNav />
      <StatCards
        loading={dashboardQuery.isLoading}
        items={[
          {
            label: t("admin.activeMembers"),
            value: data?.active_membership_count,
            hint: `${formatNumber(data?.membership_count ?? 0)} ${t("admin.totalMembers")}`,
            icon: <Users className="h-4 w-4" />,
          },
          {
            label: t("admin.documents"),
            value: data?.document_count,
            icon: <FileText className="h-4 w-4" />,
          },
          {
            label: t("admin.conversations"),
            value: data?.conversation_count,
            icon: <MessageSquare className="h-4 w-4" />,
          },
          {
            label: t("admin.tokenUsageToday"),
            value: data?.token_usage_today,
            icon: <Activity className="h-4 w-4" />,
          },
        ]}
      />

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>{t("admin.ingestion")}</CardTitle>
            <CardDescription>{t("admin.ingestionHint")}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">{t("common.pending")}</span>
              <span className="font-medium tabular-nums">
                {formatNumber(data?.ingestion_pending ?? 0)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">{t("common.running")}</span>
              <span className="font-medium tabular-nums">
                {formatNumber(data?.ingestion_running ?? 0)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">{t("common.failed")}</span>
              <span className="font-medium tabular-nums">
                {formatNumber(data?.ingestion_failed ?? 0)}
              </span>
            </div>
            <Button asChild variant="outline" size="sm">
              <Link href="/system">{t("nav.system")}</Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("admin.opsSnapshot")}</CardTitle>
            <CardDescription>{t("admin.opsHint")}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">{t("system.health")}</span>
              <span className="font-medium capitalize">
                {opsQuery.data?.readiness_status ?? "—"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">{t("system.queues")}</span>
              <span className="font-medium tabular-nums">
                {formatNumber(opsQuery.data?.queue_depth ?? 0)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">{t("admin.llm")}</span>
              <span className="font-medium">
                {opsQuery.data?.llm_configured
                  ? t("common.enabled")
                  : t("common.disabled")}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">{t("admin.knowledgeSpaces")}</span>
              <span className="font-medium tabular-nums">
                {formatNumber(data?.knowledge_space_count ?? 0)}
              </span>
            </div>
            <div className="flex flex-wrap gap-2 pt-1">
              <Button asChild variant="outline" size="sm">
                <Link href="/admin/users">{t("admin.users")}</Link>
              </Button>
              <Button asChild variant="outline" size="sm">
                <Link href="/admin/audit">{t("admin.audit")}</Link>
              </Button>
              <Button asChild variant="outline" size="sm">
                <Link href="/analytics">{t("nav.analytics")}</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </AdminPageShell>
  );
}
