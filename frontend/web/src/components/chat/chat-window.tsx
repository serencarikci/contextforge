"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpen, Download, Loader2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { CitationPanel } from "@/components/chat/citation-panel";
import { Composer } from "@/components/chat/composer";
import { MessageBubble } from "@/components/chat/message-bubble";
import { LoadingBlock } from "@/components/shared/loading-block";
import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { conversationsApi } from "@/lib/api/endpoints";
import type { Citation, Message, MessageStatus } from "@/lib/types/api";
import { cn } from "@/lib/utils";

export interface ChatWindowProps {
  conversationId: string;
  className?: string;
}

interface StreamState {
  assistantId: string | null;
  userId: string | null;
}

function asRecord(data: unknown): Record<string, unknown> {
  if (data && typeof data === "object" && !Array.isArray(data)) {
    return data as Record<string, unknown>;
  }
  return {};
}

function asString(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function citationFromEvent(data: unknown, fallbackId: string): Citation {
  const record = asRecord(data);
  return {
    id: asString(record.id) ?? fallbackId,
    document_id: asString(record.document_id) ?? "",
    document_title: asString(record.document_title) ?? "Source",
    chunk_id: asString(record.chunk_id) ?? fallbackId,
    knowledge_space_id: asString(record.knowledge_space_id) ?? "",
    page: typeof record.page === "number" ? record.page : null,
    chunk_index: typeof record.chunk_index === "number" ? record.chunk_index : null,
    snippet: asString(record.snippet) ?? "",
    rank: typeof record.rank === "number" ? record.rank : 0,
  };
}

function createLocalMessage(partial: Partial<Message> & Pick<Message, "id" | "role" | "content">): Message {
  return {
    conversation_id: partial.conversation_id ?? "",
    status: partial.status ?? "completed",
    language: partial.language ?? null,
    sequence_no: partial.sequence_no ?? 0,
    parent_message_id: partial.parent_message_id ?? null,
    model_name: partial.model_name ?? null,
    prompt_tokens: partial.prompt_tokens ?? 0,
    completion_tokens: partial.completion_tokens ?? 0,
    total_tokens: partial.total_tokens ?? 0,
    latency_ms: partial.latency_ms ?? 0,
    retrieval_ms: partial.retrieval_ms ?? 0,
    error_code: partial.error_code ?? null,
    error_message: partial.error_message ?? null,
    created_at: partial.created_at ?? new Date().toISOString(),
    updated_at: partial.updated_at ?? new Date().toISOString(),
    citations: partial.citations ?? [],
    ...partial,
  };
}

export function ChatWindow({ conversationId, className }: ChatWindowProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [citationsOpen, setCitationsOpen] = useState(false);
  const [activeCitations, setActiveCitations] = useState<Citation[]>([]);
  const [selectedCitationId, setSelectedCitationId] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const streamRef = useRef<StreamState>({ assistantId: null, userId: null });
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const lastUserContentRef = useRef<string>("");

  const conversationQuery = useQuery({
    queryKey: ["conversation", conversationId],
    queryFn: () => conversationsApi.get(conversationId),
  });

  const messagesQuery = useQuery({
    queryKey: ["conversation-messages", conversationId],
    queryFn: () => conversationsApi.listMessages(conversationId, { limit: 200, offset: 0 }),
  });

  useEffect(() => {
    if (!messagesQuery.data) {
      return;
    }
    if (streaming) {
      return;
    }
    const items = [...messagesQuery.data.items].sort(
      (a, b) => a.sequence_no - b.sequence_no,
    );
    setMessages(items);
  }, [messagesQuery.data, streaming]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, streaming]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, [conversationId]);

  const updateMessage = useCallback((id: string, updater: (message: Message) => Message) => {
    setMessages((prev) => prev.map((message) => (message.id === id ? updater(message) : message)));
  }, []);

  const stopStreaming = useCallback(async () => {
    const assistantId = streamRef.current.assistantId;
    abortRef.current?.abort();
    abortRef.current = null;
    setStreaming(false);

    if (assistantId) {
      try {
        await conversationsApi.cancelMessage(conversationId, assistantId);
        updateMessage(assistantId, (message) => ({
          ...message,
          status: "cancelled" as MessageStatus,
        }));
      } catch (error) {
        toast.error(error instanceof Error ? error.message : t("common.error"));
      }
    }
  }, [conversationId, t, updateMessage]);

  const runStream = useCallback(
    async (content: string) => {
      const trimmed = content.trim();
      if (!trimmed || streaming) {
        return;
      }

      lastUserContentRef.current = trimmed;
      setDraft("");
      setStreaming(true);
      setCitationsOpen(true);
      setActiveCitations([]);

      const optimisticUserId = `local-user-${crypto.randomUUID()}`;
      const optimisticAssistantId = `local-assistant-${crypto.randomUUID()}`;
      streamRef.current = {
        userId: optimisticUserId,
        assistantId: optimisticAssistantId,
      };

      setMessages((prev) => [
        ...prev,
        createLocalMessage({
          id: optimisticUserId,
          conversation_id: conversationId,
          role: "user",
          content: trimmed,
          status: "completed",
          sequence_no: (prev.at(-1)?.sequence_no ?? 0) + 1,
        }),
        createLocalMessage({
          id: optimisticAssistantId,
          conversation_id: conversationId,
          role: "assistant",
          content: "",
          status: "streaming",
          parent_message_id: optimisticUserId,
          sequence_no: (prev.at(-1)?.sequence_no ?? 0) + 2,
          citations: [],
        }),
      ]);

      const controller = new AbortController();
      abortRef.current = controller;
      const idempotencyKey = crypto.randomUUID();
      const streamedCitations: Citation[] = [];

      try {
        for await (const event of conversationsApi.streamMessage(
          conversationId,
          { content: trimmed, idempotency_key: idempotencyKey },
          controller.signal,
        )) {
          const data = asRecord(event.data);

          switch (event.event) {
            case "stream.started": {
              const userMessageId = asString(data.user_message_id);
              const messageId = asString(data.message_id);
              if (userMessageId) {
                setMessages((prev) =>
                  prev.map((message) =>
                    message.id === streamRef.current.userId
                      ? { ...message, id: userMessageId }
                      : message,
                  ),
                );
                streamRef.current.userId = userMessageId;
              }
              if (messageId) {
                setMessages((prev) =>
                  prev.map((message) =>
                    message.id === streamRef.current.assistantId
                      ? { ...message, id: messageId, status: "streaming" }
                      : message,
                  ),
                );
                streamRef.current.assistantId = messageId;
              }
              break;
            }
            case "citation": {
              const citation = citationFromEvent(
                event.data,
                `citation-${streamedCitations.length + 1}`,
              );
              streamedCitations.push(citation);
              setActiveCitations([...streamedCitations]);
              const assistantId = streamRef.current.assistantId;
              if (assistantId) {
                updateMessage(assistantId, (message) => ({
                  ...message,
                  citations: [...streamedCitations],
                }));
              }
              break;
            }
            case "token.delta":
            case "token": {
              const delta =
                asString(data.delta) ??
                asString(data.token) ??
                (typeof event.data === "string" ? event.data : "");
              const assistantId = streamRef.current.assistantId;
              if (assistantId && delta) {
                updateMessage(assistantId, (message) => ({
                  ...message,
                  content: `${message.content}${delta}`,
                  status: "streaming",
                }));
              }
              break;
            }
            case "generation.completed":
            case "assistant_message":
            case "done": {
              const assistantId =
                asString(data.message_id) ?? streamRef.current.assistantId;
              const replayContent = asString(data.content);
              if (assistantId) {
                updateMessage(assistantId, (message) => ({
                  ...message,
                  id: assistantId,
                  content: replayContent ?? message.content,
                  status: "completed",
                  citations:
                    streamedCitations.length > 0
                      ? streamedCitations
                      : message.citations,
                }));
              }
              break;
            }
            case "stream.cancelled": {
              const assistantId =
                asString(data.message_id) ?? streamRef.current.assistantId;
              if (assistantId) {
                updateMessage(assistantId, (message) => ({
                  ...message,
                  status: "cancelled",
                }));
              }
              break;
            }
            case "stream.error":
            case "error": {
              const assistantId = streamRef.current.assistantId;
              const errorMessage =
                asString(data.message) ?? t("common.error");
              if (assistantId) {
                updateMessage(assistantId, (message) => ({
                  ...message,
                  status: "failed",
                  error_message: errorMessage,
                }));
              }
              toast.error(errorMessage);
              break;
            }
            default:
              break;
          }
        }
      } catch (error) {
        if ((error as Error).name === "AbortError") {
          return;
        }
        const assistantId = streamRef.current.assistantId;
        const message = error instanceof Error ? error.message : t("common.error");
        if (assistantId) {
          updateMessage(assistantId, (item) => ({
            ...item,
            status: "failed",
            error_message: message,
          }));
        }
        toast.error(message);
      } finally {
        setStreaming(false);
        abortRef.current = null;
        void queryClient.invalidateQueries({
          queryKey: ["conversation-messages", conversationId],
        });
        void queryClient.invalidateQueries({ queryKey: ["conversations"] });
        void queryClient.invalidateQueries({
          queryKey: ["conversation", conversationId],
        });
      }
    },
    [conversationId, queryClient, streaming, t, updateMessage],
  );

  const handleRetry = useCallback(() => {
    const content =
      lastUserContentRef.current ||
      [...messages].reverse().find((message) => message.role === "user")?.content ||
      "";
    if (!content.trim()) {
      return;
    }
    void runStream(content);
  }, [messages, runStream]);

  const handleExport = useCallback(async () => {
    try {
      const blob = await conversationsApi.export(conversationId, "markdown");
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `conversation-${conversationId}.md`;
      anchor.click();
      URL.revokeObjectURL(url);
      toast.success(t("chat.export"));
    } catch (error) {
      toast.error(error instanceof Error ? error.message : t("common.error"));
    }
  }, [conversationId, t]);

  const title = conversationQuery.data?.title || t("chat.title");
  const citationCount = useMemo(
    () =>
      activeCitations.length ||
      messages.reduce((total, message) => total + (message.citations?.length ?? 0), 0),
    [activeCitations.length, messages],
  );

  if (conversationQuery.isLoading || messagesQuery.isLoading) {
    return <LoadingBlock rows={8} className={className} />;
  }

  if (conversationQuery.isError) {
    return (
      <EmptyState
        className={className}
        title={t("common.error")}
        description={(conversationQuery.error as Error).message}
        action={
          <Button type="button" variant="outline" onClick={() => void conversationQuery.refetch()}>
            {t("common.retry")}
          </Button>
        }
      />
    );
  }

  return (
    <div className={cn("flex h-[calc(100vh-8rem)] min-h-[32rem] overflow-hidden rounded-md border border-border bg-background", className)}>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
          <div className="min-w-0">
            <h2 className="truncate text-base font-semibold">{title}</h2>
            <p className="text-xs text-muted-foreground">
              {streaming ? t("chat.streaming") : conversationQuery.data?.status}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => {
                const latest =
                  activeCitations.length > 0
                    ? activeCitations
                    : [...messages]
                        .reverse()
                        .find((message) => message.citations?.length)?.citations ?? [];
                setActiveCitations(latest);
                setCitationsOpen(true);
              }}
            >
              <BookOpen className="h-4 w-4" />
              {t("chat.citations")}
              {citationCount > 0 ? ` (${citationCount})` : ""}
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={() => void handleExport()}>
              <Download className="h-4 w-4" />
              {t("chat.export")}
            </Button>
          </div>
        </header>

        <ScrollArea className="flex-1 px-4">
          <div className="space-y-4 py-4">
            {messages.length === 0 ? (
              <EmptyState title={t("chat.empty")} description={t("chat.placeholder")} />
            ) : (
              messages.map((message) => (
                <MessageBubble
                  key={message.id}
                  message={message}
                  streaming={
                    streaming &&
                    message.id === streamRef.current.assistantId &&
                    message.role === "assistant"
                  }
                  onRetry={handleRetry}
                  onCopy={() => toast.success(t("common.copy"))}
                  onOpenCitations={(citations) => {
                    setActiveCitations(citations);
                    setCitationsOpen(true);
                  }}
                />
              ))
            )}
            {streaming ? (
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                {t("chat.streaming")}
              </div>
            ) : null}
            <div ref={bottomRef} />
          </div>
        </ScrollArea>

        <div className="border-t border-border p-3">
          <Composer
            value={draft}
            onChange={setDraft}
            onSubmit={() => void runStream(draft)}
            onStop={() => void stopStreaming()}
            streaming={streaming}
          />
        </div>
      </div>

      {citationsOpen ? (
        <>
          <button
            type="button"
            className="fixed inset-0 z-40 bg-black/40 md:hidden"
            aria-label={t("common.cancel")}
            onClick={() => setCitationsOpen(false)}
          />
          <div className="fixed inset-y-0 right-0 z-50 w-full max-w-sm md:static md:z-auto md:max-w-none">
            <CitationPanel
              citations={activeCitations}
              open
              onClose={() => setCitationsOpen(false)}
              selectedId={selectedCitationId}
              onSelect={(citation) =>
                setSelectedCitationId(citation.id || citation.chunk_id)
              }
            />
          </div>
        </>
      ) : null}
    </div>
  );
}
