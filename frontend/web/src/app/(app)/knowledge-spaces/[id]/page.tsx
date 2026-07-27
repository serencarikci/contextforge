"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { z } from "zod";

import { ConfirmAction, DataTable, StatCards } from "@/components/admin";
import { LoadingBlock } from "@/components/shared/loading-block";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import {
  adminApi,
  documentsApi,
  knowledgeSpacesApi,
} from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query-keys";
import { formatDate, formatNumber } from "@/lib/utils";

const updateSchema = z.object({
  name: z.string().min(2).max(200),
  description: z.string().max(2000).optional().or(z.literal("")),
  visibility: z.enum(["organization", "restricted", "private"]),
});

const memberSchema = z.object({
  membership_id: z.string().uuid(),
  access_level: z.enum(["viewer", "editor", "admin"]),
});

type UpdateValues = z.infer<typeof updateSchema>;
type MemberValues = z.infer<typeof memberSchema>;

export default function KnowledgeSpaceDetailPage() {
  const { t } = useTranslation();
  const params = useParams<{ id: string }>();
  const id = params.id;
  const queryClient = useQueryClient();
  const [memberOpen, setMemberOpen] = useState(false);
  const [docPage, setDocPage] = useState(1);
  const [docLimit, setDocLimit] = useState(20);

  const spaceQuery = useQuery({
    queryKey: queryKeys.knowledgeSpaces.detail(id),
    queryFn: () => knowledgeSpacesApi.get(id),
  });

  const membershipsQuery = useQuery({
    queryKey: queryKeys.knowledgeSpaces.memberships(id, { limit: 100, offset: 0 }),
    queryFn: () =>
      knowledgeSpacesApi.listMemberships(id, { limit: 100, offset: 0 }),
  });

  const documentsQuery = useQuery({
    queryKey: queryKeys.documents.list({
      knowledge_space_id: id,
      limit: docLimit,
      offset: (docPage - 1) * docLimit,
    }),
    queryFn: () =>
      documentsApi.list({
        knowledge_space_id: id,
        limit: docLimit,
        offset: (docPage - 1) * docLimit,
      }),
  });

  const statsQuery = useQuery({
    queryKey: queryKeys.knowledgeSpaces.stats(id),
    queryFn: () => adminApi.knowledgeSpaceStats(id),
  });

  const updateForm = useForm<UpdateValues>({
    resolver: zodResolver(updateSchema),
    values: spaceQuery.data
      ? {
          name: spaceQuery.data.name,
          description: spaceQuery.data.description ?? "",
          visibility: spaceQuery.data.visibility,
        }
      : undefined,
  });

  const memberForm = useForm<MemberValues>({
    resolver: zodResolver(memberSchema),
    defaultValues: {
      membership_id: "",
      access_level: "viewer",
    },
  });

  const invalidate = async () => {
    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: queryKeys.knowledgeSpaces.detail(id),
      }),
      queryClient.invalidateQueries({
        queryKey: queryKeys.knowledgeSpaces.memberships(id),
      }),
      queryClient.invalidateQueries({
        queryKey: queryKeys.knowledgeSpaces.stats(id),
      }),
      queryClient.invalidateQueries({ queryKey: queryKeys.knowledgeSpaces.all }),
    ]);
  };

  const updateMutation = useMutation({
    mutationFn: (payload: UpdateValues) =>
      knowledgeSpacesApi.update(id, {
        name: payload.name,
        description: payload.description || null,
        visibility: payload.visibility,
      }),
    onSuccess: async () => {
      await invalidate();
      toast.success(t("common.success"));
    },
    onError: () => toast.error(t("common.error")),
  });

  const archiveMutation = useMutation({
    mutationFn: () => knowledgeSpacesApi.archive(id),
    onSuccess: async () => {
      await invalidate();
      toast.success(t("common.success"));
    },
    onError: () => toast.error(t("common.error")),
  });

  const addMemberMutation = useMutation({
    mutationFn: (payload: MemberValues) =>
      knowledgeSpacesApi.addMembership(id, payload),
    onSuccess: async () => {
      await invalidate();
      setMemberOpen(false);
      memberForm.reset({ membership_id: "", access_level: "viewer" });
      toast.success(t("common.success"));
    },
    onError: () => toast.error(t("common.error")),
  });

  const removeMemberMutation = useMutation({
    mutationFn: (membershipId: string) =>
      knowledgeSpacesApi.removeMembership(id, membershipId),
    onSuccess: async () => {
      await invalidate();
      toast.success(t("common.success"));
    },
    onError: () => toast.error(t("common.error")),
  });

  const updateAccessMutation = useMutation({
    mutationFn: ({
      membershipId,
      access_level,
    }: {
      membershipId: string;
      access_level: string;
    }) =>
      knowledgeSpacesApi.updateMembership(id, membershipId, { access_level }),
    onSuccess: async () => {
      await invalidate();
      toast.success(t("common.success"));
    },
    onError: () => toast.error(t("common.error")),
  });

  const statsItems = useMemo(
    () => [
      {
        label: t("knowledgeSpaces.documents"),
        value: statsQuery.data?.document_count,
      },
      {
        label: t("knowledgeSpaces.chunks"),
        value: statsQuery.data?.chunk_count,
      },
      {
        label: t("knowledgeSpaces.conversationLinks"),
        value: statsQuery.data?.conversation_link_count,
      },
      {
        label: t("knowledgeSpaces.members"),
        value: membershipsQuery.data?.pagination.total,
      },
    ],
    [membershipsQuery.data?.pagination.total, statsQuery.data, t],
  );

  if (spaceQuery.isLoading) {
    return <LoadingBlock rows={6} />;
  }

  if (spaceQuery.isError || !spaceQuery.data) {
    return (
      <div className="space-y-4">
        <PageHeader title={t("knowledgeSpaces.title")} />
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            {t("common.error")}
            <div className="mt-4">
              <Button variant="outline" onClick={() => void spaceQuery.refetch()}>
                {t("common.retry")}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const space = spaceQuery.data;

  return (
    <div className="space-y-6">
      <PageHeader
        title={space.name}
        description={space.description ?? t("knowledgeSpaces.detailHint")}
        actions={
          <div className="flex flex-wrap gap-2">
            <StatusBadge status={space.status} />
            {space.status === "active" ? (
              <ConfirmAction
                title={t("knowledgeSpaces.archiveConfirm")}
                description={t("knowledgeSpaces.archiveHint")}
                destructive
                confirmLabel={t("documents.archive")}
                onConfirm={async () => { await archiveMutation.mutateAsync(); }}
                trigger={
                  <Button variant="outline" disabled={archiveMutation.isPending}>
                    {t("documents.archive")}
                  </Button>
                }
              />
            ) : null}
            <Button asChild variant="outline">
              <Link href="/knowledge-spaces">{t("common.back")}</Link>
            </Button>
          </div>
        }
      />

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">{t("knowledgeSpaces.overview")}</TabsTrigger>
          <TabsTrigger value="members">{t("knowledgeSpaces.members")}</TabsTrigger>
          <TabsTrigger value="documents">{t("knowledgeSpaces.documents")}</TabsTrigger>
          <TabsTrigger value="statistics">
            {t("knowledgeSpaces.statistics")}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>{t("knowledgeSpaces.details")}</CardTitle>
                <CardDescription>
                  {t("knowledgeSpaces.slug")}:{" "}
                  <span className="font-mono">{space.slug}</span>
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <div className="flex justify-between gap-4">
                  <span className="text-muted-foreground">
                    {t("knowledgeSpaces.visibility")}
                  </span>
                  <StatusBadge status={space.visibility} />
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-muted-foreground">{t("common.created")}</span>
                  <span>{formatDate(space.created_at)}</span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-muted-foreground">{t("common.updated")}</span>
                  <span>{formatDate(space.updated_at)}</span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>{t("common.edit")}</CardTitle>
              </CardHeader>
              <CardContent>
                <Form {...updateForm}>
                  <form
                    className="space-y-4"
                    onSubmit={updateForm.handleSubmit((values) =>
                      updateMutation.mutate(values),
                    )}
                  >
                    <FormField
                      control={updateForm.control}
                      name="name"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>{t("knowledgeSpaces.name")}</FormLabel>
                          <FormControl>
                            <Input {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={updateForm.control}
                      name="description"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>
                            {t("knowledgeSpaces.descriptionLabel")}
                          </FormLabel>
                          <FormControl>
                            <Textarea rows={3} {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={updateForm.control}
                      name="visibility"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>{t("knowledgeSpaces.visibility")}</FormLabel>
                          <Select
                            value={field.value}
                            onValueChange={field.onChange}
                          >
                            <FormControl>
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              <SelectItem value="organization">
                                {t("knowledgeSpaces.visibilityOrganization")}
                              </SelectItem>
                              <SelectItem value="restricted">
                                {t("knowledgeSpaces.visibilityRestricted")}
                              </SelectItem>
                              <SelectItem value="private">
                                {t("knowledgeSpaces.visibilityPrivate")}
                              </SelectItem>
                            </SelectContent>
                          </Select>
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
          </div>
        </TabsContent>

        <TabsContent value="members" className="space-y-4">
          <div className="flex justify-end">
            <Dialog open={memberOpen} onOpenChange={setMemberOpen}>
              <DialogTrigger asChild>
                <Button>{t("knowledgeSpaces.addMember")}</Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>{t("knowledgeSpaces.addMember")}</DialogTitle>
                </DialogHeader>
                <Form {...memberForm}>
                  <form
                    className="space-y-4"
                    onSubmit={memberForm.handleSubmit((values) =>
                      addMemberMutation.mutate(values),
                    )}
                  >
                    <FormField
                      control={memberForm.control}
                      name="membership_id"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>
                            {t("knowledgeSpaces.membershipId")}
                          </FormLabel>
                          <FormControl>
                            <Input
                              {...field}
                              placeholder="00000000-0000-0000-0000-000000000000"
                              className="font-mono text-xs"
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={memberForm.control}
                      name="access_level"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>
                            {t("knowledgeSpaces.accessLevel")}
                          </FormLabel>
                          <Select
                            value={field.value}
                            onValueChange={field.onChange}
                          >
                            <FormControl>
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              <SelectItem value="viewer">viewer</SelectItem>
                              <SelectItem value="editor">editor</SelectItem>
                              <SelectItem value="admin">admin</SelectItem>
                            </SelectContent>
                          </Select>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <DialogFooter>
                      <Button
                        type="submit"
                        disabled={addMemberMutation.isPending}
                      >
                        {t("common.create")}
                      </Button>
                    </DialogFooter>
                  </form>
                </Form>
              </DialogContent>
            </Dialog>
          </div>

          <DataTable
            loading={membershipsQuery.isLoading}
            rows={membershipsQuery.data?.items ?? []}
            rowKey={(row) => row.id}
            emptyTitle={t("knowledgeSpaces.noMembers")}
            columns={[
              {
                id: "membership",
                header: t("knowledgeSpaces.membershipId"),
                cell: (row) => (
                  <span className="font-mono text-xs">{row.membership_id}</span>
                ),
              },
              {
                id: "access",
                header: t("knowledgeSpaces.accessLevel"),
                cell: (row) => (
                  <Select
                    value={row.access_level}
                    onValueChange={(value) =>
                      updateAccessMutation.mutate({
                        membershipId: row.id,
                        access_level: value,
                      })
                    }
                  >
                    <SelectTrigger className="h-8 w-32">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="viewer">viewer</SelectItem>
                      <SelectItem value="editor">editor</SelectItem>
                      <SelectItem value="admin">admin</SelectItem>
                    </SelectContent>
                  </Select>
                ),
              },
              {
                id: "created",
                header: t("common.created"),
                cell: (row) => formatDate(row.created_at),
              },
              {
                id: "actions",
                header: t("common.actions"),
                cell: (row) => (
                  <ConfirmAction
                    title={t("knowledgeSpaces.removeMember")}
                    destructive
                    confirmLabel={t("common.delete")}
                    onConfirm={async () => { await removeMemberMutation.mutateAsync(row.id); }}
                    trigger={
                      <Button variant="ghost" size="sm">
                        {t("common.delete")}
                      </Button>
                    }
                  />
                ),
              },
            ]}
          />
        </TabsContent>

        <TabsContent value="documents" className="space-y-4">
          <div className="flex justify-end">
            <Button asChild variant="outline">
              <Link href={`/documents?knowledge_space_id=${id}`}>
                {t("documents.title")}
              </Link>
            </Button>
          </div>
          <DataTable
            loading={documentsQuery.isLoading}
            rows={documentsQuery.data?.items ?? []}
            rowKey={(row) => row.id}
            emptyTitle={t("documents.empty", { defaultValue: t("common.empty") })}
            page={docPage}
            limit={docLimit}
            total={documentsQuery.data?.pagination.total ?? 0}
            onPageChange={(nextPage, nextLimit) => {
              setDocPage(nextPage);
              setDocLimit(nextLimit);
            }}
            columns={[
              {
                id: "title",
                header: t("documents.title"),
                cell: (row) => (
                  <Link
                    href={`/documents/${row.id}`}
                    className="font-medium text-primary hover:underline"
                  >
                    {row.title}
                  </Link>
                ),
              },
              {
                id: "filename",
                header: t("documents.filename", {
                  defaultValue: "Filename",
                }),
                cell: (row) => row.filename,
              },
              {
                id: "status",
                header: t("common.status"),
                cell: (row) => <StatusBadge status={row.status} />,
              },
              {
                id: "size",
                header: t("documents.size", { defaultValue: "Size" }),
                cell: (row) => `${formatNumber(row.size_bytes)} B`,
              },
              {
                id: "updated",
                header: t("common.updated"),
                cell: (row) => formatDate(row.updated_at),
              },
            ]}
          />
        </TabsContent>

        <TabsContent value="statistics" className="space-y-4">
          <StatCards items={statsItems} loading={statsQuery.isLoading} />
          {statsQuery.isError ? (
            <Button variant="outline" onClick={() => void statsQuery.refetch()}>
              {t("common.retry")}
            </Button>
          ) : null}
        </TabsContent>
      </Tabs>
    </div>
  );
}
