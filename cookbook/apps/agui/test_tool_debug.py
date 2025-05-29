#!/usr/bin/env python3
"""Debug test for tool calling issues in AG-UI integration."""

import json
import requests
import time
from typing import Dict, List, Any

def parse_sse_event(line: str) -> Dict[str, Any]:
    """Parse a single SSE event line."""
    if line.startswith("data: "):
        try:
            return json.loads(line[6:])
        except json.JSONDecodeError:
            return {}
    return {}

def test_tool_calls():
    """Test tool calls with detailed logging."""
    print("🔍 Tool Call Debug Test")
    print("=" * 60)
    
    # Test request
    request_data = {
        "message": "Help me make tea",
        "stream": True,
        "agent": "agentiveGenerativeUIAgent",
        "forwardedProps": {
            "agentId": "agentiveGenerativeUIAgent"
        }
    }
    
    print(f"📤 Request: {json.dumps(request_data, indent=2)}")
    print()
    
    # Make request
    response = requests.post(
        "http://localhost:7777/api/copilotkit/run",
        json=request_data,
        stream=True,
        headers={"Accept": "text/event-stream"}
    )
    
    print(f"📨 Response Status: {response.status_code}")
    print()
    
    # Track events
    events = []
    tool_calls = []
    messages = []
    
    # Process streaming response
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            event = parse_sse_event(line_str)
            
            if event:
                events.append(event)
                event_type = event.get("type", "")
                
                # Track tool calls
                if event_type == "toolCallStart":
                    tool_name = event.get("toolCallName", "unknown")
                    tool_id = event.get("toolCallId", "unknown")
                    tool_calls.append({
                        "name": tool_name,
                        "id": tool_id,
                        "args": None
                    })
                    print(f"🔧 Tool Start: {tool_name} (ID: {tool_id[:8]}...)")
                
                elif event_type == "toolCallArgs":
                    if tool_calls:
                        args_str = event.get("delta", "{}")
                        try:
                            args = json.loads(args_str)
                            tool_calls[-1]["args"] = args
                            print(f"   📝 Args: {args_str[:100]}...")
                        except:
                            print(f"   ⚠️  Invalid args: {args_str[:50]}...")
                
                # Track messages
                elif event_type == "textMessageContent":
                    content = event.get("delta", "")
                    messages.append(content)
                    if len(content) > 50:
                        print(f"💬 Message: {content[:50]}...")
                    else:
                        print(f"💬 Message: {content}")
    
    print()
    print("📊 Summary:")
    print(f"   Total events: {len(events)}")
    print(f"   Tool calls: {len(tool_calls)}")
    print(f"   Messages: {len(messages)}")
    print()
    
    # Analyze tool calls
    tool_counts = {}
    for tool in tool_calls:
        name = tool["name"]
        tool_counts[name] = tool_counts.get(name, 0) + 1
    
    print("📈 Tool Call Breakdown:")
    for name, count in tool_counts.items():
        print(f"   {name}: {count}")
    
    # Check for duplicate calls
    print()
    print("🔍 First 10 Tool Calls:")
    for i, tool in enumerate(tool_calls[:10]):
        args_str = json.dumps(tool["args"]) if tool["args"] else "None"
        print(f"   {i+1}. {tool['name']} - Args: {args_str[:80]}...")
    
    # Save full response for analysis
    with open("/tmp/agui_tool_debug.json", "w") as f:
        json.dump({
            "request": request_data,
            "events": events,
            "tool_calls": tool_calls,
            "messages": messages
        }, f, indent=2)
    
    print()
    print("💾 Full response saved to /tmp/agui_tool_debug.json")

if __name__ == "__main__":
    test_tool_calls() 