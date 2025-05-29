# AG-UI Integration with AGno

This directory contains the AG-UI (Agentic UI) integration for AGno agents, enabling them to work with CopilotKit frontends like Dojo.

## Overview

AG-UI provides a protocol for AI agents to communicate with frontend applications through:
- Streaming Server-Sent Events (SSE)
- Tool-based UI updates
- Bidirectional state synchronization
- Step-based execution with progress tracking

## Quick Start

### Running the Server

```bash
# Simple start
python cookbook/apps/agui/run_server.py

# With custom port
python cookbook/apps/agui/run_server.py --port 8000

# With auto-reload for development
python cookbook/apps/agui/run_server.py --reload
```

The server runs on `http://localhost:7777` by default and provides the `/api/copilotkit/run` endpoint.

### Connect from Frontend

```typescript
const agent = new CopilotAgent({
  name: "sharedStateAgent",  // or any other agent ID
  url: "http://localhost:7777/api/copilotkit"
});
```

## Available Agents

### 1. HaikuGeneratorAgent (`toolBasedGenerativeUIAgent`)
Generates haikus using tool-based UI rendering.

**Features:**
- Frontend-only tool execution
- Custom UI rendering for haikus
- Structured output format

### 2. SharedStateAgent (`sharedStateAgent`)
Recipe creator with bidirectional state synchronization.

**Features:**
- Real-time state updates
- Preserves user preferences
- Structured recipe format

### 3. AgenticGenerativeUIAgent (`agentiveGenerativeUIAgent`)
Step-based task execution with progress updates.

**Features:**
- Breaks tasks into steps
- Real-time progress tracking
- Step status updates

### 4. AgenticChatAgent (`agenticChatAgent`)
General conversational agent with UI interaction capabilities.

### 5. HumanInTheLoopAgent (`humanInTheLoopAgent`)
Task planning agent that requires human approval for actions.

### 6. PredictiveStateAgent (`predictiveStateUpdatesAgent`)
Collaborative editing agent with real-time updates.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Dojo UI       │────▶│  AG-UI Router    │────▶│  AGno Agents    │
│  (CopilotKit)   │◀────│  (Translation)   │◀────│                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## Event Types

The integration supports these event types:
- `TEXT_MESSAGE_START/CONTENT/END` - Streaming text responses
- `TOOL_CALL_START/ARGS/END` - Tool invocations
- `STATE_SNAPSHOT` - State synchronization
- `STEP_STARTED/FINISHED` - Step execution tracking

## File Structure

```
cookbook/apps/agui/
├── __init__.py                      # Package initialization
├── haiku_agent.py                   # Haiku generator agent
├── shared_state_agent.py            # Recipe creator with state sync
├── agentic_generative_ui_agent.py   # Step-based execution agent
├── multi_agent_demo.py              # Main demo server
├── run_server.py                    # Server startup script
├── README.md                        # This file
└── INTEGRATION_PLAN.md             # Detailed integration plan
```

## Development

### Adding a New Agent

1. Create your agent class inheriting from `Agent`
2. Add it to `AGENT_MAP` in `multi_agent_demo.py`
3. The agent will be automatically available at the `/api/copilotkit/run` endpoint

### Custom Event Types

Agents can emit custom events through the `tools` field:

```python
response.tools = [{
    "type": "custom_event",
    "data": {...}
}]
```

## Testing

Test the server endpoints:

```bash
# Check status
curl http://localhost:7777/api/copilotkit/status

# Test streaming
curl -X POST http://localhost:7777/api/copilotkit/run \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "agentId": "sharedStateAgent", "stream": true}'
```

## Troubleshooting

### Agent not responding
- Check that the agent ID matches one in `AGENT_MAP`
- Verify the server is running on the correct port
- Check server logs for errors

### State not updating
- Ensure state events are being emitted with type `state_update`
- Verify the frontend is handling state events

### Tool calls not working
- For frontend tools, ensure no `entrypoint` is defined
- Check that tool names match between agent and frontend