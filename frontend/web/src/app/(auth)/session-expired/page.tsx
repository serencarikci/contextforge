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

export default function SessionExpiredPage() {
    const { t } = useTranslation();

    return (
        <Card className="border-border/80 shadow-md">
            <CardHeader className="space-y-2 text-center">
                <CardTitle className="text-2xl tracking-tight">
                    {t("auth.sessionExpired")}
                </CardTitle>
                <CardDescription>{t("auth.sessionExpiredHint")}</CardDescription>
            </CardHeader>
            <CardContent>
                <p className="text-center text-sm text-muted-foreground">
                    {t("auth.loginSubtitle")}
                </p>
            </CardContent>
            <CardFooter className="justify-center">
                <Button asChild className="w-full sm:w-auto">
                    <Link href="/login">{t("auth.signIn")}</Link>
                </Button>
            </CardFooter>
        </Card>
    );
}
