export function connectWS(objective: string) {
  const ws = new WebSocket("ws://localhost:9080/stream");
  ws.addEventListener("open", () => {
    ws.send(JSON.stringify({ objective }));
  });
  return ws;
}
