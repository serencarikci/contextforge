"use client";

import { FileUp, Loader2, X } from "lucide-react";
import { useCallback, useMemo, useRef, useState, type DragEvent } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { documentsApi } from "@/lib/api/endpoints";
import type { Document } from "@/lib/types/api";
import { cn } from "@/lib/utils";

export interface UploadItem {
  id: string;
  file: File;
  title: string;
  progress: number;
  status: "queued" | "uploading" | "done" | "error";
  error?: string;
  document?: Document;
}

export interface UploadDropzoneProps {
  knowledgeSpaceId: string | null;
  onUploaded?: (documents: Document[]) => void;
  className?: string;
  accept?: string;
  multiple?: boolean;
}

function titleFromFilename(filename: string): string {
  const base = filename.replace(/\.[^.]+$/, "").trim();
  return base.length >= 2 ? base.slice(0, 200) : `Document ${Date.now()}`;
}

export function UploadDropzone({
  knowledgeSpaceId,
  onUploaded,
  className,
  accept = ".pdf,.docx,.txt,.md,.html,.htm",
  multiple = true,
}: UploadDropzoneProps) {
  const { t } = useTranslation();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [items, setItems] = useState<UploadItem[]>([]);
  const [uploading, setUploading] = useState(false);

  const updateItem = useCallback((id: string, patch: Partial<UploadItem>) => {
    setItems((prev) => prev.map((item) => (item.id === id ? { ...item, ...patch } : item)));
  }, []);

  const addFiles = useCallback((fileList: FileList | File[]) => {
    const next = Array.from(fileList).map((file) => ({
      id: crypto.randomUUID(),
      file,
      title: titleFromFilename(file.name),
      progress: 0,
      status: "queued" as const,
    }));
    setItems((prev) => [...prev, ...next]);
  }, []);

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    if (event.dataTransfer.files?.length) {
      addFiles(event.dataTransfer.files);
    }
  };

  const removeItem = (id: string) => {
    setItems((prev) => prev.filter((item) => item.id !== id));
  };

  const completedCount = useMemo(
    () => items.filter((item) => item.status === "done").length,
    [items],
  );

  const startUpload = async () => {
    if (!knowledgeSpaceId) {
      toast.error("Select a knowledge space before uploading.");
      return;
    }
    const pending = items.filter((item) => item.status === "queued" || item.status === "error");
    if (pending.length === 0) {
      return;
    }

    setUploading(true);
    const uploaded: Document[] = [];

    for (const item of pending) {
      updateItem(item.id, { status: "uploading", progress: 0, error: undefined });
      const formData = new FormData();
      formData.append("knowledge_space_id", knowledgeSpaceId);
      formData.append("title", item.title);
      formData.append("file", item.file);

      try {
        const document = await documentsApi.upload(formData, {
          onUploadProgress: (percent) => updateItem(item.id, { progress: percent }),
        });
        updateItem(item.id, {
          status: "done",
          progress: 100,
          document,
        });
        uploaded.push(document);
      } catch (error) {
        updateItem(item.id, {
          status: "error",
          error: error instanceof Error ? error.message : t("common.error"),
        });
      }
    }

    setUploading(false);
    if (uploaded.length > 0) {
      toast.success(`${uploaded.length} ${t("documents.upload").toLowerCase()}`);
      onUploaded?.(uploaded);
    }
  };

  return (
    <div className={cn("space-y-4", className)}>
      <div
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center gap-3 rounded-md border border-dashed border-border bg-muted/30 px-6 py-12 text-center transition-colors",
          dragging && "border-primary bg-primary/5",
        )}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            inputRef.current?.click();
          }
        }}
      >
        <div className="flex h-12 w-12 items-center justify-center rounded-md border border-border bg-background text-muted-foreground">
          <FileUp className="h-5 w-5" />
        </div>
        <div>
          <p className="text-sm font-medium text-foreground">{t("documents.drop")}</p>
          <p className="mt-1 text-xs text-muted-foreground">{accept}</p>
        </div>
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          multiple={multiple}
          accept={accept}
          onChange={(event) => {
            if (event.target.files?.length) {
              addFiles(event.target.files);
              event.target.value = "";
            }
          }}
        />
      </div>

      {items.length > 0 ? (
        <ul className="space-y-2">
          {items.map((item) => (
            <li
              key={item.id}
              className="rounded-md border border-border bg-card p-3"
            >
              <div className="mb-2 flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{item.title}</p>
                  <p className="truncate text-xs text-muted-foreground">
                    {item.file.name} · {(item.file.size / 1024).toFixed(1)} KB
                  </p>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 shrink-0"
                  disabled={item.status === "uploading"}
                  onClick={() => removeItem(item.id)}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
              <Progress value={item.progress} className="h-1.5" />
              <p className="mt-1.5 text-xs text-muted-foreground">
                {item.status === "uploading"
                  ? `${t("documents.processing")} ${item.progress}%`
                  : item.status === "done"
                    ? t("common.success")
                    : item.status === "error"
                      ? item.error || t("documents.failed")
                      : "Queued"}
              </p>
            </li>
          ))}
        </ul>
      ) : null}

      <div className="flex flex-wrap items-center gap-2">
        <Button
          type="button"
          onClick={() => void startUpload()}
          disabled={
            uploading ||
            !knowledgeSpaceId ||
            items.every((item) => item.status === "done")
          }
        >
          {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileUp className="h-4 w-4" />}
          {t("documents.upload")}
        </Button>
        {completedCount > 0 ? (
          <p className="text-sm text-muted-foreground">
            {completedCount}/{items.length} done
          </p>
        ) : null}
      </div>
    </div>
  );
}
