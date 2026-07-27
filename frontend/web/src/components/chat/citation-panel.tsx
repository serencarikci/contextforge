"use client";

import { BookOpen, ExternalLink, X } from "lucide-react";
import Link from "next/link";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import type { Citation } from "@/lib/types/api";
import { cn } from "@/lib/utils";

export interface CitationPanelProps {
  citations: Citation[];
  open?: boolean;
  onClose?: () => void;
  className?: string;
  selectedId?: string | null;
  onSelect?: (citation: Citation) => void;
}

export function CitationPanel({
  citations,
  open = true,
  onClose,
  className,
  selectedId,
  onSelect,
}: CitationPanelProps) {
  const { t } = useTranslation();

  if (!open) {
    return null;
  }

  return (
    <aside
      className={cn(
        "flex h-full w-full flex-col border-l border-border bg-card md:w-80",
        className,
      )}
    >
      <div className="flex items-center justify-between gap-2 px-4 py-3">
        <div className="flex items-center gap-2">
          <BookOpen className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-sm font-semibold">{t("chat.citations")}</h2>
          <span className="rounded-md bg-muted px-1.5 py-0.5 text-xs tabular-nums text-muted-foreground">
            {citations.length}
          </span>
        </div>
        {onClose ? (
          <Button type="button" variant="ghost" size="icon" className="h-8 w-8" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        ) : null}
      </div>
      <Separator />
      <ScrollArea className="flex-1">
        {citations.length === 0 ? (
          <p className="px-4 py-6 text-sm text-muted-foreground">{t("common.empty")}</p>
        ) : (
          <ul className="space-y-2 p-3">
            {citations.map((citation) => {
              const active = selectedId === citation.id || selectedId === citation.chunk_id;
              return (
                <li key={citation.id || `${citation.chunk_id}-${citation.rank}`}>
                  <button
                    type="button"
                    onClick={() => onSelect?.(citation)}
                    className={cn(
                      "w-full rounded-md border border-border bg-background p-3 text-left transition-colors hover:bg-muted/60",
                      active && "border-primary bg-muted/40",
                    )}
                  >
                    <div className="mb-1 flex items-start justify-between gap-2">
                      <p className="text-sm font-medium leading-snug text-foreground">
                        {citation.document_title || citation.document_id}
                      </p>
                      <span className="shrink-0 text-xs tabular-nums text-muted-foreground">
                        #{citation.rank}
                      </span>
                    </div>
                    {(citation.page != null || citation.chunk_index != null) && (
                      <p className="mb-2 text-xs text-muted-foreground">
                        {citation.page != null ? `p.${citation.page}` : null}
                        {citation.page != null && citation.chunk_index != null ? " · " : null}
                        {citation.chunk_index != null
                          ? `chunk ${citation.chunk_index}`
                          : null}
                      </p>
                    )}
                    <p className="line-clamp-4 text-xs leading-relaxed text-muted-foreground">
                      {citation.snippet}
                    </p>
                    <div className="mt-2">
                      <Link
                        href={`/documents?highlight=${citation.document_id}`}
                        className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                        onClick={(event) => event.stopPropagation()}
                      >
                        <ExternalLink className="h-3 w-3" />
                        {citation.document_title}
                      </Link>
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </ScrollArea>
    </aside>
  );
}
