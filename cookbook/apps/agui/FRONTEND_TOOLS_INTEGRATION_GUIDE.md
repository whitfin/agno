# Frontend Tools Integration Guide for AG-UI Protocol in Dojo

This guide explains how to properly integrate frontend tools between AGno agents (backend) and Dojo (frontend) using the AG-UI protocol.

## Overview

The AG-UI protocol enables seamless communication between AI agents and frontend applications. For frontend tools to work properly in Dojo, we need to ensure:

1. **Backend agents emit proper tool call events via AG-UI protocol**
2. **Frontend receives and processes these events through CopilotKit**
3. **Tool messages are filtered to prevent infinite loops**
4. **Events are properly formatted and routed**

## Current Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   Dojo Frontend │ <-----> │ CopilotKit Route │ <-----> │  AGno Backend   │
│  (React + CK)   │   SSE   │  (Next.js API)   │  HTTP   │  (AG-UI Router) │
└─────────────────┘         └──────────────────┘         └─────────────────┘
        ↑                                                          ↑
        │                                                          │
        └── useCopilotAction ←── AG-UI Events ←── Tool Calls ────┘
```

## Key Components

### 1. Backend Agent Configuration

The agent must be configured with frontend tools that have proper entrypoints:

```python
from agno.agent import Agent
from agno.tools.function import Function
from agno.models.openai import OpenAIChat

# Define frontend tools with minimal entrypoints
update_steps_tool = Function(
    name="update_steps",
    description="Update the current state of task execution steps",
    parameters={...},
    entrypoint=lambda steps: "Steps updated successfully"
)

# Create agent with tools
agent = Agent(
    name="AgentWithFrontendTools",
    model=OpenAIChat(id="gpt-4o-mini"),
    tools=[update_steps_tool, start_step_tool, complete_step_tool],
    instructions="Clear instructions for tool usage...",
    markdown=True,
    stream=True
)
```

### 2. AG-UI Router Configuration

The AG-UI router automatically detects frontend tools and emits proper events:

```python
# In router.py, frontend tools are detected and events are emitted:
# - TOOL_CALL_START
# - TOOL_CALL_ARGS  
# - TOOL_CALL_END
```

### 3. Message Filtering (Critical!)

To prevent infinite loops where the agent repeatedly calls the same tools, implement message filtering:

```python
def filter_tool_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter out tool-related messages to prevent infinite loops."""
    filtered = []
    skip_next = False
    
    for i, msg in enumerate(messages):
        # Skip tool response messages
        if skip_next:
            skip_next = False
            continue
            
        # Skip assistant messages that only contain tool calls
        if msg.get("role") == "assistant":
            if "tool_calls" in msg and not msg.get("content"):
                if i + 1 < len(messages) and messages[i + 1].get("role") == "tool":
                    skip_next = True
                continue
                
        # Skip tool role messages
        if msg.get("role") == "tool":
            continue
            
        # Keep all other messages
        filtered.append(msg)
    
    return filtered
```

### 4. Frontend Integration

In the Dojo frontend, use `useCopilotAction` to handle tool calls:

```typescript
// In your React component
useCopilotAction({
  name: "update_steps",
  description: "Update the current state of task execution steps",
  parameters: [...],
  handler: async ({ steps }) => {
    // Update UI state
    setSteps(steps);
  },
});
```

## Common Issues and Solutions

### Issue 1: Tool Calls Not Reaching Frontend

**Symptoms**: Backend emits events but frontend handlers don't trigger

**Solution**: Ensure CopilotKit is configured with the correct runtime and adapter:
```typescript
<CopilotKit runtimeUrl="/api/copilotkit">
  <CopilotChat
    adapter={ExperimentalEmptyAdapter}
    // ... other props
  />
</CopilotKit>
```

### Issue 2: Infinite Tool Call Loops

**Symptoms**: Agent repeatedly calls the same tools with same arguments

**Solution**: Apply message filtering in the backend:
```python
# In multi_agent_demo.py
if agent_id == "agentiveGenerativeUIAgent" and "messages" in body:
    body["messages"] = filter_tool_messages(body.get("messages", []))
```

### Issue 3: Event Format Mismatch

**Symptoms**: Zod validation errors in frontend

**Solution**: Ensure events use UPPER_SNAKE_CASE format:
- ✅ `TOOL_CALL_START`
- ❌ `toolCallStart`

## Testing

Use the provided test scripts to verify the integration:

```bash
# Test backend events
python cookbook/apps/agui/test_simple_frontend_tools.py

# Expected output:
# - Tool calls: 5-10 (not hundreds!)
# - Events: TOOL_CALL_START, TOOL_CALL_ARGS, TOOL_CALL_END
# - Proper tool arguments
```

## Best Practices

1. **Clear Agent Instructions**: Provide explicit instructions to prevent excessive tool calls
2. **Tool Entrypoints**: Always provide entrypoints for frontend tools (even minimal ones)
3. **Message Filtering**: Always filter tool messages to prevent loops
4. **Event Logging**: Enable debug logging to troubleshoot issues
5. **Test Incrementally**: Test each component separately before full integration

## Debugging Checklist

- [ ] Backend agent has frontend tools with entrypoints
- [ ] AG-UI router is emitting tool events (check logs)
- [ ] Message filtering is applied to prevent loops
- [ ] Frontend has `useCopilotAction` handlers for each tool
- [ ] CopilotKit is configured with correct runtime URL
- [ ] Events are in UPPER_SNAKE_CASE format
- [ ] No excessive tool calls (should be < 20 for simple tasks)

## Next Steps

If frontend tools are still not working after following this guide:

1. Check browser console for errors
2. Verify SSE events in Network tab
3. Add debug logging to CopilotKit handlers
4. Test with a minimal example first
5. Check for version compatibility between AG-UI and CopilotKit 