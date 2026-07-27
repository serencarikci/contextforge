"use client";

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

import { STORAGE_KEYS } from "@/lib/constants";

export interface AppNotification {
  id: string;
  title: string;
  description?: string;
  createdAt: number;
  read: boolean;
}

interface UiState {
  sidebarOpen: boolean;
  sidebarCollapsed: boolean;
  notifications: AppNotification[];
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  pushNotification: (notification: Omit<AppNotification, "id" | "createdAt" | "read">) => void;
  markNotificationRead: (id: string) => void;
  clearNotifications: () => void;
}

export const useUiStore = create<UiState>()(
  persist(
    (set) => ({
      sidebarOpen: false,
      sidebarCollapsed: false,
      notifications: [],
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
      pushNotification: (notification) =>
        set((state) => ({
          notifications: [
            {
              id: crypto.randomUUID(),
              createdAt: Date.now(),
              read: false,
              ...notification,
            },
            ...state.notifications,
          ].slice(0, 30),
        })),
      markNotificationRead: (id) =>
        set((state) => ({
          notifications: state.notifications.map((item) =>
            item.id === id ? { ...item, read: true } : item,
          ),
        })),
      clearNotifications: () => set({ notifications: [] }),
    }),
    {
      name: STORAGE_KEYS.ui,
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        notifications: state.notifications,
      }),
    },
  ),
);
