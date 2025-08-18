import RunTimeline from "@/components/RunTimeline";

async function getRun(id: string) {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  const res = await fetch(`${apiUrl}/runs/${id}`, { cache: "no-store" });
  if (!res.ok) throw new Error("run not found");
  return res.json();
}

export default async function RunDetail({ params }: { params: { runId: string } }) {
  const run = await getRun(params.runId);
  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-semibold">Run {params.runId}</h1>
      <RunTimeline run={run} />
      <pre className="bg-gray-100 p-4 rounded text-sm overflow-auto">
        {JSON.stringify(run, null, 2)}
      </pre>
    </div>
  );
}
