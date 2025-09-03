import { render, screen, fireEvent } from "@testing-library/react";
import { vi } from "vitest";
import RunTimeline from "./RunTimeline";

describe("RunTimeline", () => {
  beforeEach(() => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://api.test";
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders timeline and cost", async () => {
    global.fetch = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          events: [
            { type: "agent.span.start", timestamp: "2024-01-01", name: "alpha" },
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          tokens: 5,
          cost: 0.1,
          by_agent: { alpha: { tokens: 5, cost: 0.1 } },
        }),
      });

    render(<RunTimeline runId="1" />);
    expect(await screen.findByText(/Agent alpha/)).toBeInTheDocument();
    expect(screen.getByText(/Tokens: 5/)).toBeInTheDocument();
  });

  it("handles fetch error", async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: false, json: async () => ({}) });
    render(<RunTimeline runId="1" />);
    expect(await screen.findByText(/Failed to load timeline/)).toBeInTheDocument();
  });

  it("opens modal with message content", async () => {
    global.fetch = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          events: [
            {
              type: "message",
              timestamp: "2024-01-01",
              role: "user",
              content: "hello",
              ref: "blob1",
            },
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ tokens: 0, cost: 0, by_agent: {} }),
      })
      .mockResolvedValueOnce({ ok: true, text: async () => "full" });

    render(<RunTimeline runId="1" />);
    const view = await screen.findByText("View");
    fireEvent.click(view);
    expect(await screen.findByText("full")).toBeInTheDocument();
  });
});
