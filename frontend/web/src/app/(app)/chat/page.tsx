"use client";

import { MessageSquare } from "lucide-react";
import { useTranslation } from "react-i18next";

import { ConversationList } from "@/components/chat/conversation-list";
import { PermissionGuard } from "@/components/providers/permission-guard";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/ui/empty-state";

export default function ChatPage() {
  const { t } = useTranslation();

  return (
    <PermissionGuard permission="chat:use">
      <div className="space-y-6">
        <PageHeader
          title={t("chat.title")}
          description={t("chat.empty")}
          showSeparator
        />
        <div className="grid min-h-[32rem] overflow-hidden rounded-md border border-border bg-card lg:grid-cols-[20rem_1fr]">
          <ConversationList className="border-b border-border lg:border-b-0 lg:border-r" />
          <div className="hidden items-center justify-center p-8 lg:flex">
            <EmptyState
              icon={<MessageSquare className="h-5 w-5" />}
              title={t("chat.empty")}
              description={t("chat.placeholder")}
            />
          </div>
        </div>
      </div>
    </PermissionGuard>
  );
}
