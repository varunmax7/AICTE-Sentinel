import { notFound } from "next/navigation";

import { ComponentGallery } from "./gallery";

/**
 * Storybook-like component gallery (IMPLEMENTATION.md §19 Phase P1 task
 * list: "/dev/components page (dev only) showing every component in both
 * themes and all locales"). All locales are covered by visiting this route
 * under each locale prefix (/en/dev/components, /hi/dev/components, ...);
 * both themes are rendered side by side on the page itself.
 */
export default function DevComponentsPage() {
  if (process.env.NODE_ENV === "production") {
    notFound();
  }
  return <ComponentGallery />;
}
