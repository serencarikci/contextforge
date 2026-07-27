"use client";

import Link from "next/link";
import { use } from "react";
import { useTranslation } from "react-i18next";

import { ChatWindow } from "@/components/chat/chat-window";
import { ConversationList } from "@/components/chat/conversation-list";
import { PermissionGuard } from "@/components/providers/permission-guard";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";

export default function ConversationPage({
  params,
}: {
  params: Promise<{ conversationId: string }>;
}) {
  const { conversationId } = use(params);
  const { t } = useTranslation();

  return (
    <PermissionGuard permission="chat:use">
      <div className="space-y-4">
        <PageHeader
          title={t("chat.title")}
          breadcrumbs={
            <div className="flex items-center gap-2 text-muted-foreground">
              <Button asChild variant="link" className="h-auto p-0">
                <Link href="/chat">{t("nav.chat")}</Link>
              </Button>
              <span>/</span>
              <span className="truncate text-foreground">{conversationId}</span>
            </div>
          }
        />
        <div className="grid min-h-[32rem] overflow-hidden rounded-md border border-border lg:grid-cols-[18rem_1fr]">
          <ConversationList
            activeId={conversationId}
            compact
            className="hidden border-r border-border lg:flex"
          />
          <ChatWindow conversationId={conversationId} className="border-0" />
        </div>
      </div>
    </PermissionGuard>
  );
}
