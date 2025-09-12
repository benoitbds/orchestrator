import { render, screen, fireEvent } from "@testing-library/react";
import { vi } from "vitest";
import RunTimeline from "./RunTimeline";
vi.mock("@/lib/firebase", () => ({ auth: { currentUser: { getIdToken: vi.fn().mockResolvedValue(null) } } }));

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
          total_tokens: 5,
          cost_eur: 0.1,
          by_agent: [
            {
              agent: "alpha",
              prompt_tokens: 2,
              completion_tokens: 3,
              total_tokens: 5,
              cost_eur: 0.1,
            },
          ],
        }),
      });

    render(<RunTimeline runId="1" />);
    expect(await screen.findByText(/Agent alpha/)).toBeInTheDocument();
    expect(screen.getByText(/Tokens: 5/)).toBeInTheDocument();
    expect(screen.getByText(/€0\.1000/)).toBeInTheDocument();
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
        json: async () => ({
          total_tokens: 0,
          cost_eur: 0,
          by_agent: [],
        }),
      })
      .mockResolvedValueOnce({ ok: true, text: async () => "full" });

    render(<RunTimeline runId="1" />);
    const view = await screen.findByText("View");
    fireEvent.click(view);
    expect(await screen.findByText("full")).toBeInTheDocument();
  });
});
