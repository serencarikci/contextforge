"use client";

import { Bell } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useUiStore } from "@/stores/ui-store";

function formatTime(timestamp: number): string {
  try {
    return new Intl.DateTimeFormat(undefined, {
      hour: "2-digit",
      minute: "2-digit",
      month: "short",
      day: "numeric",
    }).format(new Date(timestamp));
  } catch {
    return new Date(timestamp).toLocaleString();
  }
}

export function NotificationArea() {
  const { t } = useTranslation();
  const notifications = useUiStore((s) => s.notifications);
  const markNotificationRead = useUiStore((s) => s.markNotificationRead);
  const clearNotifications = useUiStore((s) => s.clearNotifications);
  const unreadCount = notifications.filter((item) => !item.read).length;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="relative"
          aria-label={
            unreadCount > 0
              ? `Notifications, ${unreadCount} unread`
              : "Notifications"
          }
        >
          <Bell className="size-4" />
          {unreadCount > 0 ? (
            <Badge
              variant="accent"
              className="absolute -right-1 -top-1 h-4 min-w-4 justify-center px-1 text-[10px]"
            >
              {unreadCount > 9 ? "9+" : unreadCount}
            </Badge>
          ) : null}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80 p-0">
        <div className="flex items-center justify-between px-3 py-2">
          <DropdownMenuLabel className="p-0">Notifications</DropdownMenuLabel>
          {notifications.length > 0 ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-xs"
              onClick={() => clearNotifications()}
            >
              {t("common.delete")}
            </Button>
          ) : null}
        </div>
        <DropdownMenuSeparator className="m-0" />
        {notifications.length === 0 ? (
          <div className="px-3 py-8 text-center text-sm text-muted-foreground">
            {t("common.empty")}
          </div>
        ) : (
          <ScrollArea className="h-72">
            <ul className="py-1">
              {notifications.map((notification) => (
                <li key={notification.id}>
                  <DropdownMenuItem
                    className="items-start gap-2 rounded-none px-3 py-2"
                    onSelect={() => markNotificationRead(notification.id)}
                  >
                    <div className="min-w-0 flex-1 space-y-0.5">
                      <p className="truncate text-sm font-medium text-foreground">
                        {notification.title}
                      </p>
                      {notification.description ? (
                        <p className="line-clamp-2 text-xs text-muted-foreground">
                          {notification.description}
                        </p>
                      ) : null}
                      <p className="text-[11px] text-muted-foreground">
                        {formatTime(notification.createdAt)}
                      </p>
                    </div>
                    {!notification.read ? (
                      <span
                        className="mt-1 size-2 shrink-0 rounded-full bg-accent"
                        aria-label="Unread"
                      />
                    ) : null}
                  </DropdownMenuItem>
                </li>
              ))}
            </ul>
          </ScrollArea>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
