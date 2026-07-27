"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { useState, type ReactNode } from "react";
import { I18nextProvider } from "react-i18next";

import { Toaster } from "@/components/ui/sonner";
import i18n from "@/i18n";

export function AppProviders({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
        <I18nextProvider i18n={i18n}>
          {children}
          <Toaster richColors closeButton position="top-right" />
        </I18nextProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
