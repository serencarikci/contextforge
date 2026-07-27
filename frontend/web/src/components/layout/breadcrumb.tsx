"use client";

import { ChevronRight } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslation } from "react-i18next";

const SEGMENT_LABELS: Record<string, string> = {
  chat: "nav.chat",
  documents: "nav.documents",
  "knowledge-spaces": "nav.knowledgeSpaces",
  analytics: "nav.analytics",
  admin: "nav.admin",
  system: "nav.system",
  settings: "nav.settings",
  projects: "nav.projects",
  customers: "nav.customers",
};

function humanize(segment: string): string {
  return segment
    .split("-")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function Breadcrumb() {
  const pathname = usePathname();
  const { t } = useTranslation();
  const segments = pathname.split("/").filter(Boolean);

  if (segments.length === 0) {
    return null;
  }

  return (
    <nav aria-label="Breadcrumb" className="min-w-0">
      <ol className="flex min-w-0 items-center gap-1 text-sm text-muted-foreground">
        <li className="hidden shrink-0 sm:block">
          <Link href="/chat" className="hover:text-foreground">
            {t("common.appName")}
          </Link>
        </li>
        {segments.map((segment, index) => {
          const href = `/${segments.slice(0, index + 1).join("/")}`;
          const isLast = index === segments.length - 1;
          const labelKey = SEGMENT_LABELS[segment];
          const label = labelKey ? t(labelKey) : humanize(segment);

          return (
            <li key={href} className="flex min-w-0 items-center gap-1">
              <ChevronRight
                className="hidden size-3.5 shrink-0 sm:block"
                aria-hidden
              />
              {isLast ? (
                <span
                  className="truncate font-medium text-foreground"
                  aria-current="page"
                >
                  {label}
                </span>
              ) : (
                <Link href={href} className="truncate hover:text-foreground">
                  {label}
                </Link>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
