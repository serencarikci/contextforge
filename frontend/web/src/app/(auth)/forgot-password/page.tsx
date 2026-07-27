"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import {
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { BOOTSTRAP_PRESETS } from "@/lib/constants";

const forgotSchema = z.object({
    identity: z.string().trim().min(1, "Email or user ID is required"),
});

type ForgotValues = z.infer<typeof forgotSchema>;

export default function ForgotPasswordPage() {
    const { t } = useTranslation();
    const router = useRouter();

    const form = useForm<ForgotValues>({
        resolver: zodResolver(forgotSchema),
        defaultValues: { identity: "" },
    });

    function onSubmit(values: ForgotValues) {
        const trimmed = values.identity.trim();
        const preset = BOOTSTRAP_PRESETS.find(
            (item) => item.email.toLowerCase() === trimmed.toLowerCase() || item.userId === trimmed,
        );
        const query = new URLSearchParams({
            identity: preset?.email ?? trimmed,
        });
        router.push(`/reset-password?${query.toString()}`);
    }

    return (
        <Card className="border-border/80 shadow-md">
            <CardHeader className="space-y-2 text-center">
                <CardTitle className="text-2xl tracking-tight">
                    {t("auth.forgotPassword")}
                </CardTitle>
                <CardDescription>{t("auth.forgotHint")}</CardDescription>
            </CardHeader>
            <CardContent>
                <Form {...form}>
                    <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)} noValidate>
                        <FormField
                            control={form.control}
                            name="identity"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>{t("auth.email")}</FormLabel>
                                    <FormControl>
                                        <Input
                                            {...field}
                                            autoComplete="username"
                                            placeholder="admin@contextforge.local"
                                        />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <Button type="submit" className="w-full">
                            {t("common.next")}
                        </Button>
                    </form>
                </Form>
            </CardContent>
            <CardFooter className="justify-center">
                <Link
                    href="/login"
                    className="text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
                >
                    {t("auth.signIn")}
                </Link>
            </CardFooter>
        </Card>
    );
}
