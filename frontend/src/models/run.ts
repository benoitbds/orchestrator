export type Step = {
  order?: number;
  node: string;
  timestamp?: string;
  content?: any;
};

export function normalizeStep(msg: any): Step {
  const step: Step = {
    order: msg?.order,
    node: msg?.node || "unknown",
    timestamp: msg?.timestamp,
    content: msg?.payload ?? msg?.content,
  };
  if (typeof step.content === "string") {
    try {
      step.content = JSON.parse(step.content);
    } catch {
      // keep original string if JSON.parse fails
    }
  }
  return step;
}
