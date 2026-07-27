"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import {
  Archive,
  MessageSquarePlus,
  MoreHorizontal,
  Pin,
  PinOff,
  Search,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { LoadingBlock } from "@/components/shared/loading-block";
import { StatusBadge } from "@/components/shared/status-badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { conversationsApi } from "@/lib/api/endpoints";
import type { Conversation } from "@/lib/types/api";
import { cn } from "@/lib/utils";
import { useSessionStore } from "@/stores/session-store";

export interface ConversationListProps {
  activeId?: string | null;
  className?: string;
  compact?: boolean;
}

export function ConversationList({
  activeId,
  className,
  compact = false,
}: ConversationListProps) {
  const { t } = useTranslation();
  const router = useRouter();
  const queryClient = useQueryClient();
  const knowledgeSpaceId = useSessionStore((s) => s.knowledgeSpaceId);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"active" | "archived">("active");

  const listQuery = useQuery({
    queryKey: ["conversations", statusFilter, search],
    queryFn: () =>
      search.trim()
        ? conversationsApi.search(search.trim(), { limit: 50, offset: 0 })
        : conversationsApi.list({
            limit: 50,
            offset: 0,
            status: statusFilter,
          }),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      conversationsApi.create({
        title: null,
        knowledge_space_ids: knowledgeSpaceId ? [knowledgeSpaceId] : null,
        preferred_language: "auto",
      }),
    onSuccess: (conversation) => {
      void queryClient.invalidateQueries({ queryKey: ["conversations"] });
      router.push(`/chat/${conversation.id}`);
      toast.success(t("chat.new"));
    },
    onError: (error: Error) => {
      const message = error.message || t("common.error");
      if (/timeout/i.test(message) || /network/i.test(message)) {
        toast.error("API yanıt vermiyor. Docker Desktop’ı yeniden başlatıp `docker compose up -d` çalıştırın.");
        return;
      }
      toast.error(message);
    },
  });

  const archiveMutation = useMutation({
    mutationFn: (id: string) => conversationsApi.archive(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["conversations"] });
      toast.success(t("documents.archive"));
    },
    onError: (error: Error) => toast.error(error.message || t("common.error")),
  });

  const restoreMutation = useMutation({
    mutationFn: (id: string) => conversationsApi.restore(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["conversations"] });
      toast.success(t("common.success"));
    },
    onError: (error: Error) => toast.error(error.message || t("common.error")),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => conversationsApi.remove(id),
    onSuccess: (_data, id) => {
      void queryClient.invalidateQueries({ queryKey: ["conversations"] });
      if (activeId === id) {
        router.push("/chat");
      }
      toast.success(t("chat.delete"));
    },
    onError: (error: Error) => toast.error(error.message || t("common.error")),
  });

  const pinMutation = useMutation({
    mutationFn: ({ id, pinned }: { id: string; pinned: boolean }) =>
      conversationsApi.update(id, { pinned }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
    onError: (error: Error) => toast.error(error.message || t("common.error")),
  });

  const conversations = useMemo(() => {
    const items = listQuery.data?.items ?? [];
    return [...items].sort((a, b) => {
      if (a.pinned !== b.pinned) {
        return a.pinned ? -1 : 1;
      }
      return (
        new Date(b.last_activity_at).getTime() - new Date(a.last_activity_at).getTime()
      );
    });
  }, [listQuery.data?.items]);

  return (
    <div className={cn("flex h-full min-h-0 flex-col", className)}>
      <div className="space-y-3 border-b border-border p-3">
        <div className="flex items-center gap-2">
          <Button
            type="button"
            className="flex-1"
            onClick={() => createMutation.mutate()}
            disabled={createMutation.isPending}
          >
            <MessageSquarePlus className="h-4 w-4" />
            {createMutation.isPending ? t("common.loading") : t("chat.new")}
          </Button>
        </div>
        <div className="relative">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={t("common.search")}
            className="pl-8"
          />
        </div>
        <div className="flex gap-1">
          <Button
            type="button"
            size="sm"
            variant={statusFilter === "active" ? "secondary" : "ghost"}
            onClick={() => setStatusFilter("active")}
          >
            Active
          </Button>
          <Button
            type="button"
            size="sm"
            variant={statusFilter === "archived" ? "secondary" : "ghost"}
            onClick={() => setStatusFilter("archived")}
          >
            Archived
          </Button>
        </div>
      </div>

      <ScrollArea className="flex-1">
        {listQuery.isLoading ? (
          <div className="p-3">
            <LoadingBlock rows={6} showHeader={false} />
          </div>
        ) : listQuery.isError ? (
          <div className="p-3">
            <EmptyState
              title={t("common.error")}
              description={(listQuery.error as Error).message}
              action={
                <Button type="button" variant="outline" onClick={() => void listQuery.refetch()}>
                  {t("common.retry")}
                </Button>
              }
            />
          </div>
        ) : conversations.length === 0 ? (
          <div className="p-3">
            <EmptyState
              title={t("common.empty")}
              description={t("chat.empty")}
              action={
                <Button
                  type="button"
                  onClick={() => createMutation.mutate()}
                  disabled={createMutation.isPending}
                >
                  {createMutation.isPending ? t("common.loading") : t("chat.new")}
                </Button>
              }
            />
          </div>
        ) : (
          <ul className="space-y-1 p-2">
            {conversations.map((conversation) => (
              <ConversationListItem
                key={conversation.id}
                conversation={conversation}
                active={conversation.id === activeId}
                compact={compact}
                onArchive={() => archiveMutation.mutate(conversation.id)}
                onRestore={() => restoreMutation.mutate(conversation.id)}
                onDelete={() => {
                  if (window.confirm(t("chat.delete"))) {
                    deleteMutation.mutate(conversation.id);
                  }
                }}
                onTogglePin={() =>
                  pinMutation.mutate({
                    id: conversation.id,
                    pinned: !conversation.pinned,
                  })
                }
              />
            ))}
          </ul>
        )}
      </ScrollArea>
    </div>
  );
}

function ConversationListItem({
  conversation,
  active,
  compact,
  onArchive,
  onRestore,
  onDelete,
  onTogglePin,
}: {
  conversation: Conversation;
  active: boolean;
  compact: boolean;
  onArchive: () => void;
  onRestore: () => void;
  onDelete: () => void;
  onTogglePin: () => void;
}) {
  const { t } = useTranslation();

  return (
    <li>
      <div
        className={cn(
          "group flex items-start gap-1 rounded-md border border-transparent px-2 py-2 transition-colors hover:bg-muted/70",
          active && "border-border bg-muted",
        )}
      >
        <Link href={`/chat/${conversation.id}`} className="min-w-0 flex-1 space-y-1">
          <div className="flex items-center gap-1.5">
            {conversation.pinned ? (
              <Pin className="h-3.5 w-3.5 shrink-0 text-accent" />
            ) : null}
            <p className="truncate text-sm font-medium text-foreground">
              {conversation.title || t("chat.title")}
            </p>
          </div>
          {!compact ? (
            <p className="truncate text-xs text-muted-foreground">
              {conversation.summary_text ||
                formatDistanceToNow(new Date(conversation.last_activity_at), {
                  addSuffix: true,
                })}
            </p>
          ) : null}
          <div className="flex items-center gap-2">
            <StatusBadge status={conversation.status} className="h-5 text-[10px]" />
            <span className="text-[11px] text-muted-foreground">
              {formatDistanceToNow(new Date(conversation.last_activity_at), {
                addSuffix: true,
              })}
            </span>
          </div>
        </Link>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-8 w-8 shrink-0 opacity-100 md:opacity-0 md:group-hover:opacity-100"
            >
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={onTogglePin}>
              {conversation.pinned ? (
                <>
                  <PinOff className="h-4 w-4" />
                  Unpin
                </>
              ) : (
                <>
                  <Pin className="h-4 w-4" />
                  Pin
                </>
              )}
            </DropdownMenuItem>
            {conversation.status === "archived" ? (
              <DropdownMenuItem onClick={onRestore}>
                <Archive className="h-4 w-4" />
                Restore
              </DropdownMenuItem>
            ) : (
              <DropdownMenuItem onClick={onArchive}>
                <Archive className="h-4 w-4" />
                {t("documents.archive")}
              </DropdownMenuItem>
            )}
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="text-destructive focus:text-destructive"
              onClick={onDelete}
            >
              <Trash2 className="h-4 w-4" />
              {t("common.delete")}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </li>
  );
}
