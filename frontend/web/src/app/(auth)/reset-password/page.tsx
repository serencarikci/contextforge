"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
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
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { ApiClientError } from "@/lib/api/client";
import { validateSession } from "@/lib/api/endpoints";
import { BOOTSTRAP_PRESETS } from "@/lib/constants";
import type { Organization } from "@/lib/types/api";
import { useSessionStore } from "@/stores/session-store";

const resetSchema = z.object({
    identity: z.string().trim().min(1, "User ID or email is required"),
    organizationId: z.string().uuid("Select an organization"),
});

type ResetValues = z.infer<typeof resetSchema>;

function resolveIdentity(identity: string) {
    const trimmed = identity.trim();
    const preset = BOOTSTRAP_PRESETS.find(
        (item) => item.email.toLowerCase() === trimmed.toLowerCase() || item.userId === trimmed,
    );
    if (preset) {
        return {
            userId: preset.userId,
            email: preset.email,
            displayName: preset.displayName,
            defaultOrganizationId: preset.organizationId,
        };
    }
    return {
        userId: trimmed,
        email: trimmed.includes("@") ? trimmed : null,
        displayName: null,
        defaultOrganizationId: null,
    };
}

function ResetPasswordForm() {
    const { t } = useTranslation();
    const router = useRouter();
    const searchParams = useSearchParams();
    const login = useSessionStore((s) => s.login);
    const [organizations, setOrganizations] = useState<Organization[]>([]);
    const [loadingOrgs, setLoadingOrgs] = useState(false);
    const [formError, setFormError] = useState<string | null>(null);

    const form = useForm<ResetValues>({
        resolver: zodResolver(resetSchema),
        defaultValues: {
            identity: searchParams.get("identity") ?? "",
            organizationId: "",
        },
    });

    async function loadOrganizations(identity: string) {
        const resolved = resolveIdentity(identity);
        setFormError(null);
        setOrganizations([]);
        form.setValue("organizationId", "");

        useSessionStore.setState({
            userId: resolved.userId,
            organizationId: null,
            projectId: null,
            knowledgeSpaceId: null,
            email: resolved.email,
            displayName: resolved.displayName,
            expiresAt: null,
            permissions: [],
        });

        setLoadingOrgs(true);
        try {
            const response = await validateSession({ limit: 100, offset: 0 });
            setOrganizations(response.items);
            const preferred =
                response.items.find((org) => org.id === resolved.defaultOrganizationId)?.id ??
                response.items[0]?.id;
            if (preferred) {
                form.setValue("organizationId", preferred, { shouldValidate: true });
            }
            if (response.items.length === 0) {
                setFormError("No organizations found for this identity.");
            }
        } catch (error) {
            const message = error instanceof ApiClientError ? error.message : t("common.error");
            setFormError(message);
            useSessionStore.setState({ userId: null });
        } finally {
            setLoadingOrgs(false);
        }
    }

    useEffect(() => {
        const identity = searchParams.get("identity");
        if (identity) {
            void loadOrganizations(identity);
        }
    }, []);

    async function onSubmit(values: ResetValues) {
        setFormError(null);
        const resolved = resolveIdentity(values.identity);

        if (organizations.length === 0) {
            await loadOrganizations(values.identity);
            if (!form.getValues("organizationId")) {
                return;
            }
            values.organizationId = form.getValues("organizationId");
        }

        login({
            userId: resolved.userId,
            organizationId: values.organizationId,
            email: resolved.email,
            displayName: resolved.displayName,
        });
        router.replace("/chat");
    }

    return (
        <Card className="border-border/80 shadow-md">
            <CardHeader className="space-y-2 text-center">
                <CardTitle className="text-2xl tracking-tight">{t("auth.resetPassword")}</CardTitle>
                <CardDescription>{t("auth.resetHint")}</CardDescription>
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
                                            onBlur={() => {
                                                field.onBlur();
                                                if (field.value.trim()) {
                                                    void loadOrganizations(field.value);
                                                }
                                            }}
                                            disabled={loadingOrgs || form.formState.isSubmitting}
                                        />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />

                        <FormField
                            control={form.control}
                            name="organizationId"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>{t("auth.organization")}</FormLabel>
                                    <Select
                                        value={field.value || undefined}
                                        onValueChange={field.onChange}
                                        disabled={
                                            loadingOrgs ||
                                            form.formState.isSubmitting ||
                                            organizations.length === 0
                                        }
                                    >
                                        <FormControl>
                                            <SelectTrigger aria-label={t("auth.organization")}>
                                                <SelectValue
                                                    placeholder={
                                                        loadingOrgs
                                                            ? t("common.loading")
                                                            : t("auth.organization")
                                                    }
                                                />
                                            </SelectTrigger>
                                        </FormControl>
                                        <SelectContent>
                                            {organizations.map((org) => (
                                                <SelectItem key={org.id} value={org.id}>
                                                    {org.name}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />

                        {formError ? (
                            <p className="text-sm text-destructive" role="alert">
                                {formError}
                            </p>
                        ) : null}

                        <Button
                            type="submit"
                            className="w-full"
                            disabled={loadingOrgs || form.formState.isSubmitting}
                        >
                            {form.formState.isSubmitting ? t("common.loading") : t("auth.signIn")}
                        </Button>
                    </form>
                </Form>
            </CardContent>
            <CardFooter className="justify-center">
                <Link
                    href="/login"
                    className="text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
                >
                    {t("common.back")}
                </Link>
            </CardFooter>
        </Card>
    );
}

export default function ResetPasswordPage() {
    return (
        <Suspense
            fallback={
                <Card>
                    <CardHeader>
                        <CardTitle>ContextForge</CardTitle>
                        <CardDescription>Loading…</CardDescription>
                    </CardHeader>
                </Card>
            }
        >
            <ResetPasswordForm />
        </Suspense>
    );
}
