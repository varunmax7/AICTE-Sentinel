import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./i18n/request.ts");

const nextConfig: NextConfig = {
  output: "standalone",
  // §6's canonical env var is `PUBLIC_API_URL` (no NEXT_PUBLIC_ prefix, since
  // it's shared with apps/api and apps/voice). Client components need the
  // API base URL though, and Next.js only inlines NEXT_PUBLIC_-prefixed vars
  // into the browser bundle — so re-expose it under that name here instead
  // of renaming the canonical var or duplicating it in .env.example.
  env: {
    NEXT_PUBLIC_API_URL: process.env.PUBLIC_API_URL ?? "http://localhost:8000",
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default withNextIntl(nextConfig);
