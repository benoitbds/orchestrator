import { render, screen, fireEvent, within } from "@testing-library/react";
import RunTimeline from "./RunTimeline";
import { vi } from "vitest";

vi.mock("@/hooks/useRunWatcher", () => ({
  default: () => {},
}));

describe("RunTimeline", () => {
  const steps = [
    { order: 1, node: "plan", timestamp: "2024-01-01T00:00:00Z", content: "plan" },
    { order: 2, node: "tool:create_item", timestamp: "2024-01-01T00:01:00Z", content: "create" },
  ];

  it("renders provided steps", () => {
    render(<RunTimeline runId="1" initialSteps={steps} />);
    expect(screen.getByText("Planification")).toBeInTheDocument();
    expect(screen.getByText("Création")).toBeInTheDocument();
  });

  it("shows fallback when no steps", () => {
    render(<RunTimeline runId="1" initialSteps={[]} />);
    expect(screen.getByText(/No steps yet/i)).toBeInTheDocument();
  });

  it("opens modal with step details on click", () => {
    render(<RunTimeline runId="1" initialSteps={steps} />);
    fireEvent.click(screen.getByText("Planification"));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText("plan")).toBeInTheDocument();
  });
});
