# Frontend Tools Integration Guide for AG-UI Protocol

This guide explains how to properly integrate frontend tools between AGno agents (backend) and CopilotKit (frontend) using the AG-UI protocol.

## Overview

The AG-UI protocol enables seamless communication between AI agents and frontend applications. For frontend tools to work properly, we need to ensure:

1. **Backend agents emit proper tool call events**
2. **Frontend receives and processes these events**
3. **CopilotKit routes events to `useCopilotAction` handlers**

## Current Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   Dojo Frontend │ <-----> │ CopilotKit Route │ <-----> │  AGno Backend   │
│  (React + CK)   │         │  (Next.js API)   │         │  (AG-UI Router) │
└─────────────────┘         └──────────────────┘         └─────────────────┘
        │                            │                            │
        │                            │                            │
    useCopilotAction            HttpAgent                   Agent Tools
```

## Backend Configuration (AGno)

### 1. Define Frontend Tools in Agent

```python
from agno.agent import Agent
from agno.tools.function import Function
from agno.models.openai import OpenAIChat

# Define frontend-only tools with minimal entrypoints
update_steps_tool = Function(
    name="update_steps",
    description="Update the current state of task execution steps",
    parameters={
        "type": "object",
        "properties": {
            "steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "status": {"type": "string", "enum": ["pending", "completed"]}
                    },
                    "required": ["description", "status"]
                }
            }
        },
        "required": ["steps"]
    },
    entrypoint=lambda steps: "Steps updated successfully"
)

# Create agent with tools
agent = Agent(
    name="agentiveGenerativeUIAgent",
    model=OpenAIChat(id="gpt-4o-mini"),
    tools=[update_steps_tool, start_step_tool, complete_step_tool],
    instructions="Use the tools to update UI...",
    stream=True
)
```

### 2. Expose Agent via AG-UI Router

```python
from agno.app.ag_ui.app import AGUIApp

# Create AG-UI app
app = AGUIApp(agent=agent).get_app()

# The router automatically handles:
# - Tool call detection
# - Event streaming (TOOL_CALL_START, TOOL_CALL_ARGS, TOOL_CALL_END)
# - Proper AG-UI protocol formatting
```

## Frontend Configuration (CopilotKit)

### 1. API Route Setup

```typescript
// app/api/copilotkit/route.ts
import { HttpAgent } from "@ag-ui/client";
import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";

const BACKEND_URL = process.env.AGNO_BACKEND_URL || "http://localhost:7777/api/copilotkit/run";

// Create HttpAgent for each agent
const agentiveGenerativeUIAgent = new HttpAgent({ 
  url: BACKEND_URL, 
  agentId: "agentiveGenerativeUIAgent" 
});

const runtime = new CopilotRuntime({
  agents: {
    agentiveGenerativeUIAgent,
    // ... other agents
  },
});

export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter: new ExperimentalEmptyAdapter(),
    endpoint: "/api/copilotkit",
  });
  return handleRequest(req);
};
```

### 2. Frontend Component with Tool Handlers

```tsx
// components/AgenticGenerativeUI.tsx
import { CopilotKit, useCopilotAction } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";

const Chat = () => {
  const [currentSteps, setCurrentSteps] = useState({ steps: [] });

  // Define frontend action handler
  useCopilotAction({
    name: "update_steps",
    parameters: [
      {
        name: "steps",
        type: "object[]",
        description: "Array of steps with their current status",
      },
    ],
    handler: async ({ steps }) => {
      console.log("update_steps called with:", steps);
      setCurrentSteps({ steps });
      return "Steps updated successfully";
    },
  });

  return (
    <CopilotChat
      labels={{
        initial: "Hi! I can help you with tasks and show progress.",
      }}
    />
  );
};

export default function AgenticGenerativeUI() {
  return (
    <CopilotKit
      runtimeUrl="/api/copilotkit"
      agent="agentiveGenerativeUIAgent"
    >
      <Chat />
    </CopilotKit>
  );
}
```

## How It Works

1. **User sends message** → CopilotKit → API Route → Backend Agent
2. **Agent calls tool** → AG-UI Router emits events:
   - `TOOL_CALL_START` with tool name
   - `TOOL_CALL_ARGS` with arguments
   - `TOOL_CALL_END` to complete
3. **Events stream back** → HttpAgent → CopilotKit Runtime
4. **CopilotKit processes** → Routes to `useCopilotAction` handler
5. **Handler executes** → Updates UI state

## Debugging Tips

### 1. Verify Backend Events

```python
# Test script to check backend events
import httpx
import json

async def test_backend():
    response = await client.post(
        "http://localhost:7777/api/copilotkit/run",
        json={
            "message": "Help me plan a trip",
            "stream": True,
            "agent": "agentiveGenerativeUIAgent"
        }
    )
    
    async for line in response.aiter_lines():
        if line.startswith("data: "):
            event = json.loads(line[6:])
            if "TOOL_CALL" in event.get("type", ""):
                print(f"Tool event: {event}")
```

### 2. Check Frontend Console

```javascript
// Add logging to useCopilotAction handler
handler: async ({ steps }) => {
  console.log("🔧 Frontend tool called:", {
    toolName: "update_steps",
    args: steps,
    timestamp: new Date().toISOString()
  });
  // ... rest of handler
}
```

### 3. Enable CopilotKit Dev Console

```tsx
<CopilotKit
  runtimeUrl="/api/copilotkit"
  showDevConsole={true}  // Enable for debugging
  agent="agentiveGenerativeUIAgent"
>
```

## Common Issues and Solutions

### Issue 1: Tool calls not reaching frontend

**Symptom**: Backend emits tool events but `useCopilotAction` handler never fires

**Solution**: Ensure tool names match exactly between backend and frontend

### Issue 2: Tool execution errors

**Symptom**: "Tool not found" or similar errors

**Solution**: Backend tools need entrypoints even for frontend-only tools:
```python
entrypoint=lambda **kwargs: "Success"  # Minimal entrypoint
```

### Issue 3: State not updating

**Symptom**: Handler executes but UI doesn't update

**Solution**: Check React state updates and ensure proper re-rendering

## Best Practices

1. **Always define entrypoints** for tools in backend, even if frontend-only
2. **Use consistent tool names** between backend and frontend
3. **Add comprehensive logging** during development
4. **Test tool flow independently** before full integration
5. **Handle errors gracefully** in both backend and frontend

## Testing the Integration

Run the provided test script to verify the complete flow:

```bash
# Start backend
python cookbook/apps/agui/run_server.py

# Start frontend (in another terminal)
cd dojo && npm run dev

# Run integration test
python cookbook/apps/agui/frontend_tools_test.py
```

## Conclusion

The AG-UI protocol provides a robust bridge between AGno agents and CopilotKit frontends. By following this guide, you can ensure that frontend tools work seamlessly, enabling rich interactive experiences where AI agents can update the UI in real-time. 