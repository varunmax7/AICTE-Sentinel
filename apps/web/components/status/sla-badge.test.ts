import { describe, expect, it } from "vitest";

import { slaState } from "./sla-badge";

describe("slaState", () => {
  it("is on-time when more than 3 days remain", () => {
    expect(slaState(4)).toBe("on-time");
    expect(slaState(30)).toBe("on-time");
  });

  it("is due-soon within the 0-3 day window", () => {
    expect(slaState(3)).toBe("due-soon");
    expect(slaState(1)).toBe("due-soon");
    expect(slaState(0)).toBe("due-soon");
  });

  it("is overdue once days remaining goes negative", () => {
    expect(slaState(-1)).toBe("overdue");
    expect(slaState(-30)).toBe("overdue");
  });
});
