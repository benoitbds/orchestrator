import Link from "next/link";

import { AGENT4BA_ASCII_ART } from "@/components/branding/ascii";

const FEATURES = [
  {
    title: "Autonomous prioritisation",
    description:
      "Feed objectives in plain language and let Agent4BA turn them into ranked backlog items with rationale you can audit.",
  },
  {
    title: "Human-in-the-loop planning",
    description:
      "Collaborate with the agent in real time, approve key decisions, and iterate on plans before they reach delivery.",
  },
  {
    title: "Traceable execution",
    description:
      "Review every action, prompt, and outcome so compliance teams and stakeholders understand how work moves forward.",
  },
] as const;

function HomeHero() {
  return (
    <section className="flex flex-col items-center gap-10 text-center">
      <div className="relative w-full max-w-4xl overflow-hidden rounded-3xl border border-lime-500/30 bg-slate-950/90 p-6 shadow-[0_35px_120px_rgba(15,23,42,0.65)] backdrop-blur-xl">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(190,242,100,0.24),_transparent_70%)]"
        />
        <span className="sr-only">Agent4BA</span>
        <pre
          aria-hidden
          className="relative z-10 mx-auto max-w-full overflow-x-auto whitespace-pre leading-tight text-[11px] font-medium text-lime-300 drop-shadow-[0_0_15px_rgba(190,242,100,0.35)] sm:text-xs md:text-sm"
        >
          {AGENT4BA_ASCII_ART}
        </pre>
      </div>
      <div className="space-y-5">
        <p className="text-balance text-lg text-slate-200 sm:text-xl md:text-2xl">
          Pimped workspace orchestration for business analysts who want AI copilots without losing control.
        </p>
        <div className="flex flex-col items-center gap-3 sm:flex-row">
          <Link
            href="/login"
            className="inline-flex items-center justify-center rounded-full border border-transparent bg-lime-300 px-6 py-3 text-sm font-semibold text-slate-950 shadow-[0_12px_40px_rgba(190,242,100,0.35)] transition hover:-translate-y-0.5 hover:bg-lime-200 hover:shadow-[0_18px_55px_rgba(190,242,100,0.4)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lime-200"
          >
            Enter workspace
          </Link>
          <Link
            href="#features"
            className="inline-flex items-center justify-center rounded-full border border-lime-500/40 bg-slate-900/70 px-6 py-3 text-sm font-semibold text-lime-200 transition hover:bg-slate-900/90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lime-200"
          >
            Explore capabilities
          </Link>
        </div>
      </div>
    </section>
  );
}

function FeatureHighlights() {
  return (
    <section
      id="features"
      className="grid w-full max-w-5xl gap-6 rounded-3xl border border-lime-500/20 bg-slate-950/70 p-8 text-left shadow-[0_25px_80px_rgba(15,23,42,0.55)] backdrop-blur-xl md:grid-cols-3"
    >
      {FEATURES.map((feature) => (
        <article key={feature.title} className="space-y-3">
          <h2 className="text-lg font-semibold text-lime-200">{feature.title}</h2>
          <p className="text-sm text-slate-300">{feature.description}</p>
        </article>
      ))}
    </section>
  );
}


export default function Home() {
  return (
    <main className="relative flex min-h-dvh flex-col items-center justify-center overflow-hidden bg-slate-950 px-4 py-16 text-slate-100">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.15),_transparent_65%)]"
      />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(140deg,_rgba(190,242,100,0.18),_transparent_60%),linear-gradient(220deg,_rgba(14,116,144,0.22),_transparent_65%)]" aria-hidden />
      <div className="relative z-10 flex w-full flex-col items-center gap-16">
        <HomeHero />
        <FeatureHighlights />
      </div>
    </main>
  );
}
