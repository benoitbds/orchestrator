import { render, screen } from "@testing-library/react";

import { AgentIdentity } from "../AgentIdentity";

describe("AgentIdentity", () => {
  it("renders the Agent4BA ASCII art and tagline", () => {
    const { container } = render(<AgentIdentity />);

    const asciiBlock = container.querySelector("pre");
    expect(asciiBlock?.textContent).toContain("_____");
    expect(
      screen.getByText(/Autonomous backlog architect/i),
    ).toBeInTheDocument();
  });

  it("exposes an accessible label for assistive technologies", () => {
    render(<AgentIdentity />);

    expect(screen.getByText("Agent4BA")).toBeInTheDocument();
  });

  it("supports compact sizing for mobile layouts", () => {
    const { container } = render(
      <AgentIdentity size="mobile" className="custom-wrapper" />,
    );

    const root = container.querySelector("div");
    const asciiBlock = container.querySelector("pre");

    expect(root).toHaveClass("custom-wrapper");
    expect(asciiBlock?.className).toContain("text-[7px]");
  });
});

