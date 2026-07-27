"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
import { Textarea } from "@/components/ui/textarea";
import { adminApi } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query-keys";
import { formatDate } from "@/lib/utils";

const flagSchema = z.object({
  key: z
    .string()
    .min(2)
    .max(80)
    .regex(/^[a-z][a-z0-9_.-]*$/),
  description: z.string().max(500).optional().or(z.literal("")),
  enabled: z.boolean(),
  global_flag: z.boolean(),
  value_json: z.string().optional().or(z.literal("")),
});

type FlagValues = z.infer<typeof flagSchema>;

export default function AdminFeatureFlagsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);

  const flagsQuery = useQuery({
    queryKey: queryKeys.admin.featureFlags,
    queryFn: () => adminApi.listFeatureFlags(),
  });

  const resolvedQuery = useQuery({
    queryKey: queryKeys.admin.featureFlagsResolved,
    queryFn: () => adminApi.resolvedFeatureFlags(),
  });

  const form = useForm<FlagValues>({
    resolver: zodResolver(flagSchema),
    defaultValues: {
      key: "",
      description: "",
      enabled: false,
      global_flag: false,
      value_json: "{}",
    },
  });

  const invalidate = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.admin.featureFlags }),
      queryClient.invalidateQueries({
        queryKey: queryKeys.admin.featureFlagsResolved,
      }),
    ]);
  };

  const createMutation = useMutation({
    mutationFn: (values: FlagValues) => {
      let value: Record<string, unknown> = {};
      if (values.value_json?.trim()) {
        value = JSON.parse(values.value_json) as Record<string, unknown>;
      }
      return adminApi.createFeatureFlag({
        key: values.key,
        description: values.description || null,
        enabled: values.enabled,
        global_flag: values.global_flag,
        value,
      });
    },
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
      adminApi.updateFeatureFlag(id, { enabled }),
    onSuccess: async () => {
      await invalidate();
      toast.success(t("common.success"));
    },
    onError: () => toast.error(t("common.error")),
  });

  const deleteMutation = useMutation({
    mutationFn: adminApi.deleteFeatureFlag,
    onSuccess: async () => {
      await invalidate();
      toast.success(t("common.success"));
    },
    onError: () => toast.error(t("common.error")),
  });

  const resolvedEntries = Object.entries(resolvedQuery.data?.flags ?? {});

  return (
    <AdminPageShell
      permission="admin:settings"
      title={t("admin.featureFlags")}
      description={t("admin.featureFlagsHint")}
      actions={
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button>{t("admin.createFlag")}</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{t("admin.createFlag")}</DialogTitle>
            </DialogHeader>
            <Form {...form}>
              <form
                className="space-y-4"
                onSubmit={form.handleSubmit((values) => {
                  try {
                    createMutation.mutate(values);
                  } catch {
                    toast.error(t("admin.invalidJson"));
                  }
                })}
              >
                <FormField
                  control={form.control}
                  name="key"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t("admin.flagKey")}</FormLabel>
                      <FormControl>
                        <Input {...field} className="font-mono text-sm" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="description"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t("common.description")}</FormLabel>
                      <FormControl>
                        <Textarea rows={2} {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="value_json"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t("admin.flagValue")}</FormLabel>
                      <FormControl>
                        <Textarea rows={3} className="font-mono text-xs" {...field} />
                      </FormControl>
                      <FormMessage />
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
                <FormField
                  control={form.control}
                  name="global_flag"
                  render={({ field }) => (
                    <FormItem className="flex items-center justify-between rounded-md border border-border px-3 py-2">
                      <FormLabel>{t("admin.globalFlag")}</FormLabel>
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
      }
    >
      <AdminNav />
      <DataTable
        loading={flagsQuery.isLoading}
        rows={flagsQuery.data ?? []}
        rowKey={(row) => row.id}
        emptyTitle={t("admin.noFlags")}
        columns={[
          {
            id: "key",
            header: t("admin.flagKey"),
            cell: (row) => (
              <div>
                <div className="font-mono text-sm">{row.key}</div>
                <div className="text-xs text-muted-foreground">
                  {row.description ?? "—"}
                </div>
              </div>
            ),
          },
          {
            id: "enabled",
            header: t("common.status"),
            cell: (row) => (
              <StatusBadge
                status={row.enabled_globally ? "enabled" : "disabled"}
              />
            ),
          },
          {
            id: "scope",
            header: t("admin.scope"),
            cell: (row) =>
              row.organization_id ? t("admin.orgScoped") : t("admin.globalFlag"),
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
                <Switch
                  checked={row.enabled_globally}
                  onCheckedChange={(enabled) =>
                    toggleMutation.mutate({ id: row.id, enabled })
                  }
                />
                <ConfirmAction
                  title={t("admin.deleteFlag")}
                  destructive
                  confirmLabel={t("common.delete")}
                  onConfirm={async () => { await deleteMutation.mutateAsync(row.id); }}
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

      <Card>
        <CardHeader>
          <CardTitle>{t("admin.resolvedFlags")}</CardTitle>
          <CardDescription>{t("admin.resolvedFlagsHint")}</CardDescription>
        </CardHeader>
        <CardContent>
          {resolvedQuery.isLoading ? (
            <p className="text-sm text-muted-foreground">{t("common.loading")}</p>
          ) : resolvedEntries.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t("common.empty")}</p>
          ) : (
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {resolvedEntries.map(([key, enabled]) => (
                <div
                  key={key}
                  className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm"
                >
                  <span className="font-mono text-xs">{key}</span>
                  <StatusBadge status={enabled ? "enabled" : "disabled"} />
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </AdminPageShell>
  );
}
