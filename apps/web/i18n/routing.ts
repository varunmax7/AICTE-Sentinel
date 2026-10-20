import { defineRouting } from "next-intl/routing";

export const locales = ["en", "hi", "te", "ml", "ta", "kn"] as const;
export type Locale = (typeof locales)[number];

export const routing = defineRouting({
  locales,
  defaultLocale: "en",
});
