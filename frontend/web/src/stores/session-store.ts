"use client";

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

import {
  BOOTSTRAP_PRESETS,
  DEVELOPER_PERMISSIONS,
  PERMISSIONS,
  SESSION_COOKIE,
  SESSION_TTL_MS,
  STORAGE_KEYS,
  type Permission,
} from "@/lib/constants";

export interface SessionLoginInput {
  userId: string;
  organizationId: string;
  projectId?: string | null;
  knowledgeSpaceId?: string | null;
  email?: string | null;
  displayName?: string | null;
  permissions?: Permission[];
  ttlMs?: number;
}

export interface SessionState {
  userId: string | null;
  organizationId: string | null;
  projectId: string | null;
  knowledgeSpaceId: string | null;
  email: string | null;
  displayName: string | null;
  expiresAt: number | null;
  permissions: Permission[];
  login: (input: SessionLoginInput) => void;
  logout: (options?: { reason?: "manual" | "session-expired" }) => void;
  refreshSession: (ttlMs?: number) => void;
  switchOrg: (organizationId: string) => void;
  setProjectId: (projectId: string | null) => void;
  setKnowledgeSpaceId: (knowledgeSpaceId: string | null) => void;
  hasPermission: (permission: Permission | string) => boolean;
  isAuthenticated: () => boolean;
  isExpired: () => boolean;
}

function setSessionCookie(active: boolean): void {
  if (typeof document === "undefined") {
    return;
  }
  if (active) {
    const maxAge = Math.floor(SESSION_TTL_MS / 1000);
    document.cookie = `${SESSION_COOKIE}=1; Path=/; Max-Age=${maxAge}; SameSite=Lax`;
    return;
  }
  document.cookie = `${SESSION_COOKIE}=; Path=/; Max-Age=0; SameSite=Lax`;
}

function resolvePermissions(input: SessionLoginInput): Permission[] {
  if (input.permissions && input.permissions.length > 0) {
    return [...input.permissions];
  }

  const preset = BOOTSTRAP_PRESETS.find(
    (item) => item.userId === input.userId || item.email === input.email,
  );
  if (preset?.role === "organization_admin") {
    return [...PERMISSIONS];
  }
  if (preset?.role === "developer") {
    return [...DEVELOPER_PERMISSIONS];
  }
  return [];
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set, get) => ({
      userId: null,
      organizationId: null,
      projectId: null,
      knowledgeSpaceId: null,
      email: null,
      displayName: null,
      expiresAt: null,
      permissions: [],

      login: (input) => {
        const ttlMs = input.ttlMs ?? SESSION_TTL_MS;
        const expiresAt = Date.now() + ttlMs;
        const permissions = resolvePermissions(input);

        set({
          userId: input.userId,
          organizationId: input.organizationId,
          projectId: input.projectId ?? null,
          knowledgeSpaceId: input.knowledgeSpaceId ?? null,
          email: input.email ?? null,
          displayName: input.displayName ?? null,
          expiresAt,
          permissions,
        });
        setSessionCookie(true);
      },

      logout: () => {
        set({
          userId: null,
          organizationId: null,
          projectId: null,
          knowledgeSpaceId: null,
          email: null,
          displayName: null,
          expiresAt: null,
          permissions: [],
        });
        setSessionCookie(false);
      },

      refreshSession: (ttlMs = SESSION_TTL_MS) => {
        const state = get();
        if (!state.userId || !state.organizationId) {
          return;
        }
        set({ expiresAt: Date.now() + ttlMs });
        setSessionCookie(true);
      },

      switchOrg: (organizationId) => {
        const state = get();
        if (!state.userId) {
          return;
        }
        set({
          organizationId,
          projectId: null,
          knowledgeSpaceId: null,
          expiresAt: Date.now() + SESSION_TTL_MS,
        });
        setSessionCookie(true);
      },

      setProjectId: (projectId) => set({ projectId }),

      setKnowledgeSpaceId: (knowledgeSpaceId) => set({ knowledgeSpaceId }),

      hasPermission: (permission) => get().permissions.includes(permission as Permission),

      isAuthenticated: () => {
        const state = get();
        return Boolean(state.userId && state.organizationId && !state.isExpired());
      },

      isExpired: () => {
        const { expiresAt } = get();
        if (!expiresAt) {
          return true;
        }
        return Date.now() >= expiresAt;
      },
    }),
    {
      name: STORAGE_KEYS.session,
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        userId: state.userId,
        organizationId: state.organizationId,
        projectId: state.projectId,
        knowledgeSpaceId: state.knowledgeSpaceId,
        email: state.email,
        displayName: state.displayName,
        expiresAt: state.expiresAt,
        permissions: state.permissions,
      }),
      onRehydrateStorage: () => (state) => {
        if (!state) {
          return;
        }
        if (state.userId && state.organizationId && !state.isExpired()) {
          setSessionCookie(true);
          return;
        }
        if (state.isExpired()) {
          state.logout({ reason: "session-expired" });
        }
      },
    },
  ),
);
