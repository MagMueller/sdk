import { describe, expect, it, vi } from "vitest";

import { Browsers as V2Browsers } from "../src/v2/resources/browsers.js";
import { Browsers as V3Browsers } from "../src/v3/resources/browsers.js";

describe.each([
  ["v2", V2Browsers],
  ["v3", V3Browsers],
])("%s browser metadata", (_version, Browsers) => {
  it("sends metadata on create and as repeated-filter input on list", async () => {
    const http = {
      post: vi.fn(async () => ({})),
      get: vi.fn(async () => ({ items: [], totalItems: 0, pageNumber: 1, pageSize: 10 })),
    };
    const browsers = new Browsers(http as any);

    await browsers.create({ metadata: { team: "sdk", env: "test" } });
    await browsers.list({ metadata: ["team", "env=test"] });

    expect(http.post).toHaveBeenCalledWith("/browsers", {
      metadata: { team: "sdk", env: "test" },
    });
    expect(http.get).toHaveBeenCalledWith("/browsers", {
      metadata: ["team", "env=test"],
    });
  });
});
