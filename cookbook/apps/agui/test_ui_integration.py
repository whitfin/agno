#!/usr/bin/env python3
"""Test script to debug UI integration issues with frontend tools."""

import asyncio
import json
import httpx
from typing import List, Dict, Any

async def test_ui_integration():
    """Test the complete UI integration flow."""
    
    print("🧪 Testing AG-UI Frontend Tools Integration")
    print("=" * 80)
    
    # Test 1: Direct backend test
    print("\n📋 Test 1: Backend AG-UI Protocol Test")
    print("-" * 40)
    
    request = {
        "message": "Help me plan a trip to Paris. Break it down into steps.",
        "stream": True,
        "agent": "agentiveGenerativeUIAgent",
        "forwardedProps": {
            "agentId": "agentiveGenerativeUIAgent"
        }
    }
    
    print(f"📤 Request: {json.dumps(request, indent=2)}")
    
    async with httpx.AsyncClient() as client:
        # Test backend directly
        response = await client.post(
            "http://localhost:7777/api/copilotkit/run",
            json=request,
            timeout=30.0
        )
        
        print(f"\n📨 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print("\n🔍 Event Stream Analysis:")
            print("-" * 40)
            
            events = []
            tool_calls = []
            
            # Parse SSE events
            for line in response.text.split('\n'):
                if line.startswith('data: '):
                    try:
                        event_data = json.loads(line[6:])
                        events.append(event_data)
                        
                        # Track tool calls
                        if event_data.get('type') == 'TOOL_CALL_START':
                            tool_calls.append({
                                'name': event_data.get('toolCallName'),
                                'type': 'start',
                                'id': event_data.get('toolCallId')
                            })
                        elif event_data.get('type') == 'TOOL_CALL_ARGS':
                            # Find the corresponding tool call
                            for tc in tool_calls:
                                if tc.get('id') == event_data.get('toolCallId'):
                                    tc['args'] = event_data.get('arguments')
                        elif event_data.get('type') == 'TOOL_CALL_END':
                            # Mark as complete
                            for tc in tool_calls:
                                if tc.get('id') == event_data.get('toolCallId'):
                                    tc['complete'] = True
                    except:
                        pass
            
            # Analyze results
            print(f"Total events: {len(events)}")
            print(f"Tool calls: {len(tool_calls)}")
            
            # Show tool call details
            print("\n📊 Tool Calls Analysis:")
            for i, tc in enumerate(tool_calls, 1):
                print(f"\n{i}. {tc.get('name')} (ID: {tc.get('id', 'unknown')[:8]}...)")
                if 'args' in tc:
                    print(f"   Args: {json.dumps(tc['args'], indent=11)[:200]}...")
                print(f"   Complete: {tc.get('complete', False)}")
            
            # Check for issues
            print("\n🔍 Issue Detection:")
            
            # Check for duplicate tool calls
            tool_names = [tc.get('name') for tc in tool_calls]
            duplicates = {name: tool_names.count(name) for name in set(tool_names) if tool_names.count(name) > 1}
            
            if duplicates:
                print(f"⚠️  Duplicate tool calls detected: {duplicates}")
            else:
                print("✅ No duplicate tool calls")
            
            # Check for proper event sequence
            event_types = [e.get('type') for e in events if e.get('type')]
            has_run_started = 'RUN_STARTED' in event_types
            has_run_finished = 'RUN_FINISHED' in event_types
            
            print(f"✅ RUN_STARTED: {has_run_started}")
            print(f"✅ RUN_FINISHED: {has_run_finished}")
            
            # Check for frontend tool events
            frontend_tools = ['update_steps', 'start_step', 'complete_step']
            frontend_tool_calls = [tc for tc in tool_calls if tc.get('name') in frontend_tools]
            
            print(f"\n📱 Frontend Tool Calls: {len(frontend_tool_calls)}")
            for tc in frontend_tool_calls:
                print(f"   - {tc.get('name')}")
        else:
            print(f"❌ Error: {response.text}")
    
    # Test 2: Check event format
    print("\n\n📋 Test 2: Event Format Verification")
    print("-" * 40)
    
    # Create a minimal request to check event format
    minimal_request = {
        "message": "Hi",
        "stream": True,
        "agent": "agentiveGenerativeUIAgent",
        "forwardedProps": {
            "agentId": "agentiveGenerativeUIAgent"
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:7777/api/copilotkit/run",
            json=minimal_request,
            timeout=10.0
        )
        
        if response.status_code == 200:
            # Check first few events
            lines = response.text.split('\n')[:10]
            print("First few events:")
            for line in lines:
                if line.startswith('data: '):
                    try:
                        event = json.loads(line[6:])
                        print(f"  Type: {event.get('type')}, Keys: {list(event.keys())}")
                    except:
                        pass

if __name__ == "__main__":
    print("🚀 Starting AG-UI Frontend Tools Integration Test")
    print("Make sure the backend server is running on http://localhost:7777")
    print()
    
    asyncio.run(test_ui_integration()) 