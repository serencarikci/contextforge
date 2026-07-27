"use client";

import { Breadcrumb } from "@/components/layout/breadcrumb";
import { LanguageSwitcher } from "@/components/layout/language-switcher";
import { NotificationArea } from "@/components/layout/notification-area";
import { OrgSwitcher } from "@/components/layout/org-switcher";
import { ThemeSwitcher } from "@/components/layout/theme-switcher";
import { UserMenu } from "@/components/layout/user-menu";

export function TopNav() {
  return (
    <header className="sticky top-0 z-20 border-b border-border bg-background/90 backdrop-blur supports-[backdrop-filter]:bg-background/75">
      <div className="flex h-14 items-center gap-3 px-4 sm:px-6 lg:px-8">
        <div className="min-w-0 flex-1 pl-10 md:pl-0">
          <Breadcrumb />
        </div>
        <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
          <OrgSwitcher />
          <ThemeSwitcher />
          <LanguageSwitcher />
          <NotificationArea />
          <UserMenu />
        </div>
      </div>
    </header>
  );
}
