import { AGENT4BA_ASCII_ART } from "@/components/branding/ascii";

export default function Home() {
  return (
    <main className="relative flex min-h-dvh flex-col items-center justify-center overflow-hidden bg-slate-950 px-4 py-16">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(190,242,100,0.18),_transparent_65%)]"
      />
      <span className="sr-only">Agent4BA</span>
      <pre className="relative z-10 max-w-full whitespace-pre-wrap text-center font-mono text-[10px] leading-tight text-lime-300 drop-shadow-[0_0_12px_rgba(190,242,100,0.35)] sm:text-xs md:text-sm">
        {AGENT4BA_ASCII_ART}
      </pre>
    </main>
  );
}
