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
import { adminApi } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query-keys";
import { formatDate } from "@/lib/utils";

const providerSchema = z.object({
  provider: z.string().min(1).max(64),
  model: z.string().min(1).max(120),
  base_url: z.union([z.string().url(), z.literal("")]).optional(),
  api_key: z.string().optional().or(z.literal("")),
  temperature: z.number().min(0).max(2),
  max_tokens: z.number().int().min(1).max(128000),
  timeout_seconds: z.number().int().min(1).max(600),
  max_retries: z.number().int().min(0).max(10),
  is_active: z.boolean(),
});

type ProviderValues = z.infer<typeof providerSchema>;

export default function AdminLlmProvidersPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);

  const providersQuery = useQuery({
    queryKey: queryKeys.admin.llmProviders,
    queryFn: () => adminApi.listLlmProviders(),
  });

  const form = useForm<ProviderValues>({
    resolver: zodResolver(providerSchema),
    defaultValues: {
      provider: "openai",
      model: "gpt-4o-mini",
      base_url: "",
      api_key: "",
      temperature: 0.2,
      max_tokens: 2048,
      timeout_seconds: 60,
      max_retries: 2,
      is_active: true,
    },
  });

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: queryKeys.admin.llmProviders });

  const createMutation = useMutation({
    mutationFn: (values: ProviderValues) =>
      adminApi.createLlmProvider({
        provider: values.provider,
        model: values.model,
        base_url: values.base_url || null,
        api_key: values.api_key || null,
        temperature: values.temperature,
        max_tokens: values.max_tokens,
        timeout_seconds: values.timeout_seconds,
        max_retries: values.max_retries,
        is_active: values.is_active,
      }),
    onSuccess: async () => {
      await invalidate();
      setOpen(false);
      form.reset();
      toast.success(t("common.success"));
    },
    onError: () => toast.error(t("common.error")),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      adminApi.updateLlmProvider(id, { is_active }),
    onSuccess: async () => {
      await invalidate();
      toast.success(t("common.success"));
    },
    onError: () => toast.error(t("common.error")),
  });

  const testMutation = useMutation({
    mutationFn: adminApi.testLlmProvider,
    onSuccess: (result) => {
      toast.success(
        `${result.status}${result.latency_ms != null ? ` · ${result.latency_ms}ms` : ""}`,
      );
    },
    onError: () => toast.error(t("common.error")),
  });

  const deleteMutation = useMutation({
    mutationFn: adminApi.deleteLlmProvider,
    onSuccess: async () => {
      await invalidate();
      toast.success(t("common.success"));
    },
    onError: () => toast.error(t("common.error")),
  });

  return (
    <AdminPageShell
      permission="admin:llm"
      title={t("admin.llm")}
      description={t("admin.llmHint")}
      actions={
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button>{t("admin.addProvider")}</Button>
          </DialogTrigger>
          <DialogContent className="max-w-xl">
            <DialogHeader>
              <DialogTitle>{t("admin.addProvider")}</DialogTitle>
            </DialogHeader>
            <Form {...form}>
              <form
                className="space-y-4"
                onSubmit={form.handleSubmit((values) =>
                  createMutation.mutate(values),
                )}
              >
                <div className="grid gap-4 sm:grid-cols-2">
                  <FormField
                    control={form.control}
                    name="provider"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t("admin.provider")}</FormLabel>
                        <FormControl>
                          <Input {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="model"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t("admin.model")}</FormLabel>
                        <FormControl>
                          <Input {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
                <FormField
                  control={form.control}
                  name="base_url"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t("admin.baseUrl")}</FormLabel>
                      <FormControl>
                        <Input {...field} placeholder="https://..." />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="api_key"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t("admin.apiKey")}</FormLabel>
                      <FormControl>
                        <Input type="password" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <div className="grid gap-4 sm:grid-cols-3">
                  <FormField
                    control={form.control}
                    name="temperature"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t("admin.temperature")}</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            step="0.1"
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
                    name="max_tokens"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t("admin.maxTokens")}</FormLabel>
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
                    name="timeout_seconds"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t("admin.timeout")}</FormLabel>
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
                </div>
                <FormField
                  control={form.control}
                  name="is_active"
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
      }
    >
      <AdminNav />
      <DataTable
        loading={providersQuery.isLoading}
        rows={providersQuery.data ?? []}
        rowKey={(row) => row.id}
        emptyTitle={t("admin.noProviders")}
        columns={[
          {
            id: "provider",
            header: t("admin.provider"),
            cell: (row) => (
              <div>
                <div className="font-medium">{row.provider}</div>
                <div className="text-xs text-muted-foreground">{row.model}</div>
              </div>
            ),
          },
          {
            id: "status",
            header: t("common.status"),
            cell: (row) => (
              <StatusBadge status={row.is_active ? "active" : "inactive"} />
            ),
          },
          {
            id: "key",
            header: t("admin.apiKey"),
            cell: (row) =>
              row.api_key_set ? (
                <span className="font-mono text-xs">
                  {row.api_key_hint ?? "••••"}
                </span>
              ) : (
                "—"
              ),
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
              <div className="flex flex-wrap gap-1">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => testMutation.mutate(row.id)}
                  disabled={testMutation.isPending}
                >
                  {t("admin.test")}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() =>
                    toggleMutation.mutate({
                      id: row.id,
                      is_active: !row.is_active,
                    })
                  }
                >
                  {row.is_active ? t("admin.deactivate") : t("admin.activate")}
                </Button>
                <ConfirmAction
                  title={t("admin.deleteProvider")}
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
    </AdminPageShell>
  );
}
