"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { LoadingBlock } from "@/components/shared/loading-block";
import { useSessionStore } from "@/stores/session-store";

export function AuthGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const userId = useSessionStore((s) => s.userId);
  const organizationId = useSessionStore((s) => s.organizationId);
  const isExpired = useSessionStore((s) => s.isExpired);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const unsub = useSessionStore.persist.onFinishHydration(() => setHydrated(true));
    setHydrated(useSessionStore.persist.hasHydrated());
    return unsub;
  }, []);

  useEffect(() => {
    if (!hydrated) {
      return;
    }
    if (!userId || !organizationId) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
      return;
    }
    if (isExpired()) {
      router.replace("/session-expired");
    }
  }, [hydrated, userId, organizationId, isExpired, router, pathname]);

  if (!hydrated || !userId || !organizationId || isExpired()) {
    return <LoadingBlock rows={3} />;
  }

  return <>{children}</>;
}
