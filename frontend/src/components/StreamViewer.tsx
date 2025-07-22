"use client";
import {
  forwardRef,
  useImperativeHandle,
  useRef,
  useState,
  useEffect,
} from "react";
import { FileText, Terminal, Zap } from "lucide-react";

/* ------------------------------------------------------------------
   Types
-------------------------------------------------------------------*/
type Line = {
  node: string;
  raw: string;
  timestamp: Date;
};

type AgentStep = {
  name: string;
  status: 'pending' | 'active' | 'completed' | 'error';
  description?: string;
  icon: React.ElementType;
};

/* ------------------------------------------------------------------
   Composant principal
-------------------------------------------------------------------*/
const StreamViewer = forwardRef((_, ref) => {
  const [lines, setLines] = useState<Line[]>([]);
  const [steps, setSteps] = useState<AgentStep[]>([
    { name: 'plan', status: 'pending', description: 'Planification', icon: FileText },
    { name: 'execute', status: 'pending', description: 'Exécution', icon: Terminal },
    { name: 'write', status: 'pending', description: 'Rédaction', icon: Zap },
  ]);
  const [glowingStep, setGlowingStep] = useState<string | null>(null);
  const innerRef = useRef<HTMLPreElement>(null);

  useEffect(() => {
    if (glowingStep) {
      const timer = setTimeout(() => setGlowingStep(null), 1500);
      return () => clearTimeout(timer);
    }
  }, [glowingStep]);

  useImperativeHandle(ref, () => ({
    push(chunk: any) {
      console.log("StreamViewer received chunk:", chunk); // DEBUG
      const node = Object.keys(chunk).find(key => ['plan', 'execute', 'write'].includes(key)) ?? "unknown";

      setLines(ls => [
        ...ls,
        { node, raw: JSON.stringify(chunk, null, 2), timestamp: new Date() },
      ]);

      setGlowingStep(node);

      setSteps(prevSteps => {
        const newSteps = prevSteps.map(s => ({ ...s }));
        const currentStepIndex = newSteps.findIndex(s => s.name === node);
        if (currentStepIndex === -1) return prevSteps;

        return newSteps.map((step, index) => {
          if (index < currentStepIndex) return { ...step, status: 'completed' };
          if (index === currentStepIndex) {
            // Si c'est l'étape "write" avec du contenu, marquer comme complété
            if (node === 'write' && chunk[node]?.result) {
              return { ...step, status: 'completed' };
            }
            return { ...step, status: 'active' };
          }
          return { ...step, status: 'pending' };
        });
      });

      setTimeout(() => {
        const el = innerRef.current;
        if (el) el.scrollTop = 0;
      }, 0);
    },
    clear() {
      setLines([]);
      setSteps(prev => prev.map(s => ({ ...s, status: 'pending' })));
      setGlowingStep(null);
    }
  }));

  const renderContent = (raw: string) => {
    try {
      const data = JSON.parse(raw);
      const node = Object.keys(data).find(key => ['plan', 'execute', 'write'].includes(key)) ?? "unknown";
      const state = data[node];

      if (!state) {
        return <span className="text-gray-500">Génération du contenu...</span>;
      }

      switch (node) {
        case 'plan':
          return (
            <div className="space-y-2">
              <div className="text-blue-400 font-semibold text-sm">📋 Plan généré</div>
              <ul className="space-y-1 pl-4">
                {state.plan?.steps?.map((step: any, i: number) => (
                  <li key={i} className="text-gray-300 text-sm flex items-start">
                    <span className="text-blue-400 mr-2">•</span>
                    <span className="font-medium text-white mr-2">
                      {typeof step === 'string' ? `Étape ${i + 1}:` : `${step.title}:`}
                    </span>
                    <span>{typeof step === 'string' ? step : step.description}</span>
                  </li>
                ))}
              </ul>
            </div>
          );
        case 'execute':
          return (
            <div className="space-y-2">
              <div className="text-yellow-400 font-semibold text-sm">⚡ Exécution</div>
              <div className="bg-gray-900 p-3 rounded text-sm border-l-2 border-yellow-400">
                <pre className="text-gray-200 whitespace-pre-wrap font-mono text-xs leading-relaxed">
                  {state.command || state.exec_result?.stdout || JSON.stringify(state, null, 2)}
                </pre>
              </div>
              {state.stderr && (
                <div className="text-red-400 text-sm bg-red-900/20 p-2 rounded border-l-2 border-red-400">
                  <span className="font-medium">Erreur:</span> {state.stderr}
                </div>
              )}
            </div>
          );
        case 'write':
          return (
            <div className="space-y-2">
              <div className="text-green-400 font-semibold text-sm">✅ Résultat final</div>
              <div className="bg-green-900/20 p-3 rounded border-l-2 border-green-400">
                <div className="text-gray-200 text-sm whitespace-pre-wrap">
                  {state.result || JSON.stringify(state, null, 2)}
                </div>
              </div>
            </div>
          );
        default:
          return <span className="text-gray-400 text-sm">Traitement en cours...</span>;
      }
    } catch (e) {
      return <span className="text-red-500">Erreur de parsing du chunk.</span>;
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between bg-gray-800 p-3 rounded-lg">
        {steps.map((step) => {
          const Icon = step.icon;
          const isGlowing = glowingStep === step.name;
          const colors = {
            pending: "text-gray-500",
            active: "text-blue-400 animate-pulse",
            completed: "text-green-400",
            error: "text-red-400",
          };
          return (
            <div key={step.name} className={`flex items-center gap-2 p-2 rounded-md ${colors[step.status]} ${isGlowing ? 'animate-glow' : ''}`}>
              <Icon size={16} />
              <span className="text-sm font-medium">{step.description}</span>
            </div>
          );
        })}
      </div>

      <pre
        ref={innerRef}
        className="bg-black p-4 h-80 overflow-y-auto rounded-lg text-xs font-mono"
      >
        {[...lines].reverse().map(({ raw, timestamp }, i) => (
          <div key={lines.length - 1 - i} className="flex gap-3 items-start mb-2">
            <span className="text-gray-400 text-xs min-w-[60px]">{timestamp.toLocaleTimeString()}</span>
            <div className="flex-1">{renderContent(raw)}</div>
          </div>
        ))}
      </pre>
    </div>
  );
});

StreamViewer.displayName = "StreamViewer";
export default StreamViewer;
