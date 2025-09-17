import type { ReactNode } from "react";
import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

vi.mock("@/context/BacklogContext", () => ({
  BacklogProvider: ({ children }: { children: ReactNode }) => (
    <div data-testid="backlog-provider">{children}</div>
  ),
}));

vi.mock("@/pages/AgentShell", () => ({
  AgentShell: () => <div data-testid="agent-shell">AgentShell</div>,
}));

vi.mock("sonner", () => ({
  Toaster: () => <div data-testid="toaster" />,
}));

import Home from "../page";

describe("Home", () => {
  it("wraps the agent experience with the backlog provider and toaster", () => {
    render(<Home />);

    const provider = screen.getByTestId("backlog-provider");
    expect(provider).toBeInTheDocument();
    expect(provider).toContainElement(screen.getByTestId("agent-shell"));
    expect(screen.getByTestId("toaster")).toBeInTheDocument();
  });
});
