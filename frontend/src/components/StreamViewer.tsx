"use client";
import { forwardRef, useImperativeHandle, useState } from "react";

/** Affiche les chunks JSON reçus via WebSocket. */
const StreamViewer = forwardRef((_, ref) => {
  const [lines, setLines] = useState<string[]>([]);

  // expose une méthode push() pour lister les chunks
  useImperativeHandle(ref, () => ({
    push: (chunk: unknown) =>
      setLines((l) => [...l, JSON.stringify(chunk, null, 2)]),
  }));

  return (
    <pre className="bg-black text-green-400 p-4 h-80 overflow-y-auto rounded text-xs">
      {lines.map((l, i) => (
        <div key={i}>{l}</div>
      ))}
    </pre>
  );
});

StreamViewer.displayName = "StreamViewer";
export default StreamViewer;
