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
import { Textarea } from "@/components/ui/textarea";
import { adminApi, rolesApi } from "@/lib/api/endpoints";
import { PERMISSIONS } from "@/lib/constants";
import { queryKeys } from "@/lib/query-keys";
import { formatDate } from "@/lib/utils";

const roleSchema = z.object({
  code: z
    .string()
    .min(2)
    .max(64)
    .regex(/^[a-z][a-z0-9_]*$/),
  name: z.string().min(2).max(120),
  description: z.string().max(500).optional().or(z.literal("")),
});

const permissionsSchema = z.object({
  permission_codes: z.array(z.string()),
});

type RoleValues = z.infer<typeof roleSchema>;
type PermissionsValues = z.infer<typeof permissionsSchema>;

export default function AdminRolesPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedRoleId, setSelectedRoleId] = useState<string | null>(null);

  const rolesQuery = useQuery({
    queryKey: queryKeys.admin.roles,
    queryFn: () => rolesApi.list(),
  });

  const permissionsQuery = useQuery({
    queryKey: queryKeys.admin.rolePermissions(selectedRoleId ?? ""),
    queryFn: () => adminApi.getRolePermissions(selectedRoleId!),
    enabled: Boolean(selectedRoleId),
  });

  const createForm = useForm<RoleValues>({
    resolver: zodResolver(roleSchema),
    defaultValues: { code: "", name: "", description: "" },
  });

  const permissionsForm = useForm<PermissionsValues>({
    resolver: zodResolver(permissionsSchema),
    values: {
      permission_codes: permissionsQuery.data?.permission_codes ?? [],
    },
  });

  const createMutation = useMutation({
    mutationFn: rolesApi.create,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.admin.roles });
      setCreateOpen(false);
      createForm.reset();
      toast.success(t("common.success"));
    },
    onError: () => toast.error(t("common.error")),
  });

  const archiveMutation = useMutation({
    mutationFn: (roleId: string) => adminApi.archiveRole(roleId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.admin.roles });
      if (selectedRoleId) {
        setSelectedRoleId(null);
      }
      toast.success(t("common.success"));
    },
    onError: () => toast.error(t("common.error")),
  });

  const updatePermissionsMutation = useMutation({
    mutationFn: (payload: PermissionsValues) =>
      adminApi.updateRolePermissions(selectedRoleId!, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: queryKeys.admin.rolePermissions(selectedRoleId!),
      });
      toast.success(t("common.success"));
    },
    onError: () => toast.error(t("common.error")),
  });

  const selectedCodes = permissionsForm.watch("permission_codes");

  return (
    <AdminPageShell
      permission="admin:roles"
      title={t("admin.roles")}
      description={t("admin.rolesHint")}
      actions={
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger asChild>
            <Button>{t("admin.createRole")}</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{t("admin.createRole")}</DialogTitle>
            </DialogHeader>
            <Form {...createForm}>
              <form
                className="space-y-4"
                onSubmit={createForm.handleSubmit((values) =>
                  createMutation.mutate({
                    code: values.code,
                    name: values.name,
                    description: values.description || null,
                  }),
                )}
              >
                <FormField
                  control={createForm.control}
                  name="code"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t("admin.roleCode")}</FormLabel>
                      <FormControl>
                        <Input {...field} className="font-mono text-sm" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={createForm.control}
                  name="name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t("admin.roleName")}</FormLabel>
                      <FormControl>
                        <Input {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={createForm.control}
                  name="description"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t("common.description")}</FormLabel>
                      <FormControl>
                        <Textarea rows={3} {...field} />
                      </FormControl>
                      <FormMessage />
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
        loading={rolesQuery.isLoading}
        rows={rolesQuery.data ?? []}
        rowKey={(row) => row.id}
        emptyTitle={t("admin.noRoles")}
        columns={[
          {
            id: "name",
            header: t("admin.roleName"),
            cell: (row) => (
              <button
                type="button"
                className="text-left"
                onClick={() => setSelectedRoleId(row.id)}
              >
                <div className="font-medium text-primary hover:underline">
                  {row.name}
                </div>
                <div className="font-mono text-xs text-muted-foreground">
                  {row.code}
                </div>
              </button>
            ),
          },
          {
            id: "system",
            header: t("admin.systemRole"),
            cell: (row) =>
              row.is_system ? (
                <StatusBadge status="system" />
              ) : (
                <StatusBadge status="custom" tone="secondary" />
              ),
          },
          {
            id: "status",
            header: t("common.status"),
            cell: (row) => (
              <StatusBadge
                status={row.archived_at ? "archived" : "active"}
              />
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
            cell: (row) =>
              row.is_system || row.archived_at ? null : (
                <ConfirmAction
                  title={t("admin.archiveRole")}
                  destructive
                  confirmLabel={t("documents.archive")}
                  onConfirm={async () => { await archiveMutation.mutateAsync(row.id); }}
                  trigger={
                    <Button size="sm" variant="ghost">
                      {t("documents.archive")}
                    </Button>
                  }
                />
              ),
          },
        ]}
      />

      {selectedRoleId ? (
        <div className="rounded-md border border-border p-4">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold">{t("admin.permissions")}</h2>
            <Button variant="outline" size="sm" onClick={() => setSelectedRoleId(null)}>
              {t("common.cancel")}
            </Button>
          </div>
          <Form {...permissionsForm}>
            <form
              className="space-y-4"
              onSubmit={permissionsForm.handleSubmit((values) =>
                updatePermissionsMutation.mutate(values),
              )}
            >
              <div className="grid max-h-80 gap-2 overflow-y-auto sm:grid-cols-2 lg:grid-cols-3">
                {PERMISSIONS.map((code) => {
                  const checked = selectedCodes.includes(code);
                  return (
                    <label
                      key={code}
                      className="flex items-start gap-2 rounded-md border border-border px-3 py-2 text-sm"
                    >
                      <input
                        type="checkbox"
                        className="mt-1"
                        checked={checked}
                        onChange={(event) => {
                          const next = event.target.checked
                            ? [...selectedCodes, code]
                            : selectedCodes.filter((item) => item !== code);
                          permissionsForm.setValue("permission_codes", next, {
                            shouldDirty: true,
                          });
                        }}
                      />
                      <span className="font-mono text-xs">{code}</span>
                    </label>
                  );
                })}
              </div>
              <Button type="submit" disabled={updatePermissionsMutation.isPending}>
                {t("common.save")}
              </Button>
            </form>
          </Form>
        </div>
      ) : null}
    </AdminPageShell>
  );
}
