import { render, screen } from "@testing-library/react";

import Home from "../page";

describe("Home", () => {
  it("renders the Agent4BA ASCII art", () => {
    render(<Home />);

    expect(screen.getByText("Agent4BA")).toHaveClass("sr-only");
    expect(screen.getByText(/_____/)).toBeInTheDocument();
  });
});
