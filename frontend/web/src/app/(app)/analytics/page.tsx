"use client";

import { useQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { toast } from "sonner";

import { StatCards } from "@/components/admin";
import { PageHeader } from "@/components/shared/page-header";
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
import { adminApi, analyticsApi } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query-keys";
import { downloadBlob, formatCurrency, formatNumber } from "@/lib/utils";

const CHART_COLORS = ["#0f766e", "#d97706", "#334155", "#0ea5e9", "#be123c"];

export default function AnalyticsPage() {
  const { t } = useTranslation();
  const [days, setDays] = useState(30);
  const [exporting, setExporting] = useState(false);

  const since = useMemo(() => {
    const date = new Date();
    date.setDate(date.getDate() - days);
    return date.toISOString();
  }, [days]);

  const usageOverviewQuery = useQuery({
    queryKey: queryKeys.admin.usageOverview,
    queryFn: () => adminApi.usageOverview(),
  });

  const trendsQuery = useQuery({
    queryKey: queryKeys.admin.usageTrends(days),
    queryFn: () => adminApi.usageTrends(days),
  });

  const tokensQuery = useQuery({
    queryKey: queryKeys.admin.usageTokens,
    queryFn: () => adminApi.usageTokens(),
  });

  const chatOverviewQuery = useQuery({
    queryKey: queryKeys.analytics.chatOverview(since),
    queryFn: () => analyticsApi.chatOverview(since),
  });

  const tokenChartData = useMemo(
    () =>
      (tokensQuery.data ?? []).map((item) => ({
        name: `${item.provider}/${item.model}`,
        prompt: item.prompt_tokens,
        completion: item.completion_tokens,
        total: item.total_tokens,
        cost:
          typeof item.estimated_cost === "string"
            ? Number(item.estimated_cost)
            : item.estimated_cost,
      })),
    [tokensQuery.data],
  );

  const totalCost = useMemo(
    () => tokenChartData.reduce((sum, item) => sum + (item.cost || 0), 0),
    [tokenChartData],
  );

  const feedbackData = useMemo(() => {
    const chat = chatOverviewQuery.data;
    if (!chat) {
      return [];
    }
    return [
      { name: t("analytics.thumbsUp"), value: chat.feedback_up_count },
      { name: t("analytics.thumbsDown"), value: chat.feedback_down_count },
    ].filter((item) => item.value > 0);
  }, [chatOverviewQuery.data, t]);

  const handleExport = async () => {
    setExporting(true);
    try {
      const blob = await adminApi.exportTokenUsage();
      downloadBlob(blob, `token-usage-${Date.now()}.csv`);
      toast.success(t("common.success"));
    } catch {
      toast.error(t("common.error"));
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("analytics.title")}
        description={t("analytics.description")}
        actions={
          <div className="flex flex-wrap gap-2">
            <Select
              value={String(days)}
              onValueChange={(value) => setDays(Number(value))}
            >
              <SelectTrigger className="w-36">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7">{t("analytics.last7")}</SelectItem>
                <SelectItem value="30">{t("analytics.last30")}</SelectItem>
                <SelectItem value="90">{t("analytics.last90")}</SelectItem>
              </SelectContent>
            </Select>
            <Button
              variant="outline"
              onClick={() => void handleExport()}
              disabled={exporting}
            >
              <Download className="h-4 w-4" />
              {t("common.export")}
            </Button>
          </div>
        }
      />

      <StatCards
        loading={usageOverviewQuery.isLoading}
        items={[
          {
            label: t("analytics.conversations"),
            value: usageOverviewQuery.data?.conversations,
          },
          {
            label: t("analytics.messages"),
            value: usageOverviewQuery.data?.messages,
          },
          {
            label: t("analytics.documents"),
            value: usageOverviewQuery.data?.documents,
          },
          {
            label: t("analytics.cost"),
            value: formatCurrency(totalCost),
          },
        ]}
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>{t("analytics.usageTrends")}</CardTitle>
            <CardDescription>{t("analytics.usageTrendsHint")}</CardDescription>
          </CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendsQuery.data ?? []}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis dataKey="day" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="conversation_count"
                  name={t("analytics.conversations")}
                  stroke={CHART_COLORS[0]}
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("analytics.tokenUsage")}</CardTitle>
            <CardDescription>{t("analytics.tokenUsageHint")}</CardDescription>
          </CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={tokenChartData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis dataKey="name" hide />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Bar
                  dataKey="prompt"
                  stackId="tokens"
                  fill={CHART_COLORS[0]}
                  name={t("analytics.promptTokens")}
                />
                <Bar
                  dataKey="completion"
                  stackId="tokens"
                  fill={CHART_COLORS[1]}
                  name={t("analytics.completionTokens")}
                />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("analytics.chatOverview")}</CardTitle>
            <CardDescription>{t("analytics.chatOverviewHint")}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">
                {t("analytics.totalMessages")}
              </span>
              <span className="font-medium tabular-nums">
                {formatNumber(chatOverviewQuery.data?.total_messages ?? 0)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">
                {t("analytics.assistantMessages")}
              </span>
              <span className="font-medium tabular-nums">
                {formatNumber(chatOverviewQuery.data?.assistant_messages ?? 0)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">
                {t("analytics.failedMessages")}
              </span>
              <span className="font-medium tabular-nums">
                {formatNumber(chatOverviewQuery.data?.failed_messages ?? 0)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">
                {t("analytics.avgLatency")}
              </span>
              <span className="font-medium tabular-nums">
                {formatNumber(
                  Math.round(chatOverviewQuery.data?.avg_latency_ms ?? 0),
                )}
                ms
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">
                {t("analytics.avgRetrieval")}
              </span>
              <span className="font-medium tabular-nums">
                {formatNumber(
                  Math.round(chatOverviewQuery.data?.avg_retrieval_ms ?? 0),
                )}
                ms
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("analytics.feedback")}</CardTitle>
            <CardDescription>{t("analytics.feedbackHint")}</CardDescription>
          </CardHeader>
          <CardContent className="h-72">
            {feedbackData.length === 0 ? (
              <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                {t("analytics.noFeedback")}
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={feedbackData}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={55}
                    outerRadius={90}
                    paddingAngle={2}
                  >
                    {feedbackData.map((_, index) => (
                      <Cell
                        key={index}
                        fill={CHART_COLORS[index % CHART_COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t("analytics.costByModel")}</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="px-2 py-2">{t("admin.provider")}</th>
                <th className="px-2 py-2">{t("admin.model")}</th>
                <th className="px-2 py-2">{t("analytics.requests")}</th>
                <th className="px-2 py-2">{t("analytics.tokenUsage")}</th>
                <th className="px-2 py-2">{t("analytics.cost")}</th>
              </tr>
            </thead>
            <tbody>
              {(tokensQuery.data ?? []).map((item) => (
                <tr
                  key={`${item.provider}-${item.model}`}
                  className="border-b border-border"
                >
                  <td className="px-2 py-2">{item.provider}</td>
                  <td className="px-2 py-2 font-mono text-xs">{item.model}</td>
                  <td className="px-2 py-2 tabular-nums">
                    {formatNumber(item.request_count)}
                  </td>
                  <td className="px-2 py-2 tabular-nums">
                    {formatNumber(item.total_tokens)}
                  </td>
                  <td className="px-2 py-2 tabular-nums">
                    {formatCurrency(item.estimated_cost)}
                  </td>
                </tr>
              ))}
              {(tokensQuery.data ?? []).length === 0 ? (
                <tr>
                  <td
                    colSpan={5}
                    className="px-2 py-8 text-center text-muted-foreground"
                  >
                    {t("common.empty")}
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
