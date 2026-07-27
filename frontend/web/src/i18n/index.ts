"use client";

import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import { initReactI18next } from "react-i18next";

import { STORAGE_KEYS } from "@/lib/constants";
import en from "@/i18n/locales/en.json";
import tr from "@/i18n/locales/tr.json";

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      tr: { translation: tr },
    },
    fallbackLng: "en",
    supportedLngs: ["en", "tr"],
    interpolation: { escapeValue: false },
    detection: {
      order: ["localStorage", "navigator"],
      lookupLocalStorage: STORAGE_KEYS.locale,
      caches: ["localStorage"],
    },
  });

export default i18n;
