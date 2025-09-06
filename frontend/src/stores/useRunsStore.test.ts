import { beforeEach, describe, expect, it } from "vitest";
import { useRunsStore } from "./useRunsStore";

describe("useRunsStore", () => {
  beforeEach(() => {
    useRunsStore.setState({ runs: {}, currentRunId: undefined });
  });

  it("deduplicates summary updates", () => {
    const { startRun, appendSummaryOnce } = useRunsStore.getState();
    startRun("r1");
    appendSummaryOnce("r1", "hello");
    appendSummaryOnce("r1", "hello");
    const run = useRunsStore.getState().runs["r1"];
    expect(run.summary).toBe("hello");
    expect(run.events.length).toBe(0);
  });

  it("handles missing run gracefully", () => {
    const { appendSummaryOnce } = useRunsStore.getState();
    appendSummaryOnce("missing", "hi");
    expect(useRunsStore.getState().runs["missing"]).toBeUndefined();
  });

  it("upgrades run id", () => {
    const { startRun, appendSummaryOnce, upgradeRunId } =
      useRunsStore.getState();
    startRun("temp");
    appendSummaryOnce("temp", "res");
    upgradeRunId("temp", "real");
    const state = useRunsStore.getState();
    expect(state.runs["temp"]).toBeUndefined();
    expect(state.runs["real"].summary).toBe("res");
  });

  it("ignores upgrade when temp id missing", () => {
    const before = useRunsStore.getState().runs;
    useRunsStore.getState().upgradeRunId("missing", "real");
    expect(useRunsStore.getState().runs).toEqual(before);
  });
});
