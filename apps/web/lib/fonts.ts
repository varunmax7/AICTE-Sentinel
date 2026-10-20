/**
 * Typography (IMPLEMENTATION.md §7.3): Inter for UI, JetBrains Mono for
 * IDs/hashes, and a Noto Sans script family per Indic locale — applied on
 * `<html lang>` by the locale layout so each language renders in the script
 * actually designed for it instead of falling back to Inter's limited
 * non-Latin coverage.
 */

import {
  Inter,
  JetBrains_Mono,
  Noto_Sans_Devanagari,
  Noto_Sans_Kannada,
  Noto_Sans_Malayalam,
  Noto_Sans_Tamil,
  Noto_Sans_Telugu,
} from "next/font/google";

export const inter = Inter({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
export const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

const notoDevanagari = Noto_Sans_Devanagari({
  subsets: ["devanagari"],
  variable: "--font-script",
  display: "swap",
});
const notoTelugu = Noto_Sans_Telugu({
  subsets: ["telugu"],
  variable: "--font-script",
  display: "swap",
});
const notoMalayalam = Noto_Sans_Malayalam({
  subsets: ["malayalam"],
  variable: "--font-script",
  display: "swap",
});
const notoTamil = Noto_Sans_Tamil({
  subsets: ["tamil"],
  variable: "--font-script",
  display: "swap",
});
const notoKannada = Noto_Sans_Kannada({
  subsets: ["kannada"],
  variable: "--font-script",
  display: "swap",
});

/** Script font per locale; `en` has no Indic script so it falls back to Inter. */
export const scriptFontByLocale: Record<string, { variable: string }> = {
  en: { variable: "" },
  hi: notoDevanagari,
  te: notoTelugu,
  ml: notoMalayalam,
  ta: notoTamil,
  kn: notoKannada,
};

/** Indic locales use a taller line-height to avoid glyph clipping (§7.3). */
export const indicLocales = new Set(["hi", "te", "ml", "ta", "kn"]);
