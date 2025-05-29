"""Multi-agent demo server for AG-UI backend with proper agent ID routing.

Run with:
    uvicorn cookbook.apps.agui.multi_agent_demo:app --reload --port 7777

This server handles multiple agent IDs expected by the Dojo demos.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.app.ag_ui.app import AGUIApp

# Import our custom agents
from cookbook.apps.agui.haiku_agent import HaikuGeneratorAgent
from cookbook.apps.agui.shared_state_agent import SharedStateAgent
from cookbook.apps.agui.agentic_generative_ui_agent_fixed import agentive_generative_ui_agent_fixed
from cookbook.apps.agui.calculator_agent import CalculatorAgent
from cookbook.apps.agui.weather_agent import WeatherAgent

# ---------------------------------------------------------------------------
# Create different agents for different features
# ---------------------------------------------------------------------------

# For tool-based generative UI demo
tool_based_agent = HaikuGeneratorAgent

# For shared state demo
shared_state_agent = SharedStateAgent

# For agentic generative UI demo - use the fixed version
agentic_generative_ui_agent = agentive_generative_ui_agent_fixed

# For regular agentic chat demo - an agent that can handle frontend tools
agentic_chat_agent = Agent(
    name="AgenticChatAgent",
    description="A helpful chat agent that can interact with the UI",
    instructions="""You are a helpful assistant that can interact with the user interface.
    
When the user asks you to change colors or backgrounds, you can use the setBackgroundColor tool if it's available.
If no tools are available, just respond conversationally about what you would do.

Be friendly and helpful in your responses.""",
    model=OpenAIChat(id="gpt-4o"),
    markdown=True,
    stream=True,
)

# Human in the loop agent - placeholder for now
human_in_the_loop_agent = Agent(
    name="HumanInTheLoopAgent",
    description="An agent that requires human approval for certain actions",
    instructions="""You are an assistant that helps plan tasks but requires human approval before executing them.

When asked to perform a task:
1. Break it down into clear steps
2. Explain what you would do
3. Ask for approval before proceeding

Be clear about what actions you would take and why.""",
    model=OpenAIChat(id="gpt-4o"),
    markdown=True,
    stream=True,
)

# Predictive state updates agent - placeholder for now
predictive_state_agent = Agent(
    name="PredictiveStateAgent",
    description="An agent that provides real-time collaborative editing",
    instructions="""You are a collaborative editing assistant that helps with real-time document editing.

When given text to edit:
1. Suggest improvements
2. Show changes in real-time
3. Explain your reasoning

Be helpful and collaborative.""",
    model=OpenAIChat(id="gpt-4o"),
    markdown=True,
    stream=True,
)

# Map agent names to instances - include all properly defined agents
AGENT_MAP = {
    "agentiveGenerativeUIAgent": agentic_generative_ui_agent,  # Our step-based agent
    "sharedStateAgent": SharedStateAgent,
    "haikuGeneratorAgent": HaikuGeneratorAgent,
    "calculatorAgent": CalculatorAgent,
    "weatherAgent": WeatherAgent,
}

# ---------------------------------------------------------------------------
# Create FastAPI app with custom routing
# ---------------------------------------------------------------------------

app = FastAPI()

# Add CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create AG-UI apps for each agent - only for defined agents
agui_apps: Dict[str, AGUIApp] = {}
for agent_id, agent in AGENT_MAP.items():
    if agent is not None:  # Only create apps for properly defined agents
        agui_apps[agent_id] = AGUIApp(agent=agent)


def filter_tool_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter out tool-related messages to prevent infinite loops.
    
    This function removes:
    1. Assistant messages that only contain tool calls (no content)
    2. Tool role messages (tool responses)
    3. Any message pairs that represent a complete tool call/response cycle
    """
    if not messages:
        return messages
    
    filtered = []
    i = 0
    
    while i < len(messages):
        msg = messages[i]
        
        # Skip tool role messages entirely
        if msg.get("role") == "tool":
            logging.debug(f"Filtering out tool message at index {i}")
            i += 1
            continue
        
        # Check if this is an assistant message with only tool calls
        if msg.get("role") == "assistant":
            has_content = bool(msg.get("content"))
            has_tool_calls = bool(msg.get("tool_calls"))
            
            # If it only has tool calls and no content, check if next message is a tool response
            if has_tool_calls and not has_content:
                # Look ahead to see if the next message is a tool response
                if i + 1 < len(messages) and messages[i + 1].get("role") == "tool":
                    logging.debug(f"Filtering out tool call/response pair at indices {i} and {i+1}")
                    i += 2  # Skip both the tool call and tool response
                    continue
                else:
                    # Tool call without response - still filter it out to prevent re-execution
                    logging.debug(f"Filtering out standalone tool call at index {i}")
                    i += 1
                    continue
        
        # Keep all other messages (user messages, assistant messages with content)
        filtered.append(msg)
        i += 1
    
    logging.info(f"Filtered messages from {len(messages)} to {len(filtered)}")
    return filtered


# Add info endpoint to handle CopilotKit's info requests
@app.post("/api/copilotkit/run/info")
async def copilotkit_info(request: Request):
    """Handle CopilotKit info requests."""
    # Extract agent from URL path
    path = request.url.path
    agent_id = None
    
    # Try to extract agent ID from query params
    if request.url.query:
        import urllib.parse
        params = urllib.parse.parse_qs(request.url.query)
        if 'agent' in params:
            agent_id = params['agent'][0]
    
    logging.info(f"Info request for agent: {agent_id}")
    
    # Return basic info that CopilotKit expects
    return {
        "version": "1.0.0",
        "runtime": "agno",
        "features": {
            "streaming": True,
            "tools": True,
            "state": True
        }
    }


@app.post("/api/copilotkit/run")
async def run_with_agent_selection(request: Request):
    """Handle the /run endpoint with agent ID selection from the request."""
    
    # Parse the request to determine which agent to use
    body = await request.json()
    
    # Log the full body structure for debugging
    logging.debug(f"Full request body: {body}")
    
    # The frontend might send agent ID in different ways
    agent_id = None
    
    # Check for agent ID in the request
    if "agent" in body:
        agent_id = body["agent"]
    elif "agentId" in body:
        agent_id = body["agentId"]
    elif "forwardedProps" in body and isinstance(body["forwardedProps"], dict):
        agent_id = body["forwardedProps"].get("agent") or body["forwardedProps"].get("agentId")
    elif "data" in body and isinstance(body["data"], dict):
        # Check in data.agentSession.agentName (CopilotKit format)
        agent_session = body["data"].get("agentSession", {})
        if isinstance(agent_session, dict):
            agent_id = agent_session.get("agentName")
    
    # Also check URL query params
    if not agent_id and request.url.query:
        import urllib.parse
        params = urllib.parse.parse_qs(request.url.query)
        if 'agent' in params:
            agent_id = params['agent'][0]
    
    # Log the detected agent ID
    logging.info(f"Detected agent ID from request: {agent_id}")
    logging.debug(f"Request body keys: {list(body.keys())}")
    
    # Default to agentiveGenerativeUIAgent for the agentic generative UI demo
    if not agent_id:
        # Check if the request is for the agentic generative UI demo based on the path or other indicators
        # For now, default to agentiveGenerativeUIAgent since that's what we're testing
        agent_id = "agentiveGenerativeUIAgent"
        logging.info(f"No agent ID found, defaulting to: {agent_id}")
    
    # Get the appropriate AG-UI app
    if agent_id not in agui_apps:
        # Fallback to agentic generative UI agent
        logging.warning(f"Unknown agent ID: {agent_id}, falling back to agentiveGenerativeUIAgent")
        agent_id = "agentiveGenerativeUIAgent"
    
    logging.info(f"Using agent: {agent_id}")
    
    # Get the actual agent instance to verify
    actual_agent = AGENT_MAP.get(agent_id)
    if actual_agent:
        logging.info(f"Agent details - Name: {actual_agent.name}, Tools: {len(actual_agent.tools) if actual_agent.tools else 0}")
        if actual_agent.tools:
            tool_names = [getattr(tool, 'name', 'unknown') for tool in actual_agent.tools]
            logging.info(f"Agent tool names: {tool_names}")
    
    agui_app = agui_apps[agent_id]
    
    # Filter tool messages if this is the haiku agent to prevent loops
    if agent_id == "toolBasedGenerativeUIAgent" and "messages" in body:
        body["messages"] = filter_tool_messages(body.get("messages", []))
        logging.debug(f"Filtered messages to {len(body.get('messages', []))} messages")
    
    # Also filter tool messages for the agentiveGenerativeUIAgent to prevent loops
    if agent_id == "agentiveGenerativeUIAgent" and "messages" in body:
        body["messages"] = filter_tool_messages(body.get("messages", []))
        logging.debug(f"Filtered tool messages for agentiveGenerativeUIAgent to {len(body.get('messages', []))} messages")
    
    # Create a new request with the modified body
    from starlette.requests import Request as StarletteRequest
    from starlette.datastructures import Headers
    import json
    
    # Create new request with filtered body
    scope = request.scope.copy()
    receive = request.receive
    send = request._send
    
    async def new_receive():
        return {
            "type": "http.request",
            "body": json.dumps(body).encode()
        }
    
    new_request = StarletteRequest(scope, new_receive, send)
    
    # Get the router from the AG-UI app
    router = agui_app.get_router()
    
    # Find the /run endpoint handler
    for route in router.routes:
        if hasattr(route, 'path') and route.path == "/run" and hasattr(route, 'endpoint'):
            # Call the endpoint handler directly
            return await route.endpoint(new_request)
    
    # This shouldn't happen
    return {"error": "Run endpoint not found"}

@app.get("/api/copilotkit/status")
async def status():
    """Health check endpoint."""
    return {"status": "available", "agents": list(AGENT_MAP.keys())}

@app.get("/")
async def root():
    """Root endpoint with helpful info."""
    return {
        "service": "AG-UI Multi-Agent Demo",
        "endpoints": {
            "/api/copilotkit/run": "Main agent execution endpoint",
            "/api/copilotkit/status": "Health check and agent list",
        },
        "available_agents": list(AGENT_MAP.keys())
    } 