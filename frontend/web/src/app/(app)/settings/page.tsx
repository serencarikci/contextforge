"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTheme } from "next-themes";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { z } from "zod";

import { PageHeader } from "@/components/shared/page-header";
import { LoadingBlock } from "@/components/shared/loading-block";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
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
import { getOrganization, listOrganizations, usersApi } from "@/lib/api/endpoints";
import { STORAGE_KEYS } from "@/lib/constants";
import { queryKeys } from "@/lib/query-keys";
import { useSessionStore } from "@/stores/session-store";

const profileSchema = z.object({
  display_name: z.string().min(2).max(120),
  preferred_language: z.enum(["en", "tr", "auto"]),
});

type ProfileValues = z.infer<typeof profileSchema>;

export default function SettingsPage() {
  const { t, i18n } = useTranslation();
  const { theme, setTheme } = useTheme();
  const queryClient = useQueryClient();
  const userId = useSessionStore((s) => s.userId);
  const organizationId = useSessionStore((s) => s.organizationId);
  const email = useSessionStore((s) => s.email);
  const displayName = useSessionStore((s) => s.displayName);
  const login = useSessionStore((s) => s.login);
  const switchOrg = useSessionStore((s) => s.switchOrg);

  const userQuery = useQuery({
    queryKey: queryKeys.users.detail(userId ?? ""),
    queryFn: () => usersApi.get(userId!),
    enabled: Boolean(userId),
  });

  const orgQuery = useQuery({
    queryKey: queryKeys.organizations.detail(organizationId ?? ""),
    queryFn: () => getOrganization(organizationId!),
    enabled: Boolean(organizationId),
  });

  const orgsQuery = useQuery({
    queryKey: queryKeys.organizations.list({ limit: 50, offset: 0 }),
    queryFn: () => listOrganizations({ limit: 50, offset: 0 }),
  });

  const form = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    values: {
      display_name: userQuery.data?.display_name ?? displayName ?? "",
      preferred_language:
        (userQuery.data?.preferred_language as "en" | "tr" | "auto") ?? "en",
    },
  });

  const updateMutation = useMutation({
    mutationFn: (values: ProfileValues) =>
      usersApi.update(userId!, {
        display_name: values.display_name,
        preferred_language: values.preferred_language,
      }),
    onSuccess: async (user) => {
      await queryClient.invalidateQueries({
        queryKey: queryKeys.users.detail(userId!),
      });
      if (userId && organizationId) {
        login({
          userId,
          organizationId,
          email: user.email,
          displayName: user.display_name,
          permissions: useSessionStore.getState().permissions,
        });
      }
      if (user.preferred_language === "en" || user.preferred_language === "tr") {
        void i18n.changeLanguage(user.preferred_language);
        localStorage.setItem(STORAGE_KEYS.locale, user.preferred_language);
      }
      toast.success(t("common.success"));
    },
    onError: () => toast.error(t("common.error")),
  });

  const changeLanguage = (language: string) => {
    void i18n.changeLanguage(language);
    localStorage.setItem(STORAGE_KEYS.locale, language);
    toast.success(t("common.success"));
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("settings.title")}
        description={t("settings.description")}
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>{t("settings.profile")}</CardTitle>
            <CardDescription>{t("settings.profileHint")}</CardDescription>
          </CardHeader>
          <CardContent>
            {userQuery.isLoading ? (
              <LoadingBlock rows={3} showHeader={false} />
            ) : (
              <Form {...form}>
                <form
                  className="space-y-4"
                  onSubmit={form.handleSubmit((values) =>
                    updateMutation.mutate(values),
                  )}
                >
                  <div className="space-y-1 text-sm">
                    <div className="text-muted-foreground">{t("auth.email")}</div>
                    <div className="font-medium">
                      {userQuery.data?.email ?? email ?? "—"}
                    </div>
                  </div>
                  <FormField
                    control={form.control}
                    name="display_name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t("admin.displayName")}</FormLabel>
                        <FormControl>
                          <Input {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="preferred_language"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t("settings.preferredLanguage")}</FormLabel>
                        <Select
                          value={field.value}
                          onValueChange={field.onChange}
                        >
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="en">English</SelectItem>
                            <SelectItem value="tr">Türkçe</SelectItem>
                            <SelectItem value="auto">Auto</SelectItem>
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <Button type="submit" disabled={updateMutation.isPending}>
                    {t("common.save")}
                  </Button>
                </form>
              </Form>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("settings.organization")}</CardTitle>
            <CardDescription>{t("settings.organizationHint")}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1 text-sm">
              <div className="text-muted-foreground">{t("admin.currentOrg")}</div>
              <div className="font-medium">
                {orgQuery.data?.name ?? organizationId ?? "—"}
              </div>
              <div className="font-mono text-xs text-muted-foreground">
                {orgQuery.data?.slug}
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">
                {t("settings.switchOrganization")}
              </label>
              <Select
                value={organizationId ?? undefined}
                onValueChange={(value) => {
                  switchOrg(value);
                  toast.success(t("common.success"));
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder={t("auth.organization")} />
                </SelectTrigger>
                <SelectContent>
                  {(orgsQuery.data?.items ?? []).map((org) => (
                    <SelectItem key={org.id} value={org.id}>
                      {org.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("common.theme")}</CardTitle>
            <CardDescription>{t("settings.themeHint")}</CardDescription>
          </CardHeader>
          <CardContent>
            <Select value={theme ?? "system"} onValueChange={setTheme}>
              <SelectTrigger className="max-w-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="light">{t("common.light")}</SelectItem>
                <SelectItem value="dark">{t("common.dark")}</SelectItem>
                <SelectItem value="system">{t("common.system")}</SelectItem>
              </SelectContent>
            </Select>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("common.language")}</CardTitle>
            <CardDescription>{t("settings.languageHint")}</CardDescription>
          </CardHeader>
          <CardContent>
            <Select
              value={i18n.language?.startsWith("tr") ? "tr" : "en"}
              onValueChange={changeLanguage}
            >
              <SelectTrigger className="max-w-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="en">English</SelectItem>
                <SelectItem value="tr">Türkçe</SelectItem>
              </SelectContent>
            </Select>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
