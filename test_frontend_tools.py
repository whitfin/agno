#!/usr/bin/env python3
"""Test script to debug frontend tool calls in AGno with AG-UI protocol."""

import asyncio
import json
import httpx
from typing import List, Dict, Any

# ANSI color codes for better readability
RESET = "\033[0m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"

async def test_frontend_tools():
    """Test the agent with frontend tools."""
    
    # The AG-UI protocol expects these tools to be passed from the frontend
    frontend_tools = [
        {
            "name": "update_steps",
            "description": "Update the list of steps for the current task",
            "parameters": {
                "type": "object",
                "properties": {
                    "steps": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "description": {"type": "string"},
                                "status": {"type": "string", "enum": ["pending", "completed"]}
                            }
                        }
                    }
                },
                "required": ["steps"]
            }
        },
        {
            "name": "start_step",
            "description": "Mark a step as in progress",
            "parameters": {
                "type": "object",
                "properties": {
                    "step_name": {"type": "string"}
                },
                "required": ["step_name"]
            }
        },
        {
            "name": "complete_step",
            "description": "Mark a step as completed",
            "parameters": {
                "type": "object",
                "properties": {
                    "step_name": {"type": "string"}
                },
                "required": ["step_name"]
            }
        }
    ]
    
    # Request body following AG-UI protocol
    request_body = {
        "message": "Help me plan a trip to Paris. Break it down into steps and show me progress.",
        "stream": True,
        "session_id": "test-session",
        "tools": frontend_tools,  # Pass frontend tools
        "state": {}
    }
    
    print(f"{CYAN}=== Testing Frontend Tools with AG-UI Protocol ==={RESET}")
    print(f"{YELLOW}Endpoint:{RESET} http://localhost:7777/agentiveGenerativeUIAgent/api/copilotkit/run")
    print(f"{YELLOW}Request:{RESET}")
    print(json.dumps(request_body, indent=2))
    print()
    
    # Make the request
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Use SSE for streaming response
            async with client.stream(
                "POST",
                "http://localhost:7777/agentiveGenerativeUIAgent/api/copilotkit/run",
                json=request_body,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream"
                }
            ) as response:
                print(f"{GREEN}Connected! Status: {response.status_code}{RESET}")
                print(f"{CYAN}=== Streaming Events ==={RESET}")
                
                # Track tool calls
                tool_calls_detected = []
                
                # Process SSE stream
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix
                        if data_str.strip():
                            try:
                                event = json.loads(data_str)
                                event_type = event.get("type", "UNKNOWN")
                                
                                # Color code different event types
                                if event_type == "RUN_STARTED":
                                    print(f"{GREEN}[{event_type}]{RESET} Run started")
                                elif event_type == "TEXT_MESSAGE_START":
                                    print(f"{BLUE}[{event_type}]{RESET} Message started")
                                elif event_type == "TEXT_MESSAGE_CONTENT":
                                    content = event.get("delta", "")
                                    print(f"{BLUE}[{event_type}]{RESET} {content}", end="", flush=True)
                                elif event_type == "TEXT_MESSAGE_END":
                                    print(f"\n{BLUE}[{event_type}]{RESET} Message ended")
                                elif event_type == "TOOL_CALL_START":
                                    tool_name = event.get("tool_call_name", "unknown")
                                    tool_id = event.get("tool_call_id", "unknown")
                                    print(f"\n{MAGENTA}[{event_type}]{RESET} Tool: {tool_name} (ID: {tool_id})")
                                    tool_calls_detected.append({
                                        "name": tool_name,
                                        "id": tool_id,
                                        "args": ""
                                    })
                                elif event_type == "TOOL_CALL_ARGS":
                                    args = event.get("delta", "")
                                    print(f"{MAGENTA}[{event_type}]{RESET} Args: {args}")
                                    if tool_calls_detected:
                                        tool_calls_detected[-1]["args"] += args
                                elif event_type == "TOOL_CALL_END":
                                    print(f"{MAGENTA}[{event_type}]{RESET} Tool call completed")
                                elif event_type == "STATE_SNAPSHOT":
                                    state = event.get("snapshot", {})
                                    print(f"{YELLOW}[{event_type}]{RESET} State: {json.dumps(state, indent=2)}")
                                elif event_type == "RUN_FINISHED":
                                    print(f"{GREEN}[{event_type}]{RESET} Run completed")
                                elif event_type == "RUN_ERROR":
                                    error = event.get("message", "Unknown error")
                                    print(f"{RED}[{event_type}]{RESET} Error: {error}")
                                else:
                                    print(f"{CYAN}[{event_type}]{RESET} {json.dumps(event, indent=2)}")
                                    
                            except json.JSONDecodeError:
                                print(f"{RED}[ERROR]{RESET} Failed to parse: {data_str}")
                
                print(f"\n{CYAN}=== Summary ==={RESET}")
                print(f"Total tool calls detected: {len(tool_calls_detected)}")
                for i, tool_call in enumerate(tool_calls_detected, 1):
                    print(f"\n{YELLOW}Tool Call #{i}:{RESET}")
                    print(f"  Name: {tool_call['name']}")
                    print(f"  ID: {tool_call['id']}")
                    try:
                        args_json = json.loads(tool_call['args'])
                        print(f"  Args: {json.dumps(args_json, indent=4)}")
                    except:
                        print(f"  Args (raw): {tool_call['args']}")
                        
        except Exception as e:
            print(f"{RED}Error: {e}{RESET}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_frontend_tools()) 