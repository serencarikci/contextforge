import type { Metadata } from "next";
import { Source_Sans_3 } from "next/font/google";
import type { ReactNode } from "react";

import { AppProviders } from "@/components/providers/app-providers";

import "./globals.css";

const sourceSans = Source_Sans_3({
    variable: "--font-sans",
    subsets: ["latin", "latin-ext"],
    weight: ["400", "500", "600", "700"],
    display: "swap",
});

export const metadata: Metadata = {
    title: "ContextForge",
    description: "Enterprise AI context platform",
};

export default function RootLayout({ children }: { children: ReactNode }) {
    return (
        <html lang="en" suppressHydrationWarning>
            <body className={`${sourceSans.variable} font-sans antialiased`}>
                <AppProviders>{children}</AppProviders>
            </body>
        </html>
    );
}
