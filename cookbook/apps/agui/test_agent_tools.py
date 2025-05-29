#!/usr/bin/env python3
"""Test to verify agent tools are properly configured."""

import sys
sys.path.append('.')

from cookbook.apps.agui.agentic_generative_ui_agent_fixed import agentive_generative_ui_agent_fixed

print("🔍 Agent Tools Test")
print("=" * 60)

# Check agent configuration
agent = agentive_generative_ui_agent_fixed
print(f"Agent name: {agent.name}")
print(f"Tool choice: {agent.tool_choice}")
print(f"Number of tools: {len(agent.tools) if agent.tools else 0}")

if agent.tools:
    print("\nTools configured:")
    for i, tool in enumerate(agent.tools):
        tool_name = getattr(tool, 'name', 'unknown')
        tool_desc = getattr(tool, 'description', 'no description')[:50]
        print(f"  {i+1}. {tool_name}: {tool_desc}...")

# Test tool determination
print("\nTesting tool determination for model...")
try:
    agent.determine_tools_for_model(agent.model, session_id="test-session")
    print(f"✅ Tool determination successful")
    print(f"Tools for model: {len(agent._tools_for_model) if agent._tools_for_model else 0}")
    
    if agent._tools_for_model:
        print("\nTools prepared for model:")
        for i, tool_dict in enumerate(agent._tools_for_model):
            if isinstance(tool_dict, dict) and "function" in tool_dict:
                func = tool_dict["function"]
                print(f"  {i+1}. {func.get('name', 'unknown')}")
except Exception as e:
    print(f"❌ Error in tool determination: {e}")

# Test a simple run without streaming
print("\n" + "=" * 60)
print("Testing agent run...")
try:
    response = agent.run(
        message="Help me make tea",
        stream=False,
        session_id="test-session"
    )
    
    print(f"Response content: {response.content[:100] if response.content else 'None'}...")
    print(f"Response tools: {len(response.tools) if response.tools else 0}")
    
    if response.tools:
        print("\nTool calls made:")
        for tool in response.tools:
            print(f"  - {tool.get('tool_name', 'unknown')}")
    
except Exception as e:
    print(f"❌ Error running agent: {e}")
    import traceback
    traceback.print_exc() 