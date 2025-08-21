import { render, screen, fireEvent, within } from "@testing-library/react";
import RunTimeline, { TimelineStep } from "./RunTimeline";

describe("RunTimeline detail", () => {
  const steps: TimelineStep[] = [
    { order: 1, node: "plan", timestamp: "2024-01-01T00:00:00Z", content: "plan step" },
    { order: 2, node: "execute", timestamp: "2024-01-01T00:01:00Z", content: "execute step" },
  ];

  it("renders provided steps", () => {
    render(<RunTimeline steps={steps} />);
    expect(screen.getByText("plan")).toBeInTheDocument();
    expect(screen.getByText("execute")).toBeInTheDocument();
  });

  it("shows fallback when no steps", () => {
    render(<RunTimeline steps={[]} />);
    expect(screen.getByText(/No steps yet/i)).toBeInTheDocument();
  });

  it("opens modal with step details on click", () => {
    render(<RunTimeline steps={steps} />);
    fireEvent.click(screen.getByText("plan"));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText("plan step")).toBeInTheDocument();
  });
});
