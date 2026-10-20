import type { Metadata } from "next";
import { hasLocale, NextIntlClientProvider } from "next-intl";
import { getMessages } from "next-intl/server";
import { notFound } from "next/navigation";

import { ThemeProvider } from "@/components/theme/theme-provider";
import { indicLocales, inter, jetbrainsMono, scriptFontByLocale } from "@/lib/fonts";

import { routing } from "../../i18n/routing";
import "../globals.css";

export const metadata: Metadata = {
  title: "AICTE Approval & Compliance Portal",
  description:
    "Integrated AICTE Approval Workflow Automation, Compliance Monitoring and Alert Management System",
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }

  const scriptFont = scriptFontByLocale[locale] ?? scriptFontByLocale.en;
  const messages = await getMessages();

  return (
    <html
      lang={locale}
      data-script={indicLocales.has(locale) ? "indic" : "latin"}
      className={`${inter.variable} ${jetbrainsMono.variable} ${scriptFont.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <body className="min-h-full">
        <NextIntlClientProvider locale={locale} messages={messages}>
          <ThemeProvider>{children}</ThemeProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
