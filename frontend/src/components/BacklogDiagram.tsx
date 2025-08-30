"use client";
import { useState, useMemo, useRef, useEffect } from 'react';
import { BacklogItem, isEpic, isCapability, isFeature, isUS, isUC } from '@/models/backlogItem';
import { useItems, TreeNode } from '@/lib/hooks';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import dynamic from 'next/dynamic';

const Loader2 = dynamic(() => import('lucide-react').then(mod => ({ default: mod.Loader2 })), { ssr: false });
const CpuIcon = dynamic(() => import('lucide-react').then(mod => ({ default: mod.Cpu })), { ssr: false });
const ZoomIn = dynamic(() => import('lucide-react').then(mod => ({ default: mod.ZoomIn })), { ssr: false });
const ZoomOut = dynamic(() => import('lucide-react').then(mod => ({ default: mod.ZoomOut })), { ssr: false });
const RotateCcw = dynamic(() => import('lucide-react').then(mod => ({ default: mod.RotateCcw })), { ssr: false });

const typeColors: { [key: string]: string } = {
  Epic: '#8b5cf6', // purple-500
  Capability: '#a78bfa', // purple-400
  Feature: '#3b82f6', // blue-500
  US: '#10b981', // green-500
  UC: '#f59e0b', // yellow-500
};

const stateColors: { [key: string]: string } = {
  Funnel: '#9ca3af',
  Reviewing: '#fb923c',
  Analyzing: '#eab308',
  Backlog: '#60a5fa',
  Implementing: '#6366f1',
  Done: '#10b981',
};

const statusColors: { [key: string]: string } = {
  Todo: '#9ca3af',
  Doing: '#eab308',
  Done: '#10b981',
};

interface NodePosition {
  x: number;
  y: number;
  item: TreeNode;
  level: number;
  angle: number;
  radius: number;
}

interface DiagramState {
  zoom: number;
  panX: number;
  panY: number;
  rotation: number;
  selectedNode: TreeNode | null;
  hoveredNode: TreeNode | null;
}

interface BacklogDiagramProps {
  projectId: number | null;
  onEdit: (item: BacklogItem) => void;
}

function calculateWebLayout(tree: TreeNode[], centerX: number, centerY: number): NodePosition[] {
  const positions: NodePosition[] = [];
  
  // First, flatten all nodes to get total count and create lookup
  const allNodes: TreeNode[] = [];
  const nodeDepth = new Map<number, number>();
  const nodeRelations = new Map<number, number[]>();
  
  const flattenNodes = (nodes: TreeNode[], depth: number = 0, parentId?: number) => {
    nodes.forEach(node => {
      allNodes.push(node);
      nodeDepth.set(node.id, depth);
      
      // Track relations for better web connectivity
      if (parentId) {
        if (!nodeRelations.has(parentId)) {
          nodeRelations.set(parentId, []);
        }
        nodeRelations.get(parentId)!.push(node.id);
      }
      
      if (node.children && node.children.length > 0) {
        flattenNodes(node.children as TreeNode[], depth + 1, node.id);
      }
    });
  };
  
  flattenNodes(tree);
  
  if (allNodes.length === 0) return positions;
  
  // Calculate positions using a web/network layout
  const calculateWebPositions = () => {
    const maxDepth = Math.max(...Array.from(nodeDepth.values()));
    const layers = Array.from({length: maxDepth + 1}, () => []);
    
    // Group nodes by depth level
    allNodes.forEach(node => {
      const depth = nodeDepth.get(node.id) || 0;
      layers[depth].push(node);
    });
    
    // Position nodes in concentric circles with better distribution
    layers.forEach((layerNodes, depth) => {
      if (layerNodes.length === 0) return;
      
      const layerRadius = depth === 0 ? 0 : Math.min(300, 80 + depth * 100);
      const angleStep = layerNodes.length === 1 ? 0 : (2 * Math.PI) / layerNodes.length;
      
      // Add some randomness to avoid perfect alignment
      const angleOffset = depth * Math.PI / 6; // Offset each layer
      
      layerNodes.forEach((node, index) => {
        let x, y, angle;
        
        if (depth === 0 && layerNodes.length === 1) {
          // Single root node at center
          x = centerX;
          y = centerY;
          angle = 0;
        } else {
          // Distribute nodes around the circle
          angle = angleOffset + index * angleStep;
          
          // Add small random offset for more organic web look
          const randomOffset = (Math.random() - 0.5) * 40;
          const actualRadius = layerRadius + randomOffset;
          
          x = centerX + Math.cos(angle) * actualRadius;
          y = centerY + Math.sin(angle) * actualRadius;
        }
        
        positions.push({
          x,
          y,
          item: node,
          level: depth,
          angle,
          radius: layerRadius,
        });
      });
    });
    
    // Apply force-directed adjustments for better web appearance
    applyForceDirectedLayout();
  };
  
  // Simple force-directed algorithm to improve node positioning
  const applyForceDirectedLayout = () => {
    const iterations = 20;
    const repulsionForce = 1000;
    const attractionForce = 0.1;
    const dampening = 0.8;
    
    for (let i = 0; i < iterations; i++) {
      positions.forEach(pos1 => {
        let forceX = 0;
        let forceY = 0;
        
        // Repulsion between all nodes
        positions.forEach(pos2 => {
          if (pos1.item.id === pos2.item.id) return;
          
          const dx = pos1.x - pos2.x;
          const dy = pos1.y - pos2.y;
          const distance = Math.sqrt(dx * dx + dy * dy);
          
          if (distance > 0 && distance < 200) {
            const force = repulsionForce / (distance * distance);
            forceX += (dx / distance) * force;
            forceY += (dy / distance) * force;
          }
        });
        
        // Attraction to parent/children
        const hasParent = pos1.item.parent_id;
        if (hasParent) {
          const parent = positions.find(p => p.item.id === pos1.item.parent_id);
          if (parent) {
            const dx = parent.x - pos1.x;
            const dy = parent.y - pos1.y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            
            if (distance > 100) { // Only attract if too far
              forceX += dx * attractionForce;
              forceY += dy * attractionForce;
            }
          }
        }
        
        // Apply forces with dampening (except for root nodes)
        if (pos1.level > 0) {
          pos1.x += forceX * dampening;
          pos1.y += forceY * dampening;
          
          // Keep within bounds
          pos1.x = Math.max(50, Math.min(750, pos1.x));
          pos1.y = Math.max(50, Math.min(550, pos1.y));
        }
      });
    }
  };
  
  calculateWebPositions();
  return positions;
}

function getNodeSize(type: string): { width: number; height: number } {
  switch (type) {
    case 'Epic':
      return { width: 120, height: 60 };
    case 'Capability':
      return { width: 100, height: 50 };
    case 'Feature':
      return { width: 80, height: 40 };
    case 'US':
    case 'UC':
      return { width: 60, height: 60 };
    default:
      return { width: 80, height: 40 };
  }
}

function getNodeColor(item: TreeNode): string {
  return typeColors[item.type] || '#6b7280';
}

function getStateColor(item: TreeNode): string {
  if ((item.type === 'Epic' || item.type === 'Capability') && 'state' in item && item.state) {
    return stateColors[item.state] || '#9ca3af';
  }
  if ((item.type === 'US' || item.type === 'UC') && 'status' in item && item.status) {
    return statusColors[item.status] || '#9ca3af';
  }
  return '#9ca3af';
}

export function BacklogDiagram({ projectId, onEdit }: BacklogDiagramProps) {
  const { tree, isLoading, error } = useItems(projectId);
  const svgRef = useRef<SVGSVGElement>(null);
  const [diagram, setDiagram] = useState<DiagramState>({
    zoom: 1,
    panX: 0,
    panY: 0,
    rotation: 0,
    selectedNode: null,
    hoveredNode: null,
  });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  const positions = useMemo(() => {
    if (!tree || tree.length === 0) return [];
    return calculateWebLayout(tree, 400, 300);
  }, [tree]);

  // Gestion des événements souris
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.target === svgRef.current) {
      setIsDragging(true);
      setDragStart({ x: e.clientX - diagram.panX, y: e.clientY - diagram.panY });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      setDiagram(prev => ({
        ...prev,
        panX: e.clientX - dragStart.x,
        panY: e.clientY - dragStart.y,
      }));
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
    setDiagram(prev => ({
      ...prev,
      zoom: Math.max(0.3, Math.min(3, prev.zoom * zoomFactor)),
    }));
  };

  const handleNodeClick = (item: TreeNode) => {
    setDiagram(prev => ({ ...prev, selectedNode: item }));
    onEdit(item);
  };

  const handleNodeHover = (item: TreeNode | null) => {
    setDiagram(prev => ({ ...prev, hoveredNode: item }));
  };

  const resetView = () => {
    setDiagram(prev => ({
      ...prev,
      zoom: 1,
      panX: 0,
      panY: 0,
      rotation: 0,
    }));
  };

  const zoomIn = () => {
    setDiagram(prev => ({ ...prev, zoom: Math.min(3, prev.zoom * 1.2) }));
  };

  const zoomOut = () => {
    setDiagram(prev => ({ ...prev, zoom: Math.max(0.3, prev.zoom / 1.2) }));
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="animate-spin" />
        <span className="ml-2">Chargement...</span>
      </div>
    );
  }

  if (error) {
    return <div className="text-red-500">Erreur de chargement des éléments.</div>;
  }

  if (!tree || tree.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        Aucun élément à afficher
      </div>
    );
  }

  return (
    <div className="relative bg-gradient-to-br from-slate-50 to-slate-100 h-96 overflow-hidden rounded-lg border">
      {/* Contrôles */}
      <div className="absolute top-4 right-4 z-10 flex gap-2">
        <Button size="sm" variant="outline" onClick={zoomIn}>
          <ZoomIn className="w-4 h-4" />
        </Button>
        <Button size="sm" variant="outline" onClick={zoomOut}>
          <ZoomOut className="w-4 h-4" />
        </Button>
        <Button size="sm" variant="outline" onClick={resetView}>
          <RotateCcw className="w-4 h-4" />
        </Button>
      </div>

      {/* Indicateur de zoom */}
      <div className="absolute top-4 left-4 z-10 bg-white/80 rounded px-2 py-1 text-xs">
        Zoom: {Math.round(diagram.zoom * 100)}%
      </div>

      {/* SVG Diagramme */}
      <svg
        ref={svgRef}
        width="100%"
        height="100%"
        viewBox="0 0 800 600"
        className="cursor-grab active:cursor-grabbing"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
      >
        <defs>
          {/* Gradients pour les nœuds */}
          {Object.entries(typeColors).map(([type, color]) => (
            <linearGradient key={type} id={`gradient-${type}`} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={color} stopOpacity="0.8" />
              <stop offset="100%" stopColor={color} stopOpacity="1" />
            </linearGradient>
          ))}
          
          {/* Filtre pour l'ombre */}
          <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="2" dy="2" stdDeviation="3" floodColor="rgba(0,0,0,0.3)" />
          </filter>
        </defs>

        <g 
          transform={`translate(${diagram.panX}, ${diagram.panY}) scale(${diagram.zoom}) rotate(${diagram.rotation}, 400, 300)`}
        >
          {/* Lignes de connexion principales (parent-enfant) */}
          {positions.map((pos) => {
            if (pos.level === 0) return null;
            const parent = positions.find(p => 
              pos.item.parent_id && p.item.id === pos.item.parent_id
            );
            if (!parent) return null;

            const isHighlighted = diagram.hoveredNode?.id === pos.item.id || diagram.hoveredNode?.id === parent.item.id;
            
            return (
              <g key={`connection-${pos.item.id}`}>
                {/* Main connection line */}
                <line
                  x1={parent.x}
                  y1={parent.y}
                  x2={pos.x}
                  y2={pos.y}
                  stroke={isHighlighted ? "#4f46e5" : "#cbd5e1"}
                  strokeWidth={isHighlighted ? "3" : "2"}
                  strokeDasharray={pos.item.generated_by_ai ? "5,5" : "none"}
                  className="transition-all duration-200"
                  opacity={isHighlighted ? 1 : 0.6}
                />
                
                {/* Connection indicator dot */}
                <circle
                  cx={parent.x + (pos.x - parent.x) * 0.5}
                  cy={parent.y + (pos.y - parent.y) * 0.5}
                  r="2"
                  fill={isHighlighted ? "#4f46e5" : "#94a3b8"}
                  className="transition-all duration-200"
                  opacity={isHighlighted ? 1 : 0.4}
                />
              </g>
            );
          })}
          
          {/* Additional web connections for related items */}
          {positions.map((pos1) => {
            return positions.filter(pos2 => 
              pos1.item.id !== pos2.item.id && 
              pos1.level === pos2.level && 
              Math.abs(pos1.x - pos2.x) < 150 && 
              Math.abs(pos1.y - pos2.y) < 150
            ).map((pos2) => {
              const distance = Math.sqrt((pos1.x - pos2.x) ** 2 + (pos1.y - pos2.y) ** 2);
              const isHighlighted = diagram.hoveredNode?.id === pos1.item.id || diagram.hoveredNode?.id === pos2.item.id;
              
              return (
                <line
                  key={`web-${pos1.item.id}-${pos2.item.id}`}
                  x1={pos1.x}
                  y1={pos1.y}
                  x2={pos2.x}
                  y2={pos2.y}
                  stroke={isHighlighted ? "#8b5cf6" : "#e2e8f0"}
                  strokeWidth={isHighlighted ? "2" : "1"}
                  strokeDasharray="2,4"
                  opacity={isHighlighted ? 0.8 : 0.2}
                  className="transition-all duration-200"
                />
              );
            });
          })}

          {/* Nœuds */}
          {positions.map((pos) => {
            const size = getNodeSize(pos.item.type);
            const isHovered = diagram.hoveredNode?.id === pos.item.id;
            const isSelected = diagram.selectedNode?.id === pos.item.id;
            const scale = isHovered ? 1.1 : isSelected ? 1.05 : 1;

            return (
              <g key={pos.item.id} data-item-id={pos.item.id}>
                {/* Forme du nœud */}
                {pos.item.type === 'US' || pos.item.type === 'UC' ? (
                  <circle
                    cx={pos.x}
                    cy={pos.y}
                    r={size.width / 2}
                    fill={`url(#gradient-${pos.item.type})`}
                    stroke={isSelected ? "#4f46e5" : "white"}
                    strokeWidth={isSelected ? "3" : "2"}
                    filter="url(#shadow)"
                    className="cursor-pointer transition-all duration-200"
                    transform={`scale(${scale})`}
                    style={{ transformOrigin: `${pos.x}px ${pos.y}px` }}
                    onClick={() => handleNodeClick(pos.item)}
                    onMouseEnter={() => handleNodeHover(pos.item)}
                    onMouseLeave={() => handleNodeHover(null)}
                  />
                ) : (
                  <rect
                    x={pos.x - size.width / 2}
                    y={pos.y - size.height / 2}
                    width={size.width}
                    height={size.height}
                    rx={pos.item.type === 'Epic' ? "12" : pos.item.type === 'Capability' ? "8" : "4"}
                    fill={`url(#gradient-${pos.item.type})`}
                    stroke={isSelected ? "#4f46e5" : "white"}
                    strokeWidth={isSelected ? "3" : "2"}
                    filter="url(#shadow)"
                    className="cursor-pointer transition-all duration-200"
                    transform={`scale(${scale})`}
                    style={{ transformOrigin: `${pos.x}px ${pos.y}px` }}
                    onClick={() => handleNodeClick(pos.item)}
                    onMouseEnter={() => handleNodeHover(pos.item)}
                    onMouseLeave={() => handleNodeHover(null)}
                  />
                )}

                {/* Badge IA */}
                {pos.item.generated_by_ai && (
                  <circle
                    cx={pos.x + size.width / 2 - 8}
                    cy={pos.y - size.height / 2 + 8}
                    r="6"
                    fill="#8b5cf6"
                    stroke="white"
                    strokeWidth="1"
                  />
                )}

                {/* Texte du titre */}
                <text
                  x={pos.x}
                  y={pos.y - 2}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill="white"
                  fontSize={pos.item.type === 'Epic' ? "10" : pos.item.type === 'US' || pos.item.type === 'UC' ? "8" : "9"}
                  fontWeight="bold"
                  className="pointer-events-none select-none"
                >
                  {pos.item.title.length > 12 ? pos.item.title.substring(0, 12) + '...' : pos.item.title}
                </text>

                {/* Type */}
                <text
                  x={pos.x}
                  y={pos.y + 10}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill="white"
                  fontSize="7"
                  opacity="0.8"
                  className="pointer-events-none select-none"
                >
                  {pos.item.type}
                </text>

                {/* Métriques */}
                {'wsjf' in pos.item && pos.item.wsjf && (
                  <text
                    x={pos.x}
                    y={pos.y + 20}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fill="white"
                    fontSize="6"
                    opacity="0.9"
                    className="pointer-events-none select-none"
                  >
                    WSJF: {pos.item.wsjf}
                  </text>
                )}
                
                {'story_points' in pos.item && pos.item.story_points && (
                  <text
                    x={pos.x}
                    y={pos.y + 20}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fill="white"
                    fontSize="6"
                    opacity="0.9"
                    className="pointer-events-none select-none"
                  >
                    {pos.item.story_points}pts
                  </text>
                )}
              </g>
            );
          })}
        </g>
      </svg>

      {/* Tooltip */}
      {diagram.hoveredNode && (
        <div className="absolute bottom-4 left-4 bg-white/95 p-3 rounded-lg shadow-lg border max-w-64 z-10">
          <div className="font-semibold text-sm">{diagram.hoveredNode.title}</div>
          <div className="text-xs text-gray-600 mt-1">{diagram.hoveredNode.type}</div>
          {diagram.hoveredNode.description && (
            <div className="text-xs text-gray-500 mt-2">{diagram.hoveredNode.description}</div>
          )}
          {diagram.hoveredNode.generated_by_ai && (
            <Badge className="bg-purple-600 text-white text-xs mt-2">
              <CpuIcon className="w-3 h-3 mr-1" />
              Généré par IA
            </Badge>
          )}
        </div>
      )}

      {/* Légende */}
      {/* Légende */}
      <div className="absolute bottom-4 right-4 bg-white/95 p-3 rounded-lg shadow-lg border z-10">
        <h4 className="text-xs font-semibold mb-2 text-gray-700">Légende</h4>
        <div className="grid grid-cols-1 gap-1 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-4 h-3 bg-purple-500 rounded"></div>
            <span>Epic</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-3 bg-purple-400 rounded"></div>
            <span>Capability</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-3 bg-blue-500 rounded"></div>
            <span>Feature</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-green-500 rounded-full"></div>
            <span>US</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
            <span>UC</span>
          </div>
          <div className="mt-2 pt-2 border-t border-gray-200">
            <div className="flex items-center gap-2 mb-1">
              <div className="w-4 h-0 border-t-2 border-gray-400"></div>
              <span>Hiérarchie</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-0 border-t border-gray-300 border-dashed"></div>
              <span>Relations</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}