"use client";

import { Loader2, SendHorizonal, Square } from "lucide-react";
import { useEffect, useRef, type FormEvent, type KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

export interface ComposerProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onStop?: () => void;
  disabled?: boolean;
  streaming?: boolean;
  className?: string;
  placeholder?: string;
}

export function Composer({
  value,
  onChange,
  onSubmit,
  onStop,
  disabled = false,
  streaming = false,
  className,
  placeholder,
}: ComposerProps) {
  const { t } = useTranslation();
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) {
      return;
    }
    el.style.height = "0px";
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  }, [value]);

  const handleSubmit = (event?: FormEvent) => {
    event?.preventDefault();
    if (streaming || disabled || !value.trim()) {
      return;
    }
    onSubmit();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className={cn(
        "flex items-end gap-2 rounded-md border border-border bg-card p-2 shadow-sm",
        className,
      )}
    >
      <Textarea
        ref={textareaRef}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled || streaming}
        placeholder={placeholder ?? t("chat.placeholder")}
        rows={1}
        className="min-h-[40px] max-h-[180px] flex-1 resize-none border-0 bg-transparent px-2 py-2 shadow-none focus-visible:ring-0"
      />
      {streaming ? (
        <Button
          type="button"
          variant="destructive"
          size="icon"
          onClick={onStop}
          aria-label={t("chat.stop")}
        >
          <Square className="h-4 w-4 fill-current" />
        </Button>
      ) : (
        <Button
          type="submit"
          size="icon"
          disabled={disabled || !value.trim()}
          aria-label={t("chat.send")}
        >
          {disabled ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <SendHorizonal className="h-4 w-4" />
          )}
        </Button>
      )}
    </form>
  );
}
