#!/usr/bin/env python3
"""Minimal test to debug tool calling issues."""

import asyncio
import json
import httpx

async def test_minimal():
    """Test with minimal request to see tool behavior."""
    
    print("🧪 Minimal Tool Test")
    print("=" * 60)
    
    # Very simple request
    request = {
        "message": "Help me make tea",
        "stream": True,
        "agent": "agentiveGenerativeUIAgent",
        "forwardedProps": {
            "agentId": "agentiveGenerativeUIAgent"
        }
    }
    
    print(f"📤 Request: {json.dumps(request, indent=2)}")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:7777/api/copilotkit/run",
            json=request,
            timeout=30.0
        )
        
        print(f"\n📨 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            # Count tool calls
            tool_calls = []
            lines = response.text.split('\n')
            
            for line in lines:
                if line.startswith('data: '):
                    try:
                        event = json.loads(line[6:])
                        if event.get('type') == 'TOOL_CALL_START':
                            tool_calls.append({
                                'name': event.get('toolCallName'),
                                'id': event.get('toolCallId')
                            })
                    except:
                        pass
            
            print(f"\n📊 Tool Calls: {len(tool_calls)}")
            
            # Count by name
            tool_counts = {}
            for tc in tool_calls:
                name = tc.get('name', 'unknown')
                tool_counts[name] = tool_counts.get(name, 0) + 1
            
            print("\n📈 Tool Call Counts:")
            for name, count in tool_counts.items():
                print(f"   {name}: {count}")
            
            # Show unique tool call IDs
            unique_ids = set(tc.get('id') for tc in tool_calls)
            print(f"\n🔑 Unique Tool Call IDs: {len(unique_ids)}")
            
            # Check if IDs are being reused
            if len(unique_ids) < len(tool_calls):
                print("⚠️  WARNING: Tool call IDs are being reused!")
                
                # Find duplicates
                id_counts = {}
                for tc in tool_calls:
                    id = tc.get('id')
                    id_counts[id] = id_counts.get(id, 0) + 1
                
                duplicates = {id: count for id, count in id_counts.items() if count > 1}
                print(f"🔁 Duplicate IDs: {duplicates}")

if __name__ == "__main__":
    asyncio.run(test_minimal()) 