# AGno Showcase - Complex UIs with CopilotKit

This showcase demonstrates how to build complex, interactive UIs using CopilotKit components connected to AGno agents via the AG-UI protocol.

## Features

This showcase includes 6 different demos that illustrate various UI patterns:

1. **Agentic Generative UI** - Agent breaks down tasks into steps with real-time progress tracking
2. **Shared State** - Todo list manager with bidirectional state synchronization
3. **Tool-based Generative UI** - Haiku generator with mood-based styling
4. **Agentic Chat** - Smart calculator with step-by-step explanations
5. **Human-in-the-Loop** - Weather assistant requiring user confirmation
6. **Predictive State Updates** - Smart form with AI-powered field predictions

## Architecture

- **Frontend**: Next.js app with CopilotKit components
- **Protocol**: AG-UI (Agent User Interaction Protocol) for standardized communication
- **Backend**: AGno agents providing AI capabilities
- **Connection**: HttpAgent from @ag-ui/client connecting to AGno's AG-UI app

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Python 3.8+
- OpenAI API key (for the AGno agents)

### Installation

1. **Install frontend dependencies:**
   ```bash
   npm install
   ```

2. **Install backend dependencies:**
   ```bash
   cd ../agno-showcase-backend
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   ```bash
   export OPENAI_API_KEY="your-api-key"
   ```

### Running the Application

1. **Start the backend server:**
   ```bash
   cd ../agno-showcase-backend
   python server.py
   ```
   The backend will run on http://localhost:7777

2. **Start the frontend:**
   ```bash
   npm run dev
   ```
   The frontend will run on http://localhost:3000

## How It Works

1. **CopilotKit Components**: The frontend uses `useCopilotAction` and `useCopilotReadable` hooks to define tools and share state with agents.

2. **AG-UI Protocol**: Communication happens through standardized events (text messages, tool calls, state updates) streamed over HTTP.

3. **AGno Agents**: Backend agents process requests and use the tools defined in the frontend to update the UI.

4. **HttpAgent**: The AG-UI client connects to the backend and handles the event stream.

## Key Concepts

### Frontend-Defined Tools

Tools are defined in the React components and passed to agents:

```typescript
useCopilotAction({
  name: "update_steps",
  description: "Update the list of steps",
  parameters: [...],
  handler: async ({ steps }) => {
    // Update UI state
  }
});
```

### Bidirectional State

State is shared between frontend and agent:

```typescript
useCopilotReadable({
  description: "Current todo list",
  value: todos
});
```

### Human-in-the-Loop

Some actions require user confirmation before execution, demonstrating collaborative workflows between AI and humans.

## Learn More

- [CopilotKit Documentation](https://docs.copilotkit.ai/)
- [AG-UI Protocol](https://docs.ag-ui.com/)
- [AGno Documentation](https://github.com/agno-ai/agno)

## License

MIT
