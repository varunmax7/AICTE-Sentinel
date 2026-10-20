import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it } from "vitest";

import enMessages from "@/messages/en.json";

import { StatusChip } from "./status-chip";

function renderWithIntl(children: React.ReactNode) {
  return render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      {children}
    </NextIntlClientProvider>
  );
}

describe("StatusChip", () => {
  it("renders the translated label for a status", () => {
    renderWithIntl(<StatusChip status="APPROVED_WITH_CONDITIONS" />);
    expect(screen.getByText("Approved with Conditions")).toBeInTheDocument();
  });

  it("renders a different label for a different status", () => {
    renderWithIntl(<StatusChip status="REJECTED" />);
    expect(screen.getByText("Rejected")).toBeInTheDocument();
  });
});
