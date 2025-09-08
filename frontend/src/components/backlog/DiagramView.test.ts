import dagre from 'dagre';

describe('dagre layout', () => {
  function layoutWithDefaultEdges(count: number) {
    const g = new dagre.graphlib.Graph();
    g.setGraph({});
    g.setDefaultEdgeLabel(() => ({}));
    for (let i = 0; i < count; i++) {
      g.setNode(i, { width: 100, height: 40 });
      if (i > 0) g.setEdge(i - 1, i);
    }
    dagre.layout(g);
    return g.nodes().length;
  }

  it('handles many nodes when edges have labels', () => {
    expect(() => layoutWithDefaultEdges(50)).not.toThrow();
  });

  it('throws when edge labels are missing', () => {
    const g = new dagre.graphlib.Graph();
    g.setGraph({});
    g.setNode(0, { width: 100, height: 40 });
    g.setNode(1, { width: 100, height: 40 });
    g.setEdge(0, 1); // missing label
    expect(() => dagre.layout(g)).toThrow();
  });
});
