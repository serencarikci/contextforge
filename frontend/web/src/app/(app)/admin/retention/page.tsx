"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Play } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { z } from "zod";

import {
  AdminNav,
  AdminPageShell,
  ConfirmAction,
  DataTable,
} from "@/components/admin";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { adminApi } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query-keys";
import { formatDate, formatNumber } from "@/lib/utils";

const policySchema = z.object({
  resource_type: z.string().min(2).max(80),
  retention_days: z.number().int().min(1).max(3650),
  soft_delete_first: z.boolean(),
  enabled: z.boolean(),
});

type PolicyValues = z.infer<typeof policySchema>;

export default function AdminRetentionPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);

  const policiesQuery = useQuery({
    queryKey: queryKeys.admin.retentionPolicies,
    queryFn: () => adminApi.listRetentionPolicies(),
  });

  const runsQuery = useQuery({
    queryKey: queryKeys.admin.retentionRuns,
    queryFn: () => adminApi.listRetentionRuns(),
  });

  const form = useForm<PolicyValues>({
    resolver: zodResolver(policySchema),
    defaultValues: {
      resource_type: "documents",
      retention_days: 90,
      soft_delete_first: true,
      enabled: true,
    },
  });

  const invalidate = async () => {
    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: queryKeys.admin.retentionPolicies,
      }),
      queryClient.invalidateQueries({
        queryKey: queryKeys.admin.retentionRuns,
      }),
    ]);
  };

  const createMutation = useMutation({
    mutationFn: adminApi.createRetentionPolicy,
    onSuccess: async () => {
      await invalidate();
      setOpen(false);
      form.reset();
      toast.success(t("common.success"));
    },
    onError: () => toast.error(t("common.error")),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      adminApi.updateRetentionPolicy(id, { enabled }),
    onSuccess: async () => {
      await invalidate();
      toast.success(t("common.success"));
    },
    onError: () => toast.error(t("common.error")),
  });

  const deleteMutation = useMutation({
    mutationFn: adminApi.deleteRetentionPolicy,
    onSuccess: async () => {
      await invalidate();
      toast.success(t("common.success"));
    },
    onError: () => toast.error(t("common.error")),
  });

  const runMutation = useMutation({
    mutationFn: (policyId?: string) =>
      adminApi.runRetention(policyId ? { policy_id: policyId } : {}),
    onSuccess: async () => {
      await invalidate();
      toast.success(t("admin.retentionStarted"));
    },
    onError: () => toast.error(t("common.error")),
  });

  return (
    <AdminPageShell
      permission="admin:retention"
      title={t("admin.retention")}
      description={t("admin.retentionHint")}
      actions={
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => runMutation.mutate(undefined)}
            disabled={runMutation.isPending}
          >
            <Play className="h-4 w-4" />
            {t("admin.runRetention")}
          </Button>
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button>{t("admin.createPolicy")}</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>{t("admin.createPolicy")}</DialogTitle>
              </DialogHeader>
              <Form {...form}>
                <form
                  className="space-y-4"
                  onSubmit={form.handleSubmit((values) =>
                    createMutation.mutate(values),
                  )}
                >
                  <FormField
                    control={form.control}
                    name="resource_type"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t("admin.resourceType")}</FormLabel>
                        <FormControl>
                          <Input {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="retention_days"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t("admin.retentionDays")}</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            value={field.value}
                            onChange={(event) =>
                              field.onChange(Number(event.target.value))
                            }
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="soft_delete_first"
                    render={({ field }) => (
                      <FormItem className="flex items-center justify-between rounded-md border border-border px-3 py-2">
                        <FormLabel>{t("admin.softDeleteFirst")}</FormLabel>
                        <FormControl>
                          <Switch
                            checked={field.value}
                            onCheckedChange={field.onChange}
                          />
                        </FormControl>
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="enabled"
                    render={({ field }) => (
                      <FormItem className="flex items-center justify-between rounded-md border border-border px-3 py-2">
                        <FormLabel>{t("common.enabled")}</FormLabel>
                        <FormControl>
                          <Switch
                            checked={field.value}
                            onCheckedChange={field.onChange}
                          />
                        </FormControl>
                      </FormItem>
                    )}
                  />
                  <DialogFooter>
                    <Button type="submit" disabled={createMutation.isPending}>
                      {t("common.create")}
                    </Button>
                  </DialogFooter>
                </form>
              </Form>
            </DialogContent>
          </Dialog>
        </div>
      }
    >
      <AdminNav />
      <Tabs defaultValue="policies">
        <TabsList>
          <TabsTrigger value="policies">{t("admin.policies")}</TabsTrigger>
          <TabsTrigger value="runs">{t("admin.runs")}</TabsTrigger>
        </TabsList>
        <TabsContent value="policies" className="mt-4">
          <DataTable
            loading={policiesQuery.isLoading}
            rows={policiesQuery.data ?? []}
            rowKey={(row) => row.id}
            emptyTitle={t("admin.noPolicies")}
            columns={[
              {
                id: "resource",
                header: t("admin.resourceType"),
                cell: (row) => row.resource_type,
              },
              {
                id: "days",
                header: t("admin.retentionDays"),
                cell: (row) => formatNumber(row.retention_days),
              },
              {
                id: "soft",
                header: t("admin.softDeleteFirst"),
                cell: (row) =>
                  row.soft_delete_first ? t("common.yes") : t("common.no"),
              },
              {
                id: "status",
                header: t("common.status"),
                cell: (row) => (
                  <StatusBadge status={row.enabled ? "enabled" : "disabled"} />
                ),
              },
              {
                id: "actions",
                header: t("common.actions"),
                cell: (row) => (
                  <div className="flex gap-1">
                    <Switch
                      checked={row.enabled}
                      onCheckedChange={(enabled) =>
                        toggleMutation.mutate({ id: row.id, enabled })
                      }
                    />
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => runMutation.mutate(row.id)}
                    >
                      {t("admin.run")}
                    </Button>
                    <ConfirmAction
                      title={t("admin.deletePolicy")}
                      destructive
                      confirmLabel={t("common.delete")}
                      onConfirm={async () => {
                        await deleteMutation.mutateAsync(row.id);
                      }}
                      trigger={
                        <Button size="sm" variant="ghost">
                          {t("common.delete")}
                        </Button>
                      }
                    />
                  </div>
                ),
              },
            ]}
          />
        </TabsContent>
        <TabsContent value="runs" className="mt-4">
          <DataTable
            loading={runsQuery.isLoading}
            rows={runsQuery.data ?? []}
            rowKey={(row) => row.id}
            emptyTitle={t("admin.noRuns")}
            columns={[
              {
                id: "started",
                header: t("admin.startedAt"),
                cell: (row) => formatDate(row.started_at),
              },
              {
                id: "status",
                header: t("common.status"),
                cell: (row) => <StatusBadge status={row.status} />,
              },
              {
                id: "deleted",
                header: t("admin.deletedCount"),
                cell: (row) => formatNumber(row.deleted_count),
              },
              {
                id: "finished",
                header: t("admin.finishedAt"),
                cell: (row) => formatDate(row.finished_at),
              },
              {
                id: "policy",
                header: t("admin.policy"),
                cell: (row) => (
                  <span className="font-mono text-xs">{row.policy_id}</span>
                ),
              },
            ]}
          />
        </TabsContent>
      </Tabs>
    </AdminPageShell>
  );
}
