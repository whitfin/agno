import { HttpAgent } from "@ag-ui/client";

import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";

import { NextRequest } from "next/server";

// Backend AG-UI endpoint – override via env or use localhost default
const BACKEND_URL =
  process.env.AGNO_BACKEND_URL || "http://localhost:7777/api/copilotkit/run";

console.log(`[CopilotKit API] Using backend URL: ${BACKEND_URL}`);

// Custom HttpAgent that includes agentId in forwardedProps
class CustomHttpAgent extends HttpAgent {
  protected prepareRunAgentInput(parameters?: any) {
    const input = super.prepareRunAgentInput(parameters);
    // Include agentId in forwardedProps so backend can detect it
    return {
      ...input,
      forwardedProps: {
        ...input.forwardedProps,
        agentId: this.agentId,
      },
    };
  }
}

const makeAgent = (agentId: string) => {
  console.log(`[CopilotKit API] Creating HttpAgent for ${agentId}`);
  return new CustomHttpAgent({ url: BACKEND_URL, agentId });
};

// Provide separate instances for each agent ID expected by the frontend demos
const agenticChatAgent = makeAgent("agenticChatAgent");
const agentiveGenerativeUIAgent = makeAgent("agentiveGenerativeUIAgent");
const humanInTheLoopAgent = makeAgent("humanInTheLoopAgent");
const predictiveStateUpdatesAgent = makeAgent("predictiveStateUpdatesAgent");
const sharedStateAgent = makeAgent("sharedStateAgent");
const toolBasedGenerativeUIAgent = makeAgent("toolBasedGenerativeUIAgent");

const runtime = new CopilotRuntime({
  agents: {
    agenticChatAgent,
    agentiveGenerativeUIAgent,
    humanInTheLoopAgent,
    predictiveStateUpdatesAgent,
    sharedStateAgent,
    toolBasedGenerativeUIAgent,
  },
});

export const POST = async (req: NextRequest) => {
  console.log(`[CopilotKit API] Received POST request`);
  
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter: new ExperimentalEmptyAdapter(),
    endpoint: "/api/copilotkit",
  });

  return handleRequest(req);
};
