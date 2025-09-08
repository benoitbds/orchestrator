"use client";

import { useEffect, useMemo, useRef, useState } from 'react';
import dagre from 'dagre';
import { forceSimulation, forceCollide, forceX, forceY, forceLink } from 'd3-force';
import { zoom } from 'd3-zoom';
import { select } from 'd3-selection';
import { BacklogItem } from '@/models/backlogItem';
import { useItems } from '@/lib/hooks';
import { getLayout, saveLayout, LayoutNode } from '@/lib/layout';
import { useAutoFit, BBox } from './useAutoFit';
import { Button } from '@/components/ui/button';

interface DiagramViewProps {
  projectId: number | null;
  onEdit: (item: BacklogItem) => void;
}

export interface NodeDatum {
  id: number;
  title: string;
  type: BacklogItem['type'];
  parent_id: number | null;
  rank: number;
  width: number;
  height: number;
  x: number;
  y: number;
  fx?: number;
  fy?: number;
  pinned?: boolean;
  generated_by_ai?: boolean;
}

const typeColor: Record<string, string> = {
  Epic: '#8b5cf6',
  Capability: '#a78bfa',
  Feature: '#3b82f6',
  US: '#10b981',
  UC: '#f59e0b',
};

const rankByType: Record<BacklogItem['type'], number> = {
  Epic: 0,
  Capability: 1,
  Feature: 2,
  US: 3,
  UC: 4,
};

export function DiagramView({ projectId, onEdit }: DiagramViewProps) {
  const { data: items } = useItems(projectId);
  const [nodes, setNodes] = useState<NodeDatum[]>([]);
  const [edges, setEdges] = useState<{ source: number; target: number }[]>([]);
  const [focused, setFocused] = useState<number | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const zoomRef = useRef(returnZoom());
  const autoFit = useAutoFit(svgRef);
  const saveTimer = useRef<NodeJS.Timeout | null>(null);

  function returnZoom() {
    return zoom<SVGSVGElement, unknown>().scaleExtent([0.2, 2.5]);
  }

  // Measure text width
  const measure = useMemo(() => {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    return (text: string) => {
      if (!ctx) return 120;
      ctx.font = '12px sans-serif';
      return Math.max(120, ctx.measureText(text).width + 24);
    };
  }, []);

  // Build graph
  useEffect(() => {
    if (!items || !projectId) return;
    const n: NodeDatum[] = items.map(item => ({
      id: item.id,
      title: item.title,
      type: item.type,
      parent_id: item.parent_id,
      rank: rankByType[item.type],
      width: measure(item.title),
      height: 40,
      x: 0,
      y: 0,
      generated_by_ai: item.generated_by_ai,
    }));
    const e = n
      .filter(nd => nd.parent_id !== null)
      .map(nd => ({ source: nd.parent_id as number, target: nd.id }));
    setNodes(n);
    setEdges(e);
  }, [items, measure, projectId]);

  // Merge saved layout
  useEffect(() => {
    if (!projectId || nodes.length === 0) return;
    getLayout(projectId).then(saved => {
      setNodes(nds =>
        nds.map(nd => {
          const found = saved.find(s => s.item_id === nd.id);
          return found ? { ...nd, x: found.x, y: found.y, pinned: found.pinned, fx: found.pinned ? found.x : undefined, fy: found.pinned ? found.y : undefined } : nd;
        })
      );
    });
  }, [projectId, nodes.length]);

  // Layout with dagre + force
  useEffect(() => {
    if (nodes.length === 0 || edges.length === 0) return;
    const g = new dagre.graphlib.Graph();
    g.setGraph({ rankdir: 'LR', nodesep: 40, ranksep: 80 });
    g.setDefaultEdgeLabel(() => ({}));
    nodes.forEach(nd => g.setNode(nd.id, { width: nd.width, height: nd.height, rank: nd.rank }));
    edges.forEach(e => g.setEdge(e.source, e.target));
    dagre.layout(g);
    const initial = nodes.map(nd => {
      const pos = g.node(nd.id);
      return { ...nd, x: nd.pinned ? nd.x : pos.x, y: nd.pinned ? nd.y : pos.y };
    });
    const sim = forceSimulation(initial)
      .force('collide', forceCollide<NodeDatum>(d => Math.max(d.width, d.height) / 2 + 8))
      .force('x', forceX<NodeDatum>(d => d.rank * 280).strength(1))
      .force('y', forceY<NodeDatum>(0).strength(0.05))
      .force('link', forceLink<NodeDatum, { source: number; target: number }>(edges).id(d => (d as any).id).distance(120))
      .alpha(0.5);
    for (let i = 0; i < 300 && sim.alpha() > 0.02; i++) {
      sim.tick();
    }
    sim.stop();
    setNodes(sim.nodes() as NodeDatum[]);
  }, [nodes.length, edges]);

  // Setup zoom
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    select(svg).call(zoomRef.current.on('zoom', (e) => {
      select(svg).select('g').attr('transform', e.transform);
    }));
    // initial fit
    const bbox = computeBBox(nodes);
    if (bbox) autoFit(bbox);
  }, [nodes, autoFit]);

  // Dragging
  const dragNode = useRef<NodeDatum | null>(null);
  function onPointerDown(e: React.PointerEvent, node: NodeDatum) {
    dragNode.current = node;
    node.fx = node.x;
    node.fy = node.y;
    (e.target as Element).setPointerCapture(e.pointerId);
  }
  function onPointerMove(e: React.PointerEvent) {
    if (!dragNode.current) return;
    const pt = pointer(e, svgRef.current);
    dragNode.current.x = pt[0];
    dragNode.current.y = pt[1];
    dragNode.current.fx = pt[0];
    dragNode.current.fy = pt[1];
    setNodes([...nodes]);
  }
  function onPointerUp(e: React.PointerEvent) {
    if (!dragNode.current) return;
    dragNode.current.pinned = true;
    dragNode.current.fx = dragNode.current.x;
    dragNode.current.fy = dragNode.current.y;
    dragNode.current = null;
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => {
      if (!projectId) return;
      saveLayout(projectId, nodes.map(n => ({ item_id: n.id, x: n.x, y: n.y, pinned: n.pinned })));
    }, 500);
  }

  function pointer(event: React.PointerEvent, svg: SVGSVGElement | null) {
    const pt = svg?.createSVGPoint();
    if (!pt) return [0, 0];
    pt.x = event.clientX;
    pt.y = event.clientY;
    const gpt = pt.matrixTransform(svg.getScreenCTM()?.inverse());
    return [gpt.x, gpt.y];
  }

  // Focus subtree
  const visible = useMemo(() => {
    if (!focused) return nodes.map(n => n.id);
    const ids = new Set<number>();
    const queue = [focused];
    while (queue.length) {
      const id = queue.shift()!;
      ids.add(id);
      edges.filter(e => e.source === id).forEach(e => queue.push(e.target));
    }
    return Array.from(ids);
  }, [focused, nodes, edges]);

  useEffect(() => {
    // auto fit focused subtree
    const visNodes = nodes.filter(n => visible.includes(n.id));
    const bbox = computeBBox(visNodes);
    if (bbox) autoFit(bbox);
  }, [focused]);

  function computeBBox(nds: NodeDatum[]): BBox | null {
    if (nds.length === 0) return null;
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    nds.forEach(n => {
      minX = Math.min(minX, n.x - n.width / 2);
      maxX = Math.max(maxX, n.x + n.width / 2);
      minY = Math.min(minY, n.y - n.height / 2);
      maxY = Math.max(maxY, n.y + n.height / 2);
    });
    return { x: minX, y: minY, width: maxX - minX, height: maxY - minY };
  }

  function handleReset() {
    setFocused(null);
    const bbox = computeBBox(nodes);
    if (bbox) autoFit(bbox);
  }

  if (!projectId) return null;

  if (nodes.length >= 300) {
    return <div className="p-4 text-sm">Diagram too large to render.</div>;
  }

  return (
    <div className="relative h-[600px] border rounded">
      <svg ref={svgRef} className="w-full h-full" onPointerMove={onPointerMove} onPointerUp={onPointerUp}>
        <g>
          {edges.map((e, i) => {
            const path = buildEdgePath(nodes, e);
            return path ? <path key={i} d={path} fill="none" stroke="#ccc" /> : null;
          })}
          {nodes.map(n => (
            <g
              key={n.id}
              opacity={visible.includes(n.id) ? 1 : 0.2}
              transform={`translate(${n.x - n.width / 2},${n.y - n.height / 2})`}
              onPointerDown={(e) => onPointerDown(e, n)}
              onDoubleClick={() => setFocused(focused === n.id ? null : n.id)}
            >
              <rect width={n.width} height={n.height} rx={20} fill={typeColor[n.type]} />
              {n.generated_by_ai && (
                <g
                  className="pointer-events-none"
                  transform={`translate(${n.width - 18},4)`}
                >
                  <rect width={14} height={14} rx={3} fill="#8b5cf6" />
                  <text
                    x={7}
                    y={7}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize="8"
                    fill="#fff"
                  >
                    IA
                  </text>
                </g>
              )}
              <title>{`${n.title} (${n.type})`}</title>
              <text
                x={n.width / 2}
                y={n.height / 2}
                textAnchor="middle"
                dominantBaseline="middle"
                fill="#fff"
                fontSize="12"
                className="cursor-pointer"
                onClick={(e) => {
                  e.stopPropagation();
                  const item = items?.find(i => i.id === n.id);
                  if (item) onEdit(item);
                }}
                onPointerDown={(e) => e.stopPropagation()}
              >
                {n.title.length > 20 ? n.title.slice(0, 20) + "…" : n.title}
              </text>
            </g>
          ))}
        </g>
      </svg>
      <div className="absolute top-2 right-2 flex gap-2">
        <Button size="sm" onClick={() => zoomRef.current.scaleBy(select(svgRef.current!), 1.2)}>Zoom In</Button>
        <Button size="sm" onClick={() => zoomRef.current.scaleBy(select(svgRef.current!), 0.8)}>Zoom Out</Button>
        <Button size="sm" onClick={handleReset}>Reset</Button>
      </div>
    </div>
  );
}

export function buildEdgePath(nodes: NodeDatum[], edge: { source: number; target: number }): string | null {
  const s = nodes.find(n => n.id === edge.source);
  const t = nodes.find(n => n.id === edge.target);
  if (!s || !t) return null;
  return `M${s.x + s.width / 2},${s.y} Q${(s.x + t.x) / 2},${s.y} ${t.x - t.width / 2},${t.y}`;
}
