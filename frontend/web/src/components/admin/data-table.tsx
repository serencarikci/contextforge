"use client";

import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { LoadingBlock } from "@/components/shared/loading-block";
import { EmptyState } from "@/components/ui/empty-state";
import { Pagination } from "@/components/ui/pagination";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

export interface DataTableColumn<T> {
  id: string;
  header: ReactNode;
  cell: (row: T) => ReactNode;
  className?: string;
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  loading = false,
  emptyTitle,
  emptyDescription,
  emptyAction,
  page,
  limit,
  total,
  onPageChange,
  className,
}: {
  columns: DataTableColumn<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  loading?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  emptyAction?: ReactNode;
  page?: number;
  limit?: number;
  total?: number;
  onPageChange?: (page: number, limit: number) => void;
  className?: string;
}) {
  const { t } = useTranslation();

  if (loading) {
    return <LoadingBlock variant="table" rows={6} className={className} />;
  }

  if (rows.length === 0) {
    return (
      <EmptyState
        title={emptyTitle ?? t("common.empty")}
        description={emptyDescription}
        action={emptyAction}
        className={className}
      />
    );
  }

  return (
    <div className={cn("space-y-4", className)}>
      <div className="rounded-md border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map((column) => (
                <TableHead key={column.id} className={column.className}>
                  {column.header}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={rowKey(row)}>
                {columns.map((column) => (
                  <TableCell key={column.id} className={column.className}>
                    {column.cell(row)}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      {onPageChange && page !== undefined && limit !== undefined && total !== undefined ? (
        <Pagination page={page} limit={limit} total={total} onChange={onPageChange} />
      ) : null}
    </div>
  );
}
