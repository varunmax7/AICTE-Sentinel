"use client";

import { ThemeProvider as NextThemesProvider } from "next-themes";
import type { ComponentProps } from "react";

/**
 * next-themes, configured per IMPLEMENTATION.md §7.2: `data-theme="light"` /
 * `data-theme="dark"` on <html>, defaulting to the user's system preference.
 * `styles/tokens.css` reads that attribute (and `prefers-color-scheme` as a
 * fallback) to pick the right CSS variables.
 */
export function ThemeProvider({ children, ...props }: ComponentProps<typeof NextThemesProvider>) {
  return (
    <NextThemesProvider
      attribute="data-theme"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
      {...props}
    >
      {children}
    </NextThemesProvider>
  );
}
