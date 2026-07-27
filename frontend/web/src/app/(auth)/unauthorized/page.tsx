"use client";

import Link from "next/link";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import {
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";

export default function UnauthorizedPage() {
    const { t } = useTranslation();

    return (
        <Card className="border-border/80 shadow-md">
            <CardHeader className="space-y-2 text-center">
                <CardTitle className="text-2xl tracking-tight">{t("auth.unauthorized")}</CardTitle>
                <CardDescription>{t("auth.unauthorizedHint")}</CardDescription>
            </CardHeader>
            <CardContent>
                <p className="text-center text-sm text-muted-foreground">{t("common.error")}</p>
            </CardContent>
            <CardFooter className="flex flex-col gap-2 sm:flex-row sm:justify-center">
                <Button asChild variant="outline">
                    <Link href="/chat">{t("nav.chat")}</Link>
                </Button>
                <Button asChild>
                    <Link href="/login">{t("auth.signIn")}</Link>
                </Button>
            </CardFooter>
        </Card>
    );
}
