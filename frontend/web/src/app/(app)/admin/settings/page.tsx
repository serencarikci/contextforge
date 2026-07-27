"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { z } from "zod";

import { AdminNav, AdminPageShell } from "@/components/admin";
import { LoadingBlock } from "@/components/shared/loading-block";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { adminApi } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query-keys";
import { formatDate } from "@/lib/utils";

const settingsSchema = z.object({
  quotas_json: z.string(),
  defaults_json: z.string(),
  feature_overrides_json: z.string(),
  is_active: z.boolean(),
});

type SettingsValues = z.infer<typeof settingsSchema>;

function safeStringify(value: unknown): string {
  return JSON.stringify(value ?? {}, null, 2);
}

export default function AdminSettingsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const settingsQuery = useQuery({
    queryKey: queryKeys.admin.settings,
    queryFn: () => adminApi.getSettings(),
  });

  const form = useForm<SettingsValues>({
    resolver: zodResolver(settingsSchema),
    values: settingsQuery.data
      ? {
          quotas_json: safeStringify(settingsQuery.data.quotas),
          defaults_json: safeStringify(settingsQuery.data.defaults),
          feature_overrides_json: safeStringify(
            settingsQuery.data.feature_overrides,
          ),
          is_active: settingsQuery.data.is_active,
        }
      : undefined,
  });

  const updateMutation = useMutation({
    mutationFn: (values: SettingsValues) =>
      adminApi.updateSettings({
        quotas: JSON.parse(values.quotas_json) as Record<string, unknown>,
        defaults: JSON.parse(values.defaults_json) as Record<string, unknown>,
        feature_overrides: JSON.parse(values.feature_overrides_json) as Record<
          string,
          boolean
        >,
        is_active: values.is_active,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: queryKeys.admin.settings,
      });
      toast.success(t("common.success"));
    },
    onError: () => toast.error(t("common.error")),
  });

  return (
    <AdminPageShell
      permission="admin:settings"
      title={t("admin.settings")}
      description={t("admin.settingsHint")}
    >
      <AdminNav />
      {settingsQuery.isLoading ? (
        <LoadingBlock rows={5} />
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>{t("admin.orgSettings")}</CardTitle>
            <CardDescription>
              {settingsQuery.data
                ? `${t("common.updated")}: ${formatDate(settingsQuery.data.updated_at)}`
                : t("admin.settingsHint")}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Form {...form}>
              <form
                className="space-y-4"
                onSubmit={form.handleSubmit((values) => {
                  try {
                    updateMutation.mutate(values);
                  } catch {
                    toast.error(t("admin.invalidJson"));
                  }
                })}
              >
                <FormField
                  control={form.control}
                  name="is_active"
                  render={({ field }) => (
                    <FormItem className="flex items-center justify-between rounded-md border border-border px-3 py-2">
                      <FormLabel>{t("admin.orgActive")}</FormLabel>
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
                  name="quotas_json"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t("admin.quotas")}</FormLabel>
                      <FormControl>
                        <Textarea rows={6} className="font-mono text-xs" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="defaults_json"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t("admin.defaults")}</FormLabel>
                      <FormControl>
                        <Textarea rows={6} className="font-mono text-xs" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="feature_overrides_json"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t("admin.featureOverrides")}</FormLabel>
                      <FormControl>
                        <Textarea rows={6} className="font-mono text-xs" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <Button type="submit" disabled={updateMutation.isPending}>
                  {t("common.save")}
                </Button>
              </form>
            </Form>
          </CardContent>
        </Card>
      )}
    </AdminPageShell>
  );
}
