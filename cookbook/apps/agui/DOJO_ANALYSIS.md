# Dojo Frontend Tool Calling Analysis

## Overview
This document analyzes the Dojo frontend's capability to handle advanced UI tool calling from backend AGno agents.

## Architecture Components

### 1. CopilotKit Integration
- **Version**: `0.0.0-mme-ag-ui-0-0-28-alpha-0-20250516114853` (alpha version)
- **Runtime**: Uses `ExperimentalEmptyAdapter` as the service adapter
- **Agent Communication**: Through `HttpAgent` from `@ag-ui/client`

### 2. Tool Registration System

#### Frontend Tool Definition (`useCopilotAction`)
```typescript
useCopilotAction({
  name: "update_steps",
  parameters: [...],
  handler: async ({ steps }) => {
    // Frontend handler logic
    return "Steps updated successfully";
  }
});
```

**Current Tools Registered**:
- `update_steps`: Updates all steps with their status
- `start_step`: Marks a step as active
- `complete_step`: Marks a step as completed

### 3. Event Processing Pipeline

1. **Backend → Frontend Flow**:
   ```
   AGno Agent → AG-UI Router → SSE Events → HttpAgent → CopilotKit Runtime → React Components
   ```

2. **Event Types Supported**:
   - `TOOL_CALL_START`
   - `TOOL_CALL_ARGS`
   - `TOOL_CALL_END`
   - `TEXT_MESSAGE_START/CONTENT/END`
   - `STATE_SNAPSHOT`
   - `RUN_STARTED/FINISHED`

### 4. Current Limitations

#### 1. **ExperimentalEmptyAdapter**
- The `ExperimentalEmptyAdapter` is a minimal implementation
- May not properly process tool call events from the backend
- Designed for simple message passing, not complex tool orchestration

#### 2. **Tool Registration Scope**
- All `useCopilotAction` hooks across different demos are registered globally
- No isolation between different agent demos
- Causes tool name conflicts and confusion

#### 3. **Event Processing**
- The frontend receives tool call events (confirmed: 33 events for 11 tool calls)
- But CopilotKit may not be routing them to the registered handlers
- Instead, the raw text response is displayed

#### 4. **State Management**
- Uses local React state (`useState`) for UI updates
- No persistent state management across sessions
- Relies on tool calls to update UI state

## Analysis Results

### ✅ What Works
1. **Backend Integration**: Successfully sends tool call events via SSE
2. **Event Deduplication**: Router properly deduplicates tool calls
3. **Tool Registration**: Frontend tools are properly defined with handlers
4. **UI Components**: Progress indicator UI is well-implemented

### ❌ What Doesn't Work
1. **Tool Execution**: Tool calls are not being executed by the frontend
2. **Event Routing**: CopilotKit is not routing tool events to handlers
3. **Tool Isolation**: Multiple demos interfere with each other
4. **Adapter Limitations**: `ExperimentalEmptyAdapter` may not support tool calls

## Recommendations

### 1. **Upgrade CopilotKit Integration**
- Use a proper service adapter instead of `ExperimentalEmptyAdapter`
- Consider implementing a custom adapter that properly handles AG-UI events

### 2. **Implement Tool Isolation**
- Scope tools to specific agent contexts
- Use agent-specific tool namespaces

### 3. **Add Debug Logging**
```typescript
// Add to the frontend
window.addEventListener('message', (event) => {
  if (event.data.type?.includes('TOOL_CALL')) {
    console.log('Tool call event received:', event.data);
  }
});
```

### 4. **Create Custom Event Handler**
```typescript
// Custom handler for AG-UI events
const handleAGUIEvent = (event: BaseEvent) => {
  switch (event.type) {
    case 'TOOL_CALL_START':
      // Route to appropriate handler
      break;
    case 'TOOL_CALL_ARGS':
      // Parse and execute tool
      break;
  }
};
```

### 5. **Test Tool Execution Path**
- Add console logs in tool handlers
- Verify events are reaching the frontend
- Check CopilotKit's internal event processing

## Conclusion

The Dojo frontend has the **foundation** to handle advanced UI tool calling:
- Proper tool registration system
- Well-designed UI components
- Correct event structure from backend

However, the **integration layer** (CopilotKit with `ExperimentalEmptyAdapter`) is not properly routing tool call events to the registered handlers. This causes the agent's tool calls to be displayed as text instead of being executed.

To fully support advanced UI tool calling, the frontend needs:
1. A proper CopilotKit adapter that handles AG-UI events
2. Tool isolation between different demos
3. Better event routing and debugging capabilities 