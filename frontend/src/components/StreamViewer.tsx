"use client";
import {
  forwardRef,
  useImperativeHandle,
  useRef,
  useState,
} from "react";

/* ------------------------------------------------------------------
   Types
-------------------------------------------------------------------*/
type Line = {
  node: string;   // plan | execute | write | …
  raw: string;    // JSON stringify
};

/* ------------------------------------------------------------------
   Composant principal
-------------------------------------------------------------------*/
const StreamViewer = forwardRef((_, ref) => {
  const [lines, setLines] = useState<Line[]>([]);
  const innerRef = useRef<HTMLPreElement>(null);

  /* Palette simple : couleur selon le node -----------------------*/
  const color = (node: string) => {
    switch (node) {
      case "plan":
        return "text-green-400";
      case "execute":
        return "text-yellow-300";
      case "write":
        return "text-cyan-300";
      default:
        return "text-white";
    }
  };

  /* Méthode push exposée au parent ------------------------------*/
  useImperativeHandle(ref, () => ({
    push(chunk: any) {
      setLines((ls) => [
        ...ls,
        {
          node: chunk.node ?? "unknown",
          raw: JSON.stringify(chunk, null, 2),
        },
      ]);

      // auto-scroll tout en bas après rendu
      setTimeout(() => {
        const el = innerRef.current;
        if (el) el.scrollTop = el.scrollHeight;
      }, 0);
    },
  }));

  /* Rendu --------------------------------------------------------*/
  return (
    <pre
      ref={innerRef}
      className="bg-black p-4 h-80 overflow-y-auto rounded text-xs"
    >
      {lines.map(({ node, raw }, i) => (
        <div key={i} className={color(node)}>
          {raw}
        </div>
      ))}
    </pre>
  );
});

StreamViewer.displayName = "StreamViewer";
export default StreamViewer;
