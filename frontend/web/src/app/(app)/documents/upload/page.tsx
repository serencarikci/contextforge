"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { UploadDropzone } from "@/components/documents/upload-dropzone";
import { PermissionGuard } from "@/components/providers/permission-guard";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { knowledgeSpacesApi } from "@/lib/api/endpoints";
import { useSessionStore } from "@/stores/session-store";

export default function DocumentsUploadPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const sessionKnowledgeSpaceId = useSessionStore((s) => s.knowledgeSpaceId);
  const setKnowledgeSpaceId = useSessionStore((s) => s.setKnowledgeSpaceId);
  const [knowledgeSpaceId, setLocalKnowledgeSpaceId] = useState<string>(
    sessionKnowledgeSpaceId ?? "",
  );

  const spacesQuery = useQuery({
    queryKey: ["knowledge-spaces-options"],
    queryFn: () => knowledgeSpacesApi.list({ limit: 100, offset: 0, status: "active" }),
  });

  return (
    <PermissionGuard permission="document:create">
      <div className="mx-auto max-w-3xl space-y-6">
        <PageHeader
          title={t("documents.upload")}
          description={t("documents.drop")}
          breadcrumbs={
            <div className="flex items-center gap-2 text-muted-foreground">
              <Button asChild variant="link" className="h-auto p-0">
                <Link href="/documents">{t("nav.documents")}</Link>
              </Button>
              <span>/</span>
              <span className="text-foreground">{t("documents.upload")}</span>
            </div>
          }
          showSeparator
        />

        <div className="space-y-2 rounded-md border border-border bg-card p-4">
          <Label>{t("nav.knowledgeSpaces")}</Label>
          <Select
            value={knowledgeSpaceId || undefined}
            onValueChange={(value) => {
              setLocalKnowledgeSpaceId(value);
              setKnowledgeSpaceId(value);
            }}
          >
            <SelectTrigger>
              <SelectValue placeholder={t("nav.knowledgeSpaces")} />
            </SelectTrigger>
            <SelectContent>
              {(spacesQuery.data?.items ?? []).map((space) => (
                <SelectItem key={space.id} value={space.id}>
                  {space.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <UploadDropzone
          knowledgeSpaceId={knowledgeSpaceId || null}
          onUploaded={() => {
            router.push("/documents");
          }}
        />
      </div>
    </PermissionGuard>
  );
}
