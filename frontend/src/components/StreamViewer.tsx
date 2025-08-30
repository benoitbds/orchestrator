"use client";
import {
  forwardRef,
  useImperativeHandle,
  useRef,
  useState,
  useEffect,
} from "react";
import AgentTimeline, { AgentTimelineStep } from "./AgentTimeline";
import { Badge } from "@/components/ui/badge";

/* ------------------------------------------------------------------
   Types
-------------------------------------------------------------------*/
type Line = {
  node: string;
  state: any;
  timestamp: Date;
};


/* ------------------------------------------------------------------
   Composant principal
-------------------------------------------------------------------*/
interface StreamViewerProps {
  timelineSteps: AgentTimelineStep[];
}

const StreamViewer = forwardRef<any, StreamViewerProps>(({ timelineSteps }, ref) => {
  const [lines, setLines] = useState<Line[]>([]);
  const innerRef = useRef<HTMLPreElement>(null);

  useImperativeHandle(ref, () => ({
    push({ node, state }: { node: string; state: any }) {
      console.log("StreamViewer received chunk:", { node, state }); // DEBUG

      setLines(ls => [...ls, { node, state, timestamp: new Date() }]);

      setTimeout(() => {
        const el = innerRef.current;
        if (el) el.scrollTop = 0;
      }, 0);
    },
    clear() {
      setLines([]);
    }
  }));

  const renderContent = (node: string, state: any) => {
    if (!state) {
      return <span className="text-gray-500">Génération du contenu...</span>;
    }

    // Extract plain text from HTML content for cleaner display
    const extractPlainText = (content: string): string => {
      if (!content) return '';
      
      // Remove HTML tags
      const withoutHTML = content.replace(/<[^>]*>/g, '');
      
      // Clean up extra whitespace and decode HTML entities
      const cleaned = withoutHTML
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&amp;/g, '&')
        .replace(/&quot;/g, '"')
        .replace(/&#x27;/g, "'")
        .replace(/\s+/g, ' ')
        .trim();
      
      return cleaned;
    };

    // Handle tool execution results with simplified display
    if (node === 'write' && state?.result) {
      const plainText = extractPlainText(state.result);
      
      return (
        <div className="space-y-2">
          <div className="text-green-400 font-semibold text-sm">✅ Agent Response</div>
          <div className="rounded border-l-2 border-green-400 bg-green-900/20 p-3">
            <div className="text-gray-200 text-sm whitespace-pre-wrap">
              {plainText || 'Operation completed'}
            </div>
          </div>
        </div>
      );
    }

    // Handle tool calls and other operations
    const displayContent = (() => {
      if (typeof state === 'string') {
        return extractPlainText(state);
      } else if (state && typeof state === 'object') {
        // For tool responses, show a simplified view
        if (state.ok !== undefined) {
          const status = state.ok ? '✅ Success' : '❌ Failed';
          const details = state.error || (state.result ? 'Operation completed' : '');
          return `${status}${details ? ': ' + details : ''}`;
        }
        return JSON.stringify(state, null, 2);
      }
      return String(state);
    })();

    return (
      <div className="space-y-2">
        <div className="text-blue-400 font-semibold text-sm">🔧 {node}</div>
        <div className="bg-gray-900 p-3 rounded text-sm border-l-2 border-blue-400">
          <pre className="text-gray-200 whitespace-pre-wrap font-mono text-xs leading-relaxed">
            {displayContent}
          </pre>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-4">
      <AgentTimeline steps={timelineSteps} />

      <pre
        ref={innerRef}
        className="bg-black p-4 h-80 overflow-y-auto rounded-lg text-xs font-mono"
      >
        {[...lines].reverse().map(({ node, state, timestamp }, i) => (
          <div key={lines.length - 1 - i} className="flex gap-3 items-start mb-2">
            <span className="text-gray-400 text-xs min-w-[60px]">{timestamp.toLocaleTimeString()}</span>
            <div className="flex-1">{renderContent(node, state)}</div>
          </div>
        ))}
      </pre>
    </div>
  );
});

StreamViewer.displayName = "StreamViewer";
export default StreamViewer;
