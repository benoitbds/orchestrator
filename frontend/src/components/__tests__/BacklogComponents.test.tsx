import { render, screen } from "@testing-library/react";
import { BacklogItem } from "../BacklogItem";
import { BacklogColumn } from "../BacklogColumn";
import { BacklogColumnVirtuoso } from "../BacklogColumnVirtuoso";

global.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
} as any;

global.IntersectionObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
} as any;

describe("BacklogItem", () => {
  it("renders title, status and tags", () => {
    render(
      <ul>
        <BacklogItem
          id="1"
          title="Test Item"
          status="Todo"
          tags={["bug", "urgent"]}
        />
      </ul>
    );
    expect(screen.getByText("Test Item")).toBeInTheDocument();
    expect(screen.getByText("Todo")).toBeInTheDocument();
    expect(screen.getByText("bug")).toBeInTheDocument();
    expect(screen.getByText("urgent")).toBeInTheDocument();
  });

  it("handles absence of status and tags", () => {
    render(
      <ul>
        <BacklogItem id="2" title="Simple" />
      </ul>
    );
    expect(screen.getByText("Simple")).toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});

describe("BacklogColumn", () => {
  const items = [
    { id: "1", title: "A" },
    { id: "2", title: "B" },
  ];

  it("renders sticky header and items", () => {
    render(<BacklogColumn items={items} />);
    const header = screen.getByText("Backlog");
    expect(header).toBeInTheDocument();
    expect(header.parentElement).toHaveClass("sticky");
    expect(screen.getAllByRole("listitem").length).toBe(2);
  });

  it("renders without items", () => {
    render(<BacklogColumn items={[]} />);
    expect(screen.queryAllByRole("listitem").length).toBe(0);
  });
});

describe("BacklogColumnVirtuoso", () => {
  const items = Array.from({ length: 3 }).map((_, i) => ({
    id: String(i),
    title: `Item ${i}`,
  }));

  it("renders header and list container", () => {
    render(
      <div style={{ height: 300 }}>
        <BacklogColumnVirtuoso items={items} />
      </div>
    );
    expect(screen.getByText("Backlog")).toBeInTheDocument();
    expect(screen.getByTestId("virtuoso-item-list")).toBeInTheDocument();
  });

  it("handles empty items", () => {
    render(
      <div style={{ height: 300 }}>
        <BacklogColumnVirtuoso items={[]} />
      </div>
    );
    expect(screen.getByText("Backlog")).toBeInTheDocument();
    expect(screen.getByTestId("virtuoso-item-list").childElementCount).toBe(0);
  });
});

