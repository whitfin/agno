import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { HttpAgent } from "@ag-ui/client";
import { NextRequest } from "next/server";

// Backend AGno endpoint
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:7777";

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

// Create AG-UI HttpAgents for each demo agent
const agents = {
  agentiveGenerativeUIAgent: new CustomHttpAgent({
    url: `${BACKEND_URL}/agentiveGenerativeUIAgent/api/copilotkit/run`,
    agentId: "agentiveGenerativeUIAgent",
  }),
  sharedStateAgent: new CustomHttpAgent({
    url: `${BACKEND_URL}/sharedStateAgent/api/copilotkit/run`,
    agentId: "sharedStateAgent",
  }),
  haikuGeneratorAgent: new CustomHttpAgent({
    url: `${BACKEND_URL}/haikuGeneratorAgent/api/copilotkit/run`,
    agentId: "haikuGeneratorAgent",
  }),
  calculatorAgent: new CustomHttpAgent({
    url: `${BACKEND_URL}/calculatorAgent/api/copilotkit/run`,
    agentId: "calculatorAgent",
  }),
  weatherAgent: new CustomHttpAgent({
    url: `${BACKEND_URL}/weatherAgent/api/copilotkit/run`,
    agentId: "weatherAgent",
  }),
  predictiveStateAgent: new CustomHttpAgent({
    url: `${BACKEND_URL}/predictiveStateAgent/api/copilotkit/run`,
    agentId: "predictiveStateAgent",
  }),
};

// Create runtime with all agents
const runtime = new CopilotRuntime({
  agents,
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