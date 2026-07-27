"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/utils";

const ADMIN_LINKS: Array<{ href: string; key: string; exact?: boolean }> = [
  { href: "/admin", key: "dashboard", exact: true },
  { href: "/admin/users", key: "users" },
  { href: "/admin/organizations", key: "organizations" },
  { href: "/admin/roles", key: "roles" },
  { href: "/admin/prompts", key: "prompts" },
  { href: "/admin/llm-providers", key: "llm" },
  { href: "/admin/feature-flags", key: "featureFlags" },
  { href: "/admin/settings", key: "settings" },
  { href: "/admin/audit", key: "audit" },
  { href: "/admin/retention", key: "retention" },
];

export function AdminNav({ className }: { className?: string }) {
  const pathname = usePathname();
  const { t } = useTranslation();

  return (
    <nav
      className={cn(
        "flex flex-wrap gap-2 rounded-md border border-border bg-muted/30 p-2",
        className,
      )}
    >
      {ADMIN_LINKS.map((link) => {
        const active = link.exact
          ? pathname === link.href
          : pathname.startsWith(link.href);
        return (
          <Link
            key={link.href}
            href={link.href}
            className={cn(
              "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
              active
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:bg-background/70 hover:text-foreground",
            )}
          >
            {t(`admin.${link.key}`)}
          </Link>
        );
      })}
    </nav>
  );
}
