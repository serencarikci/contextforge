"use client";

import { Languages } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { STORAGE_KEYS } from "@/lib/constants";

const LOCALES = [
  { code: "en", label: "English" },
  { code: "tr", label: "Türkçe" },
] as const;

export function LanguageSwitcher() {
  const { t, i18n } = useTranslation();
  const current = (i18n.resolvedLanguage ?? i18n.language ?? "en").slice(0, 2);

  function handleChange(next: string) {
    void i18n.changeLanguage(next);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEYS.locale, next);
    }
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          aria-label={t("common.language")}
        >
          <Languages className="size-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuRadioGroup value={current} onValueChange={handleChange}>
          {LOCALES.map((locale) => (
            <DropdownMenuRadioItem key={locale.code} value={locale.code}>
              {locale.label}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
