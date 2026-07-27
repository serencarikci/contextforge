"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
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
import { listOrganizations } from "@/lib/api/endpoints";
import { BOOTSTRAP_ORG_ID, BOOTSTRAP_PRESETS } from "@/lib/constants";
import type { Organization } from "@/lib/types/api";
import { useSessionStore } from "@/stores/session-store";

const loginSchema = z.object({
    identity: z.string().trim().min(1, "Email or user ID is required"),
    organizationId: z.string().uuid("Select an organization"),
});

type LoginValues = z.infer<typeof loginSchema>;

const BOOTSTRAP_ORGANIZATION: Organization = {
    id: BOOTSTRAP_ORG_ID,
    name: "ContextForge Dev",
    slug: "contextforge-dev",
    status: "active",
    created_at: new Date(0).toISOString(),
    updated_at: new Date(0).toISOString(),
};

function resolveIdentity(identity: string): {
    userId: string;
    email: string | null;
    displayName: string | null;
    defaultOrganizationId: string | null;
} {
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

function LoginForm() {
    const { t } = useTranslation();
    const router = useRouter();
    const searchParams = useSearchParams();
    const login = useSessionStore((s) => s.login);
    const [organizations, setOrganizations] = useState<Organization[]>([]);
    const [resolvedUser, setResolvedUser] = useState<ReturnType<typeof resolveIdentity> | null>(
        null,
    );
    const [loadingOrgs, setLoadingOrgs] = useState(false);
    const [formError, setFormError] = useState<string | null>(null);

    const form = useForm<LoginValues>({
        resolver: zodResolver(loginSchema),
        defaultValues: {
            identity: "",
            organizationId: "",
        },
        mode: "onSubmit",
    });

    async function loadOrganizationsForIdentity(identity: string) {
        setFormError(null);
        setOrganizations([]);
        form.setValue("organizationId", "");

        const resolved = resolveIdentity(identity);
        setResolvedUser(resolved);

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

        if (resolved.defaultOrganizationId) {
            setOrganizations([BOOTSTRAP_ORGANIZATION]);
            form.setValue("organizationId", resolved.defaultOrganizationId, {
                shouldValidate: true,
            });
            setLoadingOrgs(false);
            return;
        }

        setLoadingOrgs(true);
        try {
            const response = await listOrganizations({ limit: 100, offset: 0 });
            setOrganizations(response.items);

            const preferred = response.items[0]?.id;
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
            setResolvedUser(null);
        } finally {
            setLoadingOrgs(false);
        }
    }

    async function onIdentityBlur() {
        const identity = form.getValues("identity").trim();
        if (!identity) {
            return;
        }
        if (resolvedUser && resolveIdentity(identity).userId === resolvedUser.userId) {
            return;
        }
        await loadOrganizationsForIdentity(identity);
    }

    async function applyPreset(userId: string) {
        const preset = BOOTSTRAP_PRESETS.find((item) => item.userId === userId);
        if (!preset) {
            return;
        }

        setFormError(null);
        setOrganizations([BOOTSTRAP_ORGANIZATION]);
        setResolvedUser({
            userId: preset.userId,
            email: preset.email,
            displayName: preset.displayName,
            defaultOrganizationId: preset.organizationId,
        });
        form.setValue("identity", preset.email, { shouldDirty: true, shouldValidate: true });
        form.setValue("organizationId", preset.organizationId, {
            shouldDirty: true,
            shouldValidate: true,
        });

        login({
            userId: preset.userId,
            organizationId: preset.organizationId,
            email: preset.email,
            displayName: preset.displayName,
        });

        const next = searchParams.get("next");
        router.replace(next && next.startsWith("/") ? next : "/chat");
    }

    async function onSubmit(values: LoginValues) {
        setFormError(null);
        const resolved = resolveIdentity(values.identity);

        let organizationId = values.organizationId;
        if (resolved.defaultOrganizationId) {
            organizationId = resolved.defaultOrganizationId;
        } else if (!organizationId) {
            setLoadingOrgs(true);
            try {
                const response = await listOrganizations({ limit: 100, offset: 0 });
                setOrganizations(response.items);
                organizationId = response.items[0]?.id ?? "";
                if (!organizationId) {
                    setFormError("No organizations found for this identity.");
                    return;
                }
                form.setValue("organizationId", organizationId, { shouldValidate: true });
            } catch (error) {
                const message = error instanceof ApiClientError ? error.message : t("common.error");
                setFormError(message);
                return;
            } finally {
                setLoadingOrgs(false);
            }
        }

        const org =
            organizations.find((item) => item.id === organizationId) ??
            (organizationId === BOOTSTRAP_ORG_ID ? BOOTSTRAP_ORGANIZATION : null);

        login({
            userId: resolved.userId,
            organizationId,
            email: resolved.email,
            displayName: resolved.displayName ?? org?.name ?? null,
        });

        const next = searchParams.get("next");
        router.replace(next && next.startsWith("/") ? next : "/chat");
    }

    return (
        <Card className="border-border/80 shadow-md">
            <CardHeader className="space-y-3 text-center">
                <div className="mx-auto flex size-12 items-center justify-center rounded-md bg-primary text-lg font-semibold text-primary-foreground">
                    CF
                </div>
                <div className="space-y-1">
                    <CardTitle className="text-2xl tracking-tight">
                        {t("auth.loginTitle")}
                    </CardTitle>
                    <CardDescription>{t("auth.loginSubtitle")}</CardDescription>
                </div>
            </CardHeader>
            <CardContent className="space-y-5">
                <div className="grid gap-2 sm:grid-cols-2">
                    {BOOTSTRAP_PRESETS.map((preset) => (
                        <Button
                            key={preset.userId}
                            type="button"
                            variant="outline"
                            className="h-auto flex-col items-start gap-0.5 px-3 py-2 text-left"
                            onClick={() => void applyPreset(preset.userId)}
                            disabled={loadingOrgs || form.formState.isSubmitting}
                        >
                            <span className="text-xs text-muted-foreground">
                                {t("auth.usePreset")}
                            </span>
                            <span className="text-sm font-medium">
                                {preset.role === "organization_admin"
                                    ? t("auth.presetAdmin")
                                    : t("auth.presetDeveloper")}
                            </span>
                        </Button>
                    ))}
                </div>

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
                                            onBlur={() => {
                                                field.onBlur();
                                                void onIdentityBlur();
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
                    href="/forgot-password"
                    className="text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
                >
                    {t("auth.forgotPassword")}
                </Link>
            </CardFooter>
        </Card>
    );
}

export default function LoginPage() {
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
            <LoginForm />
        </Suspense>
    );
}
