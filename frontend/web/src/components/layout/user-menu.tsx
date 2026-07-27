"use client";

import { LogOut, UserRound } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useSessionStore } from "@/stores/session-store";

function initials(displayName: string | null, email: string | null, userId: string | null) {
  const source = displayName || email || userId || "?";
  const parts = source.trim().split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0]![0]}${parts[1]![0]}`.toUpperCase();
  }
  return source.slice(0, 2).toUpperCase();
}

export function UserMenu() {
  const { t } = useTranslation();
  const router = useRouter();
  const displayName = useSessionStore((s) => s.displayName);
  const email = useSessionStore((s) => s.email);
  const userId = useSessionStore((s) => s.userId);
  const logout = useSessionStore((s) => s.logout);

  function handleLogout() {
    logout({ reason: "manual" });
    router.replace("/login");
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="rounded-md"
          aria-label={displayName || email || t("auth.signOut")}
        >
          <Avatar className="size-8">
            <AvatarFallback>
              {initials(displayName, email, userId)}
            </AvatarFallback>
          </Avatar>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="font-normal">
          <div className="flex flex-col gap-0.5">
            <span className="truncate text-sm font-medium text-foreground">
              {displayName || email || t("common.appName")}
            </span>
            {email ? (
              <span className="truncate text-xs text-muted-foreground">{email}</span>
            ) : null}
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => router.push("/settings")}>
          <UserRound className="size-4" aria-hidden />
          {t("nav.settings")}
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={handleLogout}>
          <LogOut className="size-4" aria-hidden />
          {t("auth.signOut")}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
