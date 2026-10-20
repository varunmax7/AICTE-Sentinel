import { getLocale } from "next-intl/server";

import { redirect } from "@/i18n/navigation";

export default async function RootPage() {
  redirect({ href: "/login", locale: await getLocale() });
}
