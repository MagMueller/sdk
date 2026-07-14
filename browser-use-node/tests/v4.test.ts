import { describe, expect, it, vi } from "vitest";

import { Runs } from "../src/v4/resources/runs.js";
import { Sessions } from "../src/v4/resources/sessions.js";

const RUN_ID = "00000000-0000-0000-0000-000000000001";
const SESSION_ID = "00000000-0000-0000-0000-000000000002";

function runSummary(status: string) {
  return {
    id: RUN_ID,
    task: "Find pricing",
    title: null,
    model: "minimax-m3",
    contextLimit: 200000,
    status,
    result: status === "completed" ? "done" : null,
    error: null,
    sessionId: SESSION_ID,
    workspaceId: null,
    totalInputTokens: 1,
    totalOutputTokens: 1,
    totalCostUsd: "0.01",
    createdAt: "2026-01-01T00:00:00Z",
    updatedAt: "2026-01-01T00:00:00Z",
  };
}

describe("v4 runs.waitForCompletion", () => {
  it("polls status until terminal, then fetches the full run once", async () => {
    const statuses = ["queued", "running", "completed"];
    let statusCalls = 0;
    let getCalls = 0;
    const http = {
      get: vi.fn(async (path: string) => {
        if (path === `/runs/${RUN_ID}/status`) {
          return { status: statuses[statusCalls++] };
        }
        if (path === `/runs/${RUN_ID}`) {
          getCalls++;
          return runSummary("completed");
        }
        throw new Error(`Unexpected GET ${path}`);
      }),
    };
    const runs = new Runs(http as any);

    const run = await runs.waitForCompletion(RUN_ID, { interval: 1 });

    expect(statusCalls).toBe(3);
    expect(getCalls).toBe(1);
    expect(run.status).toBe("completed");
    expect(run.result).toBe("done");
  });

  it("stops immediately on failed status", async () => {
    const http = {
      get: vi.fn(async (path: string) =>
        path.endsWith("/status") ? { status: "failed" } : runSummary("failed"),
      ),
    };
    const runs = new Runs(http as any);

    const run = await runs.waitForCompletion(RUN_ID, { interval: 1 });

    expect(run.status).toBe("failed");
  });

  it("throws when the timeout elapses before a terminal status", async () => {
    const http = {
      get: vi.fn(async () => ({ status: "running" })),
    };
    const runs = new Runs(http as any);

    await expect(
      runs.waitForCompletion(RUN_ID, { timeout: 10, interval: 1 }),
    ).rejects.toThrow(/did not complete/);
  });
});

describe("v4 runs pagination + events", () => {
  it("passes cursor pagination params on list", async () => {
    const http = {
      get: vi.fn(async () => ({ runs: [], nextCursor: null, hasMore: false })),
    };
    const runs = new Runs(http as any);

    await runs.list({ sessionId: SESSION_ID, cursor: "abc", limit: 5 });

    expect(http.get).toHaveBeenCalledWith("/runs", {
      sessionId: SESSION_ID,
      cursor: "abc",
      limit: 5,
    });
  });

  it("fetches events incrementally via after", async () => {
    const pages: Record<string, unknown> = {
      first: {
        events: [
          { runId: RUN_ID, id: 1, ts: "2026-01-01T00:00:00Z", type: "step", data: {} },
          { runId: RUN_ID, id: 2, ts: "2026-01-01T00:00:01Z", type: "step", data: {} },
        ],
        nextAfter: 2,
        hasMore: true,
      },
      second: {
        events: [
          { runId: RUN_ID, id: 3, ts: "2026-01-01T00:00:02Z", type: "done", data: {} },
        ],
        nextAfter: 3,
        hasMore: false,
      },
    };
    const http = {
      get: vi.fn(async (_path: string, query?: Record<string, unknown>) =>
        query?.after === 2 ? pages.second : pages.first,
      ),
    };
    const runs = new Runs(http as any);

    const first = await runs.events(RUN_ID, { limit: 2 });
    expect(first.nextAfter).toBe(2);
    expect(first.hasMore).toBe(true);

    const second = await runs.events(RUN_ID, { after: first.nextAfter, limit: 2 });
    expect(http.get).toHaveBeenLastCalledWith(`/runs/${RUN_ID}/events`, { after: 2, limit: 2 });
    expect(second.hasMore).toBe(false);
    expect(second.events[0].id).toBe(3);
  });
});

describe("v4 sessions queue", () => {
  const queuedMessage = {
    id: 7,
    sessionId: SESSION_ID,
    runId: null,
    status: "pending",
    text: "also check the careers page",
    createdAt: "2026-01-01T00:00:00Z",
  };

  it("sends a message to the queue", async () => {
    const http = {
      post: vi.fn(async () => queuedMessage),
    };
    const sessions = new Sessions(http as any);

    const msg = await sessions.sendMessage(SESSION_ID, {
      text: "also check the careers page",
      interrupt: true,
    });

    expect(http.post).toHaveBeenCalledWith(`/sessions/${SESSION_ID}/queue`, {
      text: "also check the careers page",
      interrupt: true,
    });
    expect(msg.status).toBe("pending");
  });

  it("lists pending queued messages", async () => {
    const http = {
      get: vi.fn(async () => ({ queue: [queuedMessage] })),
    };
    const sessions = new Sessions(http as any);

    const resp = await sessions.queue(SESSION_ID);

    expect(http.get).toHaveBeenCalledWith(`/sessions/${SESSION_ID}/queue`);
    expect(resp.queue).toHaveLength(1);
  });

  it("removes a queued message", async () => {
    const http = {
      delete: vi.fn(async () => ({ ...queuedMessage, status: "cancelled" })),
    };
    const sessions = new Sessions(http as any);

    const msg = await sessions.removeMessage(SESSION_ID, 7);

    expect(http.delete).toHaveBeenCalledWith(`/sessions/${SESSION_ID}/queue/7`);
    expect(msg.status).toBe("cancelled");
  });

  it("passes cursor pagination params on list", async () => {
    const http = {
      get: vi.fn(async () => ({ sessions: [], nextCursor: null, hasMore: false })),
    };
    const sessions = new Sessions(http as any);

    await sessions.list({ cursor: "xyz", limit: 10 });

    expect(http.get).toHaveBeenCalledWith("/sessions", { cursor: "xyz", limit: 10 });
  });
});
