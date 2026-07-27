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
import { Textarea } from "@/components/ui/textarea";
import { adminApi } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query-keys";
import { formatDate } from "@/lib/utils";

const promptSchema = z.object({
  name: z.string().min(2).max(120),
  version: z.string().min(1).max(40),
  language: z.string().min(2).max(10),
  content: z.string().min(1),
  activate: z.boolean(),
});

type PromptValues = z.infer<typeof promptSchema>;

export default function AdminPromptsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);

  const promptsQuery = useQuery({
    queryKey: queryKeys.admin.prompts,
    queryFn: () => adminApi.listPrompts(),
  });

  const form = useForm<PromptValues>({
    resolver: zodResolver(promptSchema),
    defaultValues: {
      name: "",
      version: "1.0.0",
      language: "en",
      content: "",
      activate: false,
    },
  });

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: queryKeys.admin.prompts });

  const createMutation = useMutation({
    mutationFn: adminApi.createPrompt,
    onSuccess: async () => {
      await invalidate();
      setOpen(false);
      form.reset();
      toast.success(t("common.success"));
    },
    onError: () => toast.error(t("common.error")),
  });

  const activateMutation = useMutation({
    mutationFn: adminApi.activatePrompt,
    onSuccess: async () => {
      await invalidate();
      toast.success(t("common.success"));
    },
    onError: () => toast.error(t("common.error")),
  });

  const deactivateMutation = useMutation({
    mutationFn: adminApi.deactivatePrompt,
    onSuccess: async () => {
      await invalidate();
      toast.success(t("common.success"));
    },
    onError: () => toast.error(t("common.error")),
  });

  const rollbackMutation = useMutation({
    mutationFn: adminApi.rollbackPrompt,
    onSuccess: async () => {
      await invalidate();
      toast.success(t("common.success"));
    },
    onError: () => toast.error(t("common.error")),
  });

  const deleteMutation = useMutation({
    mutationFn: adminApi.deletePrompt,
    onSuccess: async () => {
      await invalidate();
      toast.success(t("common.success"));
    },
    onError: () => toast.error(t("common.error")),
  });

  const previewMutation = useMutation({
    mutationFn: (templateId: string) =>
      adminApi.previewPrompt(templateId, { values: {} }),
    onSuccess: (result) => setPreview(result.rendered),
    onError: () => toast.error(t("common.error")),
  });

  return (
    <AdminPageShell
      permission="admin:prompts"
      title={t("admin.prompts")}
      description={t("admin.promptsHint")}
      actions={
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button>{t("admin.createPrompt")}</Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>{t("admin.createPrompt")}</DialogTitle>
            </DialogHeader>
            <Form {...form}>
              <form
                className="space-y-4"
                onSubmit={form.handleSubmit((values) =>
                  createMutation.mutate(values),
                )}
              >
                <div className="grid gap-4 sm:grid-cols-3">
                  <FormField
                    control={form.control}
                    name="name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t("admin.promptName")}</FormLabel>
                        <FormControl>
                          <Input {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="version"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t("admin.version")}</FormLabel>
                        <FormControl>
                          <Input {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="language"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t("common.language")}</FormLabel>
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
                  name="content"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t("admin.promptContent")}</FormLabel>
                      <FormControl>
                        <Textarea rows={8} className="font-mono text-xs" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="activate"
                  render={({ field }) => (
                    <FormItem className="flex items-center justify-between rounded-md border border-border px-3 py-2">
                      <FormLabel>{t("admin.activateOnCreate")}</FormLabel>
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
        loading={promptsQuery.isLoading}
        rows={promptsQuery.data ?? []}
        rowKey={(row) => row.id}
        emptyTitle={t("admin.noPrompts")}
        columns={[
          {
            id: "name",
            header: t("admin.promptName"),
            cell: (row) => (
              <div>
                <div className="font-medium">{row.name}</div>
                <div className="text-xs text-muted-foreground">
                  v{row.version} · {row.language}
                </div>
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
            id: "system",
            header: t("admin.systemRole"),
            cell: (row) =>
              row.is_system ? <StatusBadge status="system" /> : "—",
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
                  onClick={() => previewMutation.mutate(row.id)}
                >
                  {t("admin.preview")}
                </Button>
                {row.is_active ? (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => deactivateMutation.mutate(row.id)}
                  >
                    {t("admin.deactivate")}
                  </Button>
                ) : (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => activateMutation.mutate(row.id)}
                  >
                    {t("admin.activate")}
                  </Button>
                )}
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => rollbackMutation.mutate(row.id)}
                >
                  {t("admin.rollback")}
                </Button>
                {!row.is_system ? (
                  <ConfirmAction
                    title={t("admin.deletePrompt")}
                    destructive
                    confirmLabel={t("common.delete")}
                    onConfirm={async () => { await deleteMutation.mutateAsync(row.id); }}
                    trigger={
                      <Button size="sm" variant="ghost">
                        {t("common.delete")}
                      </Button>
                    }
                  />
                ) : null}
              </div>
            ),
          },
        ]}
      />

      {preview ? (
        <div className="rounded-md border border-border bg-muted/30 p-4">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="font-medium">{t("admin.preview")}</h3>
            <Button size="sm" variant="outline" onClick={() => setPreview(null)}>
              {t("common.cancel")}
            </Button>
          </div>
          <pre className="whitespace-pre-wrap font-mono text-xs">{preview}</pre>
        </div>
      ) : null}
    </AdminPageShell>
  );
}
