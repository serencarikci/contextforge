"use client";

import { formatDistanceToNow } from "date-fns";
import { Download, MoreHorizontal, RefreshCw, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";

import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { Document, DocumentStatus } from "@/lib/types/api";
import { cn } from "@/lib/utils";

export interface DocumentPipelineStatus {
  parse: string;
  embedding: string;
}

function derivePipelineStatus(status: DocumentStatus): DocumentPipelineStatus {
  switch (status) {
    case "ready":
      return { parse: "succeeded", embedding: "succeeded" };
    case "processing":
      return { parse: "running", embedding: "pending" };
    case "failed":
      return { parse: "failed", embedding: "failed" };
    case "uploaded":
      return { parse: "pending", embedding: "pending" };
    case "deleted":
      return { parse: "skipped", embedding: "skipped" };
    default:
      return { parse: "pending", embedding: "pending" };
  }
}

function formatBytes(size: number): string {
  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

export interface DocumentTableProps {
  documents: Document[];
  selectedIds: string[];
  onSelectionChange: (ids: string[]) => void;
  onDelete: (document: Document) => void;
  onReprocess: (document: Document) => void;
  onDownload: (document: Document) => void;
  pipelineById?: Record<string, DocumentPipelineStatus>;
  highlightId?: string | null;
  className?: string;
  canReprocess?: boolean;
  canDelete?: boolean;
}

export function DocumentTable({
  documents,
  selectedIds,
  onSelectionChange,
  onDelete,
  onReprocess,
  onDownload,
  pipelineById,
  highlightId,
  className,
  canReprocess = false,
  canDelete = true,
}: DocumentTableProps) {
  const { t } = useTranslation();
  const allSelected =
    documents.length > 0 && documents.every((document) => selectedIds.includes(document.id));

  const toggleAll = (checked: boolean) => {
    if (checked) {
      onSelectionChange(documents.map((document) => document.id));
      return;
    }
    onSelectionChange([]);
  };

  const toggleOne = (id: string, checked: boolean) => {
    if (checked) {
      onSelectionChange(Array.from(new Set([...selectedIds, id])));
      return;
    }
    onSelectionChange(selectedIds.filter((item) => item !== id));
  };

  return (
    <div className={cn("overflow-hidden rounded-md border border-border", className)}>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-10">
              <Checkbox
                checked={allSelected}
                onCheckedChange={(checked) => toggleAll(Boolean(checked))}
                aria-label="Select all"
              />
            </TableHead>
            <TableHead>Title</TableHead>
            <TableHead>{t("common.status")}</TableHead>
            <TableHead>Parse</TableHead>
            <TableHead>Embedding</TableHead>
            <TableHead>Size</TableHead>
            <TableHead>Updated</TableHead>
            <TableHead className="w-12">
              <span className="sr-only">{t("common.actions")}</span>
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {documents.map((document) => {
            const pipeline =
              pipelineById?.[document.id] ?? derivePipelineStatus(document.status);
            const selected = selectedIds.includes(document.id);
            return (
              <TableRow
                key={document.id}
                data-state={selected ? "selected" : undefined}
                className={cn(highlightId === document.id && "bg-accent/10")}
              >
                <TableCell>
                  <Checkbox
                    checked={selected}
                    onCheckedChange={(checked) => toggleOne(document.id, Boolean(checked))}
                    aria-label={`Select ${document.title}`}
                  />
                </TableCell>
                <TableCell>
                  <div className="min-w-0 space-y-0.5">
                    <p className="truncate font-medium text-foreground">{document.title}</p>
                    <p className="truncate text-xs text-muted-foreground">
                      {document.filename}
                    </p>
                  </div>
                </TableCell>
                <TableCell>
                  <StatusBadge status={document.status} />
                </TableCell>
                <TableCell>
                  <StatusBadge status={pipeline.parse} />
                </TableCell>
                <TableCell>
                  <StatusBadge status={pipeline.embedding} />
                </TableCell>
                <TableCell className="tabular-nums text-muted-foreground">
                  {formatBytes(document.size_bytes)}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {formatDistanceToNow(new Date(document.updated_at), { addSuffix: true })}
                </TableCell>
                <TableCell>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button type="button" variant="ghost" size="icon" className="h-8 w-8">
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => onDownload(document)}>
                        <Download className="h-4 w-4" />
                        {t("common.export")}
                      </DropdownMenuItem>
                      {canReprocess ? (
                        <DropdownMenuItem onClick={() => onReprocess(document)}>
                          <RefreshCw className="h-4 w-4" />
                          {t("documents.reprocess")}
                        </DropdownMenuItem>
                      ) : null}
                      {canDelete ? (
                        <>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            className="text-destructive focus:text-destructive"
                            onClick={() => onDelete(document)}
                          >
                            <Trash2 className="h-4 w-4" />
                            {t("common.delete")}
                          </DropdownMenuItem>
                        </>
                      ) : null}
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
