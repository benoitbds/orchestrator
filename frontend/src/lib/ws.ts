export function connectWS(objective: string, projectId?: number) {
  const wsUrl = (process.env.NEXT_PUBLIC_API_URL || "ws://localhost:8000").replace(
    /^http/,
    "ws"
  );
  const ws = new WebSocket(`${wsUrl}/stream`);
  ws.addEventListener("open", () => {
    ws.send(JSON.stringify({ objective, project_id: projectId }));
  });
  return ws;
}
