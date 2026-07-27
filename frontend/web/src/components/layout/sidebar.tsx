"use client";

import {
    BarChart3,
    BookOpen,
    ChevronLeft,
    ChevronRight,
    FileText,
    LayoutDashboard,
    Menu,
    MessageSquare,
    Settings,
    Server,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { useUiStore } from "@/stores/ui-store";

const NAV_ITEMS = [
    { href: "/chat", labelKey: "nav.chat", icon: MessageSquare },
    { href: "/documents", labelKey: "nav.documents", icon: FileText },
    { href: "/knowledge-spaces", labelKey: "nav.knowledgeSpaces", icon: BookOpen },
    { href: "/analytics", labelKey: "nav.analytics", icon: BarChart3 },
    { href: "/admin", labelKey: "nav.admin", icon: LayoutDashboard },
    { href: "/system", labelKey: "nav.system", icon: Server },
    { href: "/settings", labelKey: "nav.settings", icon: Settings },
] as const;

function NavLinks({ collapsed, onNavigate }: { collapsed?: boolean; onNavigate?: () => void }) {
    const pathname = usePathname();
    const { t } = useTranslation();

    return (
        <nav aria-label="Primary" className="flex flex-col gap-1 px-2">
            {NAV_ITEMS.map(({ href, labelKey, icon: Icon }) => {
                const active = pathname === href || pathname.startsWith(`${href}/`);
                const label = t(labelKey);
                const link = (
                    <Link
                        href={href}
                        onClick={onNavigate}
                        aria-current={active ? "page" : undefined}
                        className={cn(
                            "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                            collapsed && "justify-center px-2",
                            active
                                ? "bg-sidebar-muted text-sidebar-foreground"
                                : "text-sidebar-foreground/75 hover:bg-sidebar-muted/70 hover:text-sidebar-foreground",
                        )}
                    >
                        <Icon className="size-4 shrink-0" aria-hidden />
                        {!collapsed ? <span className="truncate">{label}</span> : null}
                        {collapsed ? <span className="sr-only">{label}</span> : null}
                    </Link>
                );

                if (!collapsed) {
                    return <div key={href}>{link}</div>;
                }

                return (
                    <Tooltip key={href}>
                        <TooltipTrigger asChild>{link}</TooltipTrigger>
                        <TooltipContent side="right">{label}</TooltipContent>
                    </Tooltip>
                );
            })}
        </nav>
    );
}

function Brand({ collapsed }: { collapsed?: boolean }) {
    const { t } = useTranslation();

    return (
        <Link
            href="/chat"
            className={cn(
                "flex items-center gap-2 px-3 py-1 text-sidebar-foreground",
                collapsed && "justify-center px-0",
            )}
        >
            <span
                className="flex size-8 items-center justify-center rounded-md bg-primary text-sm font-semibold text-primary-foreground"
                aria-hidden
            >
                CF
            </span>
            {!collapsed ? (
                <span className="truncate text-lg font-semibold tracking-tight">
                    {t("common.appName")}
                </span>
            ) : (
                <span className="sr-only">{t("common.appName")}</span>
            )}
        </Link>
    );
}

function DesktopSidebar() {
    const { t } = useTranslation();
    const collapsed = useUiStore((s) => s.sidebarCollapsed);
    const setSidebarCollapsed = useUiStore((s) => s.setSidebarCollapsed);

    return (
        <aside
            className={cn(
                "fixed inset-y-0 left-0 z-40 hidden border-r border-sidebar-muted bg-sidebar text-sidebar-foreground transition-[width] duration-200 md:flex md:flex-col",
                collapsed ? "w-16" : "w-64",
            )}
            aria-label="Application sidebar"
        >
            <div
                className={cn(
                    "flex h-14 items-center border-b border-sidebar-muted",
                    collapsed ? "justify-center px-2" : "justify-between px-3",
                )}
            >
                <Brand collapsed={collapsed} />
                {!collapsed ? (
                    <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="text-sidebar-foreground hover:bg-sidebar-muted hover:text-sidebar-foreground"
                        onClick={() => setSidebarCollapsed(true)}
                        aria-label="Collapse sidebar"
                    >
                        <ChevronLeft className="size-4" />
                    </Button>
                ) : null}
            </div>

            <ScrollArea className="flex-1 py-3">
                <NavLinks collapsed={collapsed} />
            </ScrollArea>

            <div className="border-t border-sidebar-muted p-2">
                {collapsed ? (
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Button
                                type="button"
                                variant="ghost"
                                size="icon"
                                className="w-full text-sidebar-foreground hover:bg-sidebar-muted hover:text-sidebar-foreground"
                                onClick={() => setSidebarCollapsed(false)}
                                aria-label="Expand sidebar"
                            >
                                <ChevronRight className="size-4" />
                            </Button>
                        </TooltipTrigger>
                        <TooltipContent side="right">Expand</TooltipContent>
                    </Tooltip>
                ) : (
                    <p className="px-3 py-2 text-xs text-sidebar-foreground/55">
                        {t("common.appName")}
                    </p>
                )}
            </div>
        </aside>
    );
}

function MobileSidebar() {
    const { t } = useTranslation();
    const open = useUiStore((s) => s.sidebarOpen);
    const setSidebarOpen = useUiStore((s) => s.setSidebarOpen);

    return (
        <>
            <Button
                type="button"
                variant="outline"
                size="icon"
                className="md:hidden"
                onClick={() => setSidebarOpen(true)}
                aria-label="Open navigation menu"
            >
                <Menu className="size-4" />
            </Button>

            <Sheet open={open} onOpenChange={setSidebarOpen}>
                <SheetContent
                    side="left"
                    className="w-[18rem] border-sidebar-muted bg-sidebar p-0 text-sidebar-foreground [&>button]:text-sidebar-foreground"
                >
                    <div className="flex h-14 items-center border-b border-sidebar-muted px-3">
                        <SheetTitle className="sr-only">{t("common.appName")}</SheetTitle>
                        <Brand />
                    </div>
                    <ScrollArea className="h-[calc(100vh-3.5rem)] py-3">
                        <NavLinks onNavigate={() => setSidebarOpen(false)} />
                    </ScrollArea>
                </SheetContent>
            </Sheet>
        </>
    );
}

export function Sidebar() {
    return (
        <>
            <DesktopSidebar />
            <div className="fixed left-3 top-3 z-30 md:hidden">
                <MobileSidebar />
            </div>
        </>
    );
}
