import { render, screen } from "@testing-library/react";

import Home from "../page";

describe("Home", () => {
  it("shows the stylised Agent4BA hero", () => {
    const { container } = render(<Home />);

    expect(screen.getByText("Agent4BA")).toHaveClass("sr-only");
    expect(container.querySelector("pre")?.textContent).toContain("_____");
  });

  it("links to the login workspace", () => {
    render(<Home />);

    const cta = screen.getByRole("link", { name: "Enter workspace" });
    expect(cta).toHaveAttribute("href", "/login");
  });
});
