"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, Trash2, Upload } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import {
  DocumentFilters,
  type DocumentFiltersValue,
} from "@/components/documents/document-filters";
import { DocumentTable } from "@/components/documents/document-table";
import { PermissionGuard } from "@/components/providers/permission-guard";
import { LoadingBlock } from "@/components/shared/loading-block";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";
import { Pagination } from "@/components/ui/pagination";
import { adminApi, documentsApi, knowledgeSpacesApi } from "@/lib/api/endpoints";
import type { Document } from "@/lib/types/api";
import { useSessionStore } from "@/stores/session-store";

function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const handle = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(handle);
  }, [value, delayMs]);

  return debounced;
}

function DocumentsPageContent() {
  const { t } = useTranslation();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const hasPermission = useSessionStore((s) => s.hasPermission);
  const sessionKnowledgeSpaceId = useSessionStore((s) => s.knowledgeSpaceId);
  const canCreate = hasPermission("document:create");
  const canDelete = hasPermission("document:delete");
  const canAdminBulk = hasPermission("admin:documents");

  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(20);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [filters, setFilters] = useState<DocumentFiltersValue>({
    query: "",
    status: "all",
    knowledgeSpaceId: sessionKnowledgeSpaceId ?? "all",
  });

  const debouncedQuery = useDebouncedValue(filters.query, 300);
  const offset = (page - 1) * limit;
  const highlightId = searchParams.get("highlight");

  const spacesQuery = useQuery({
    queryKey: ["knowledge-spaces-options"],
    queryFn: () => knowledgeSpacesApi.list({ limit: 100, offset: 0, status: "active" }),
  });

  const documentsQuery = useQuery({
    queryKey: [
      "documents",
      page,
      limit,
      debouncedQuery,
      filters.status,
      filters.knowledgeSpaceId,
    ],
    queryFn: () =>
      documentsApi.list({
        limit,
        offset,
        query: debouncedQuery.trim() || undefined,
        knowledge_space_id:
          filters.knowledgeSpaceId === "all" ? undefined : filters.knowledgeSpaceId,
        status: filters.status === "all" ? undefined : filters.status,
      }),
  });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["documents"] });
  };

  const deleteMutation = useMutation({
    mutationFn: async (ids: string[]) => {
      if (canAdminBulk && ids.length > 1) {
        return adminApi.documentsBulkDelete({ document_ids: ids });
      }
      await Promise.all(ids.map((id) => documentsApi.remove(id)));
      return { processed: ids.length, skipped: 0, job_ids: [] as string[] };
    },
    onSuccess: (result) => {
      setSelectedIds([]);
      invalidate();
      toast.success(`${result.processed} deleted`);
    },
    onError: (error: Error) => toast.error(error.message || t("common.error")),
  });

  const reprocessMutation = useMutation({
    mutationFn: async (ids: string[]) => {
      if (!canAdminBulk) {
        throw new Error("Bulk reprocess requires admin:documents permission");
      }
      return adminApi.documentsBulkReprocess({ document_ids: ids });
    },
    onSuccess: (result) => {
      setSelectedIds([]);
      invalidate();
      toast.success(`${result.processed} ${t("documents.reprocess").toLowerCase()}`);
    },
    onError: (error: Error) => toast.error(error.message || t("common.error")),
  });

  const handleDownload = async (document: Document) => {
    try {
      const blob = await documentsApi.download(document.id);
      const url = URL.createObjectURL(blob);
      const anchor = window.document.createElement("a");
      anchor.href = url;
      anchor.download = document.filename || `${document.title}.bin`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : t("common.error"));
    }
  };

  const documents = documentsQuery.data?.items ?? [];
  const total = documentsQuery.data?.pagination.total ?? 0;
  const filteredDocuments =
    filters.status === "all"
      ? documents
      : documents.filter((document) => document.status === filters.status);

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("documents.title")}
        description={t("documents.searchPlaceholder")}
        showSeparator
        actions={
          canCreate ? (
            <Button asChild>
              <Link href="/documents/upload">
                <Upload className="h-4 w-4" />
                {t("documents.upload")}
              </Link>
            </Button>
          ) : null
        }
      />

      <DocumentFilters
        value={filters}
        onChange={(value) => {
          setPage(1);
          setFilters(value);
        }}
        knowledgeSpaces={(spacesQuery.data?.items ?? []).map((space) => ({
          id: space.id,
          name: space.name,
        }))}
      />

      {selectedIds.length > 0 ? (
        <div className="flex flex-wrap items-center gap-2 rounded-md border border-border bg-muted/40 px-3 py-2">
          <span className="text-sm text-muted-foreground">
            {selectedIds.length} selected
          </span>
          {canAdminBulk ? (
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={reprocessMutation.isPending}
              onClick={() => reprocessMutation.mutate(selectedIds)}
            >
              <RefreshCw className="h-4 w-4" />
              {t("documents.reprocess")}
            </Button>
          ) : null}
          {canDelete ? (
            <Button
              type="button"
              size="sm"
              variant="destructive"
              disabled={deleteMutation.isPending}
              onClick={() => {
                if (window.confirm(t("common.delete"))) {
                  deleteMutation.mutate(selectedIds);
                }
              }}
            >
              <Trash2 className="h-4 w-4" />
              {t("common.delete")}
            </Button>
          ) : null}
        </div>
      ) : null}

      {documentsQuery.isLoading ? (
        <LoadingBlock variant="table" rows={8} />
      ) : documentsQuery.isError ? (
        <EmptyState
          title={t("common.error")}
          description={(documentsQuery.error as Error).message}
          action={
            <Button type="button" variant="outline" onClick={() => void documentsQuery.refetch()}>
              {t("common.retry")}
            </Button>
          }
        />
      ) : filteredDocuments.length === 0 ? (
        <EmptyState
          title={t("common.empty")}
          description={t("documents.searchPlaceholder")}
          action={
            canCreate ? (
              <Button asChild>
                <Link href="/documents/upload">{t("documents.upload")}</Link>
              </Button>
            ) : null
          }
        />
      ) : (
        <>
          <DocumentTable
            documents={filteredDocuments}
            selectedIds={selectedIds}
            onSelectionChange={setSelectedIds}
            highlightId={highlightId}
            canDelete={canDelete}
            canReprocess={canAdminBulk}
            onDelete={(document) => {
              if (window.confirm(t("common.delete"))) {
                deleteMutation.mutate([document.id]);
              }
            }}
            onReprocess={(document) => reprocessMutation.mutate([document.id])}
            onDownload={(document) => void handleDownload(document)}
          />
          <Pagination
            page={page}
            limit={limit}
            total={total}
            onChange={(nextPage, nextLimit) => {
              setPage(nextPage);
              setLimit(nextLimit);
            }}
          />
        </>
      )}
    </div>
  );
}

export default function DocumentsPage() {
  return (
    <PermissionGuard permission="document:read">
      <Suspense fallback={<LoadingBlock variant="table" rows={8} />}>
        <DocumentsPageContent />
      </Suspense>
    </PermissionGuard>
  );
}
