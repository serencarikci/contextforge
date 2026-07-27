"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";

import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useSessionStore } from "@/stores/session-store";

export default function LogoutPage() {
    const { t } = useTranslation();
    const router = useRouter();
    const logout = useSessionStore((s) => s.logout);

    useEffect(() => {
        logout({ reason: "manual" });
        router.replace("/login");
    }, [logout, router]);

    return (
        <Card className="border-border/80 shadow-md">
            <CardHeader className="space-y-2 text-center">
                <CardTitle className="text-2xl tracking-tight">{t("auth.signOut")}</CardTitle>
                <CardDescription>{t("common.loading")}</CardDescription>
            </CardHeader>
        </Card>
    );
}
