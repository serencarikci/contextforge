"use client";

import { Search } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { DocumentStatus } from "@/lib/types/api";
import { cn } from "@/lib/utils";

export interface DocumentFiltersValue {
  query: string;
  status: DocumentStatus | "all";
  knowledgeSpaceId: string | "all";
}

export interface DocumentFiltersProps {
  value: DocumentFiltersValue;
  onChange: (value: DocumentFiltersValue) => void;
  knowledgeSpaces?: Array<{ id: string; name: string }>;
  className?: string;
}

const STATUS_OPTIONS: Array<DocumentStatus | "all"> = [
  "all",
  "uploaded",
  "processing",
  "ready",
  "failed",
  "deleted",
];

export function DocumentFilters({
  value,
  onChange,
  knowledgeSpaces = [],
  className,
}: DocumentFiltersProps) {
  const { t } = useTranslation();

  return (
    <div
      className={cn(
        "grid gap-3 rounded-md border border-border bg-card p-3 sm:grid-cols-2 lg:grid-cols-3",
        className,
      )}
    >
      <div className="space-y-1.5 sm:col-span-2 lg:col-span-1">
        <Label htmlFor="document-search">{t("common.search")}</Label>
        <div className="relative">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            id="document-search"
            value={value.query}
            onChange={(event) => onChange({ ...value, query: event.target.value })}
            placeholder={t("documents.searchPlaceholder")}
            className="pl-8"
          />
        </div>
      </div>

      <div className="space-y-1.5">
        <Label>{t("common.status")}</Label>
        <Select
          value={value.status}
          onValueChange={(status) =>
            onChange({ ...value, status: status as DocumentFiltersValue["status"] })
          }
        >
          <SelectTrigger>
            <SelectValue placeholder={t("common.filter")} />
          </SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map((status) => (
              <SelectItem key={status} value={status}>
                {status === "all" ? t("common.filter") : status}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label>{t("nav.knowledgeSpaces")}</Label>
        <Select
          value={value.knowledgeSpaceId}
          onValueChange={(knowledgeSpaceId) =>
            onChange({ ...value, knowledgeSpaceId })
          }
        >
          <SelectTrigger>
            <SelectValue placeholder={t("nav.knowledgeSpaces")} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t("common.filter")}</SelectItem>
            {knowledgeSpaces.map((space) => (
              <SelectItem key={space.id} value={space.id}>
                {space.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
