"use client";

import { Check, Copy, RefreshCw } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import rehypeSanitize from "rehype-sanitize";
import remarkGfm from "remark-gfm";

import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import type { Citation, Message } from "@/lib/types/api";
import { cn } from "@/lib/utils";

import "highlight.js/styles/github-dark-dimmed.css";

export interface MessageBubbleProps {
  message: Message;
  streaming?: boolean;
  onRetry?: () => void;
  onCopy?: (content: string) => void;
  onOpenCitations?: (citations: Citation[]) => void;
  className?: string;
}

export function MessageBubble({
  message,
  streaming = false,
  onRetry,
  onCopy,
  onOpenCitations,
  className,
}: MessageBubbleProps) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);
  const isUser = message.role === "user";
  const isAssistant = message.role === "assistant";
  const showActions = isAssistant && !streaming && message.status !== "pending";

  const handleCopy = async () => {
    const text = message.content;
    try {
      await navigator.clipboard.writeText(text);
      onCopy?.(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div
      className={cn(
        "group flex w-full",
        isUser ? "justify-end" : "justify-start",
        className,
      )}
      data-role={message.role}
      data-status={message.status}
    >
      <div
        className={cn(
          "max-w-[min(100%,42rem)] space-y-2 rounded-md border px-3 py-2.5 shadow-sm",
          isUser
            ? "border-primary/20 bg-primary text-primary-foreground"
            : "border-border bg-card text-card-foreground",
        )}
      >
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium uppercase tracking-wide opacity-80">
            {message.role}
          </span>
          {!isUser && message.status !== "completed" ? (
            <StatusBadge status={streaming ? "streaming" : message.status} showDot />
          ) : null}
        </div>

        {isUser ? (
          <p className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</p>
        ) : (
          <div
            className={cn(
              "prose prose-sm dark:prose-invert max-w-none text-sm leading-relaxed",
              "prose-pre:rounded-md prose-pre:bg-[#0d1117] prose-code:before:content-none prose-code:after:content-none",
            )}
          >
            {message.content ? (
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeSanitize, rehypeHighlight]}
              >
                {message.content}
              </ReactMarkdown>
            ) : streaming ? (
              <p className="text-muted-foreground">{t("chat.streaming")}</p>
            ) : (
              <p className="text-muted-foreground">{t("common.empty")}</p>
            )}
            {streaming ? (
              <span className="ml-0.5 inline-block h-4 w-1 animate-pulse bg-foreground/70 align-middle" />
            ) : null}
          </div>
        )}

        {message.error_message ? (
          <p className="text-xs text-destructive">{message.error_message}</p>
        ) : null}

        {showActions ? (
          <div className="flex flex-wrap items-center gap-1 pt-1 opacity-100 md:opacity-0 md:transition-opacity md:group-hover:opacity-100">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-xs"
              onClick={() => void handleCopy()}
            >
              {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
              {t("chat.copyMessage")}
            </Button>
            {onRetry ? (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-7 px-2 text-xs"
                onClick={onRetry}
              >
                <RefreshCw className="h-3.5 w-3.5" />
                {t("chat.retry")}
              </Button>
            ) : null}
            {message.citations?.length ? (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-7 px-2 text-xs"
                onClick={() => onOpenCitations?.(message.citations)}
              >
                {t("chat.citations")} ({message.citations.length})
              </Button>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
