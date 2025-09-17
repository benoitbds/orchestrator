import { cn } from "@/lib/utils";
import { AGENT4BA_ASCII_ART } from "./ascii";

type AgentIdentityProps = {
  className?: string;
  size?: "desktop" | "mobile";
};

export function AgentIdentity({ className, size = "desktop" }: AgentIdentityProps) {
  const preTextSize =
    size === "mobile"
      ? "text-[7px] sm:text-[8px]"
      : "text-[9px] sm:text-[10px] md:text-xs";

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-2xl border border-lime-500/30 bg-slate-950 shadow-[0_0_25px_rgba(101,163,13,0.3)]",
        className,
      )}
    >
      <span className="sr-only">Agent4BA</span>
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(190,242,100,0.22),_transparent_65%)]"
      />
      <pre
        aria-hidden="true"
        className={cn(
          "relative z-10 whitespace-pre px-3 py-4 font-mono leading-tight tracking-tight text-lime-300 drop-shadow-[0_0_12px_rgba(190,242,100,0.35)] md:px-5",
          preTextSize,
        )}
      >
        {AGENT4BA_ASCII_ART}
      </pre>
      <div className="relative z-10 border-t border-lime-500/30 bg-slate-900/80 px-3 py-2 md:px-5">
        <p className="text-[11px] font-semibold uppercase tracking-[0.5em] text-lime-200/80">
          Autonomous backlog architect
        </p>
      </div>
    </div>
  );
}

