import { render, screen } from "@testing-library/react";
import DashboardLayout from "./DashboardLayout";

describe("DashboardLayout", () => {
  it("renders header and footer", () => {
    render(<DashboardLayout />);
    expect(screen.getByText("Header")).toBeInTheDocument();
    expect(screen.getByText("Footer")).toBeInTheDocument();
  });

  it("renders all backlog items", () => {
    render(<DashboardLayout />);
    expect(screen.getByText("Backlog Item 50")).toBeInTheDocument();
  });

  it("renders all messages", () => {
    render(<DashboardLayout />);
    expect(screen.getByText("Message 50")).toBeInTheDocument();
  });
});
