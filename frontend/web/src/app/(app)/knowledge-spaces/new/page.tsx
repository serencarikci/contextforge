"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { z } from "zod";

import { PageHeader } from "@/components/shared/page-header";
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
  FormDescription,
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
import { Textarea } from "@/components/ui/textarea";
import { knowledgeSpacesApi, projectsApi } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query-keys";
import { slugify } from "@/lib/utils";

const schema = z.object({
  name: z.string().min(2).max(200),
  slug: z
    .string()
    .min(1)
    .max(64)
    .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/),
  description: z.string().max(2000).optional().or(z.literal("")),
  visibility: z.enum(["organization", "restricted", "private"]),
  project_id: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

export default function NewKnowledgeSpacePage() {
  const { t } = useTranslation();
  const router = useRouter();
  const queryClient = useQueryClient();

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: "",
      slug: "",
      description: "",
      visibility: "organization",
      project_id: "none",
    },
  });

  const nameValue = form.watch("name");
  useEffect(() => {
    if (!form.getFieldState("slug").isDirty) {
      form.setValue("slug", slugify(nameValue), { shouldValidate: false });
    }
  }, [nameValue, form]);

  const projectsQuery = useQuery({
    queryKey: queryKeys.projects.list({ limit: 100, offset: 0 }),
    queryFn: () => projectsApi.list({ limit: 100, offset: 0 }),
  });

  const createMutation = useMutation({
    mutationFn: knowledgeSpacesApi.create,
    onSuccess: async (space) => {
      await queryClient.invalidateQueries({
        queryKey: queryKeys.knowledgeSpaces.all,
      });
      toast.success(t("common.success"));
      router.push(`/knowledge-spaces/${space.id}`);
    },
    onError: () => toast.error(t("common.error")),
  });

  const onSubmit = form.handleSubmit((values) => {
    createMutation.mutate({
      name: values.name,
      slug: values.slug,
      description: values.description || null,
      visibility: values.visibility,
      project_id:
        !values.project_id || values.project_id === "none"
          ? null
          : values.project_id,
    });
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("knowledgeSpaces.create")}
        description={t("knowledgeSpaces.createHint")}
        actions={
          <Button variant="outline" onClick={() => router.back()}>
            {t("common.back")}
          </Button>
        }
      />

      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>{t("knowledgeSpaces.details")}</CardTitle>
          <CardDescription>{t("knowledgeSpaces.createHint")}</CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={onSubmit} className="space-y-4">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("knowledgeSpaces.name")}</FormLabel>
                    <FormControl>
                      <Input {...field} autoFocus />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="slug"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("knowledgeSpaces.slug")}</FormLabel>
                    <FormControl>
                      <Input {...field} className="font-mono text-sm" />
                    </FormControl>
                    <FormDescription>
                      {t("knowledgeSpaces.slugHint")}
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("knowledgeSpaces.descriptionLabel")}</FormLabel>
                    <FormControl>
                      <Textarea rows={4} {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="visibility"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("knowledgeSpaces.visibility")}</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="organization">
                          {t("knowledgeSpaces.visibilityOrganization")}
                        </SelectItem>
                        <SelectItem value="restricted">
                          {t("knowledgeSpaces.visibilityRestricted")}
                        </SelectItem>
                        <SelectItem value="private">
                          {t("knowledgeSpaces.visibilityPrivate")}
                        </SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="project_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("nav.projects")}</FormLabel>
                    <Select
                      value={field.value ?? "none"}
                      onValueChange={field.onChange}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue
                            placeholder={t("knowledgeSpaces.noProject")}
                          />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="none">
                          {t("knowledgeSpaces.noProject")}
                        </SelectItem>
                        {(projectsQuery.data?.items ?? []).map((project) => (
                          <SelectItem key={project.id} value={project.id}>
                            {project.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <div className="flex justify-end gap-2 pt-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => router.push("/knowledge-spaces")}
                >
                  {t("common.cancel")}
                </Button>
                <Button type="submit" disabled={createMutation.isPending}>
                  {t("common.create")}
                </Button>
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
}
