# AG-UI Router for AGno

A production-ready FastAPI router that enables AGno agents and teams to work seamlessly with AG-UI (CopilotKit) frontends.

## Overview

The AG-UI router provides a standardized HTTP interface for AGno agents and teams, allowing them to be easily integrated with web applications built using the AG-UI protocol. It handles:

- **Streaming and non-streaming responses**
- **Tool call events with proper formatting**
- **Dynamic tool injection**
- **State management**
- **Legacy format compatibility**
- **Error handling and logging**

## Quick Start

```python
from agno.app.ag_ui.app import AGUIApp
from agno.agent import Agent

# Create your agent
agent = Agent(
    name="my_agent",
    instructions="You are a helpful assistant",
    model="gpt-4"
)

# Create the app
app = AGUIApp(agent=agent).get_app()

# Run with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7777)
```

## Features

### Single Endpoint Design

The router exposes a single `/run` endpoint that handles all agent interactions. This simplifies integration and reduces complexity.

### Request Formats

The `/run` endpoint accepts both JSON and multipart/form-data requests:

#### Standard JSON Format
```json
{
    "message": "Hello, how are you?",
    "stream": true,
    "session_id": "unique-session-id",
    "user_id": "user-123",
    "monitor": false
}
```

#### Legacy AG-UI Format
```json
{
    "messages": [
        {"role": "user", "content": "Hello, how are you?"}
    ],
    "threadId": "unique-thread-id"
}
```

### Response Format

The router returns AG-UI protocol events in either streaming (SSE) or non-streaming (JSON array) format:

#### Event Types
- `runStarted` - Indicates the start of agent processing
- `textMessageStart` - Marks the beginning of a text response
- `textMessageContent` - Contains text content chunks
- `textMessageEnd` - Marks the end of a text response
- `toolCallStart` - Indicates a tool is being called
- `toolCallArgs` - Contains tool call arguments
- `toolCallEnd` - Marks the end of a tool call
- `stateSnapshot` - Contains the current agent state
- `runFinished` - Indicates processing is complete
- `runError` - Contains error information

### Tool Call Support

The router automatically detects and formats tool calls from various AGno response formats:

```python
# AGno agents can return tool calls in multiple formats
# The router handles all of them transparently:

# Format 1: formatted_tool_calls (string format)
"calculate_sum(a=5, b=10)"

# Format 2: OpenAI-style tool calls
{
    "id": "call_123",
    "function": {
        "name": "calculate_sum",
        "arguments": "{\"a\": 5, \"b\": 10}"
    }
}

# Format 3: Direct tool format
{
    "tool_name": "calculate_sum",
    "tool_args": {"a": 5, "b": 10}
}
```

### Dynamic Tool Injection

Tools can be dynamically added to an agent at runtime:

```python
# Request with dynamic tools
{
    "message": "Use the weather tool",
    "tools": [
        {
            "name": "get_weather",
            "description": "Get current weather",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"}
                }
            }
        }
    ]
}
```

### State Management

The router supports agent state persistence across requests:

```python
# Send state with request
{
    "message": "Continue our conversation",
    "state": {"conversation_history": [...], "user_preferences": {...}}
}

# Receive state in response
# Look for the "stateSnapshot" event in the response
```

## Integration with Dojo

The router is designed to work seamlessly with Dojo frontends:

```typescript
// In your Dojo app
import { HttpAgent } from "@ag-ui/client";

const agent = new HttpAgent({
  url: "http://localhost:7777/api/copilotkit/run",
  agentId: "my_agent"
});
```

## Error Handling

The router includes comprehensive error handling:

- **Parse errors** (400): Invalid request format
- **Runtime errors** (500): Agent execution failures
- **Stream errors**: Handled gracefully with error events

All errors are logged with full context for debugging.

## Production Considerations

### Logging

The router uses AGno's logging system with debug level enabled by default. In production, you may want to adjust the log level:

```python
from agno.utils.log import set_log_level
set_log_level("INFO")
```

### Performance

- The router prefers async methods (`arun`) when available
- Streaming responses are memory-efficient for large outputs
- Tool list merging is optimized for minimal overhead

### Security

- The router validates all input data
- Dynamic tools are normalized and validated
- State updates are wrapped in try-catch blocks

## Advanced Usage

### Custom Router Configuration

```python
from agno.app.ag_ui.router import get_router
from fastapi import FastAPI

# Create custom FastAPI app
app = FastAPI(title="My AG-UI Service")

# Add the AG-UI router
router = get_router(agent=my_agent)
app.include_router(router, prefix="/api/copilotkit")

# Add your own endpoints
@app.get("/health")
def health_check():
    return {"status": "healthy"}
```

### Working with Teams

The router supports AGno teams just like agents:

```python
from agno.team import Team
from agno.app.ag_ui.app import AGUIApp

team = Team(
    name="my_team",
    agents=[agent1, agent2, agent3]
)

app = AGUIApp(team=team).get_app()
```

## Testing

Use the included test script to verify your setup:

```bash
python scripts/test_simplified_router.py
```

The test script covers:
- Streaming and non-streaming requests
- Legacy format compatibility
- Optional parameters
- Dynamic tool injection
- Error handling

## Troubleshooting

### Common Issues

1. **"No user message found in request"**
   - Ensure your request includes either a `message` field or a `messages` array with a user message

2. **Tool calls not appearing**
   - Check that your agent is configured with tools
   - Verify tool call format matches expected patterns

3. **State not persisting**
   - Ensure your agent has a `session_state` attribute
   - Check that state is JSON-serializable

### Debug Mode

Enable detailed logging for troubleshooting:

```python
from agno.utils.log import set_log_level_to_debug
set_log_level_to_debug()
```

## Contributing

When contributing to the router:

1. Maintain backward compatibility with legacy formats
2. Add tests for new event types or formats
3. Document any new features or parameters
4. Follow the existing error handling patterns
5. Ensure all tool call formats are supported

## License

This module is part of the AGno framework and follows the same license terms. 