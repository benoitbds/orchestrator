import { render, screen } from "@testing-library/react";
import RunProgress from "./RunProgress";

describe("RunProgress", () => {
  const baseRun = { run_id: "1", status: "running" };

  it("renders segments for provided steps", () => {
    const run = {
      ...baseRun,
      steps: [
        { step: "plan", start: "2024-01-01T00:00:00Z", end: "2024-01-01T00:01:00Z" },
        { step: "execute", start: "2024-01-01T00:01:00Z", end: "2024-01-01T00:02:00Z" },
      ],
    };
    render(<RunProgress run={run} />);
    expect(screen.getByTitle("plan")).toBeInTheDocument();
    expect(screen.getByTitle("execute")).toBeInTheDocument();
  });

  it("shows loading skeleton when steps are undefined", () => {
    render(<RunProgress run={baseRun as any} />);
    expect(screen.getByTestId("timeline-loading")).toBeInTheDocument();
  });

  it("shows loading skeleton when steps array is empty", () => {
    render(<RunProgress run={{ ...baseRun, steps: [] }} />);
    expect(screen.getByTestId("timeline-loading")).toBeInTheDocument();
  });
});
