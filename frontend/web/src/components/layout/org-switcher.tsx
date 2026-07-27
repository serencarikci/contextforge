"use client";

import { useQuery } from "@tanstack/react-query";
import { Building2, Check, ChevronsUpDown } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { listOrganizations } from "@/lib/api/endpoints";
import { cn } from "@/lib/utils";
import { useSessionStore } from "@/stores/session-store";

export function OrgSwitcher() {
  const { t } = useTranslation();
  const router = useRouter();
  const organizationId = useSessionStore((s) => s.organizationId);
  const switchOrg = useSessionStore((s) => s.switchOrg);
  const userId = useSessionStore((s) => s.userId);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["organizations", userId],
    queryFn: () => listOrganizations({ limit: 100, offset: 0 }),
    enabled: Boolean(userId),
    staleTime: 60_000,
  });

  const organizations = data?.items ?? [];
  const current =
    organizations.find((org) => org.id === organizationId) ?? null;

  function handleSelect(nextOrganizationId: string) {
    if (nextOrganizationId === organizationId) {
      return;
    }
    switchOrg(nextOrganizationId);
    router.refresh();
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="max-w-[14rem] gap-2"
          aria-label={t("auth.organization")}
        >
          <Building2 className="size-4 shrink-0" aria-hidden />
          <span className="hidden truncate sm:inline">
            {isLoading
              ? t("common.loading")
              : current?.name ?? t("auth.organization")}
          </span>
          <ChevronsUpDown className="hidden size-3.5 shrink-0 opacity-60 sm:block" aria-hidden />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        <DropdownMenuLabel>{t("auth.organization")}</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {isError ? (
          <DropdownMenuItem disabled>{t("common.error")}</DropdownMenuItem>
        ) : null}
        {!isLoading && organizations.length === 0 ? (
          <DropdownMenuItem disabled>{t("common.empty")}</DropdownMenuItem>
        ) : null}
        {organizations.map((org) => {
          const selected = org.id === organizationId;
          return (
            <DropdownMenuItem
              key={org.id}
              onSelect={() => handleSelect(org.id)}
              className={cn(selected && "bg-muted")}
            >
              <span className="min-w-0 flex-1 truncate">{org.name}</span>
              {selected ? <Check className="size-4 shrink-0" aria-hidden /> : null}
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
