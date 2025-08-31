import { RefObject, useCallback } from 'react';
import { select } from 'd3-selection';

export interface BBox { x: number; y: number; width: number; height: number; }

export function computeFit(container: { width: number; height: number }, box: BBox) {
  const scale = Math.min(container.width / box.width, container.height / box.height, 2.5);
  const x = (container.width - box.width * scale) / 2 - box.x * scale;
  const y = (container.height - box.height * scale) / 2 - box.y * scale;
  return { scale, x, y };
}

export function useAutoFit(svgRef: RefObject<SVGSVGElement>) {
  return useCallback((box: BBox) => {
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const { scale, x, y } = computeFit(rect, box);
    select(svg).select('g').attr('transform', `translate(${x},${y}) scale(${scale})`);
  }, [svgRef]);
}
