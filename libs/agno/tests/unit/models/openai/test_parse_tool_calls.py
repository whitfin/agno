import json
from typing import Any, Dict, List

import pytest

from agno.models.openai import OpenAIChat


class MockToolCall:
    """Mock object to simulate ChoiceDeltaToolCall structure"""
    
    def __init__(self, index: int = 0, id: str = None, type: str = "function", name: str = None, arguments: str = None):
        self.index = index
        self.id = id
        self.type = type
        self.function = MockFunction(name, arguments)


class MockFunction:
    """Mock object to simulate function structure in ChoiceDeltaToolCall"""
    
    def __init__(self, name: str = None, arguments: str = None):
        self.name = name
        self.arguments = arguments


class TestOpenAIParseToolCalls:
    """Test suite for OpenAI parse_tool_calls method to ensure our concatenation fix works correctly"""

    def test_parse_single_complete_tool_call(self):
        """Test parsing a single complete tool call - should work normally"""
        tool_calls_data = [
            MockToolCall(
                index=0,
                id="call_123",
                type="function",
                name="test_function",
                arguments='{"param1": "value1", "param2": "value2"}'
            )
        ]
        
        result = OpenAIChat.parse_tool_calls(tool_calls_data)
        
        assert len(result) == 1
        assert result[0]["id"] == "call_123"
        assert result[0]["type"] == "function"
        assert result[0]["function"]["name"] == "test_function"
        assert result[0]["function"]["arguments"] == '{"param1": "value1", "param2": "value2"}'

    def test_parse_streaming_fragments_normal_concatenation(self):
        """Test that legitimate streaming fragments still get concatenated correctly"""
        # Simulate streaming chunks where arguments are built up in fragments
        tool_calls_data = [
            # First chunk with function name
            MockToolCall(index=0, id="call_123", name="test_function", arguments=""),
            # Second chunk with partial arguments
            MockToolCall(index=0, arguments='{"param1": "val'),
            # Third chunk completing arguments
            MockToolCall(index=0, arguments='ue1", "param2": "value2"}'),
        ]
        
        result = OpenAIChat.parse_tool_calls(tool_calls_data)
        
        assert len(result) == 1
        assert result[0]["id"] == "call_123"
        assert result[0]["function"]["name"] == "test_function"
        assert result[0]["function"]["arguments"] == '{"param1": "value1", "param2": "value2"}'

    def test_prevent_complete_json_concatenation(self):
        """Test our fix: prevent concatenation when both current and new arguments are complete JSON"""
        tool_calls_data = [
            # First complete tool call
            MockToolCall(
                index=0,
                id="call_123",
                name="test_function",
                arguments='{"param1": "value1", "param2": "value2"}'
            ),
            # Second complete tool call (this should NOT be concatenated)
            MockToolCall(
                index=0,
                arguments='{"param3": "value3", "param4": "value4"}'
            ),
        ]
        
        result = OpenAIChat.parse_tool_calls(tool_calls_data)
        
        assert len(result) == 1
        # Should have the first complete JSON, not concatenated
        assert result[0]["function"]["arguments"] == '{"param1": "value1", "param2": "value2"}'
        # Should NOT contain the concatenated malformed JSON
        assert '{"param1": "value1", "param2": "value2"}{"param3": "value3", "param4": "value4"}' not in result[0]["function"]["arguments"]

    def test_allow_fragment_to_complete_concatenation(self):
        """Test that fragments can still be added to complete JSON (edge case)"""
        tool_calls_data = [
            # First chunk with complete JSON
            MockToolCall(
                index=0,
                id="call_123",
                name="test_function", 
                arguments='{"param1": "value1"}'
            ),
            # Second chunk with invalid JSON fragment (should concatenate)
            MockToolCall(
                index=0,
                arguments=', "param2": "value2"}'
            ),
        ]
        
        result = OpenAIChat.parse_tool_calls(tool_calls_data)
        
        assert len(result) == 1
        # Should allow concatenation since second chunk is not valid JSON
        assert '{"param1": "value1"}, "param2": "value2"}' in result[0]["function"]["arguments"]

    def test_multiple_tool_calls_different_indices(self):
        """Test multiple tool calls with different indices work correctly"""
        tool_calls_data = [
            MockToolCall(
                index=0,
                id="call_123",
                name="function1",
                arguments='{"param1": "value1"}'
            ),
            MockToolCall(
                index=1,
                id="call_456", 
                name="function2",
                arguments='{"param2": "value2"}'
            ),
        ]
        
        result = OpenAIChat.parse_tool_calls(tool_calls_data)
        
        assert len(result) == 2
        assert result[0]["id"] == "call_123"
        assert result[0]["function"]["name"] == "function1"
        assert result[0]["function"]["arguments"] == '{"param1": "value1"}'
        assert result[1]["id"] == "call_456" 
        assert result[1]["function"]["name"] == "function2"
        assert result[1]["function"]["arguments"] == '{"param2": "value2"}'

    def test_empty_arguments_handling(self):
        """Test handling of empty or None arguments"""
        tool_calls_data = [
            MockToolCall(index=0, id="call_123", name="test_function", arguments=""),
            MockToolCall(index=0, arguments=None),
        ]
        
        result = OpenAIChat.parse_tool_calls(tool_calls_data)
        
        assert len(result) == 1
        assert result[0]["function"]["arguments"] == ""

    def test_malformed_json_does_not_prevent_concatenation(self):
        """Test that malformed JSON still allows concatenation (preserves original behavior)"""
        tool_calls_data = [
            MockToolCall(
                index=0,
                id="call_123",
                name="test_function",
                arguments='{"param1": "val'  # Incomplete JSON
            ),
            MockToolCall(
                index=0,
                arguments='ue1", "param2":'  # More incomplete JSON
            ),
            MockToolCall(
                index=0,
                arguments=' "value2"}'  # Completion
            ),
        ]
        
        result = OpenAIChat.parse_tool_calls(tool_calls_data)
        
        assert len(result) == 1
        assert result[0]["function"]["arguments"] == '{"param1": "value1", "param2": "value2"}'

    def test_edge_case_single_complete_json_with_duplicate_issue(self):
        """Test the exact scenario from the user's issue report"""
        # This simulates the user's reported issue
        tool_calls_data = [
            MockToolCall(
                index=0,
                id="call_123",
                name="test_function",
                arguments='{"param1": "val1", "param2": "value2", "param3": "value3"}'
            ),
            # This would have caused the duplication in the old code
            MockToolCall(
                index=0,
                arguments='{"param1": "val1", "param2": "value2", "param3": "value3"}'
            ),
        ]
        
        result = OpenAIChat.parse_tool_calls(tool_calls_data)
        
        assert len(result) == 1
        # Verify we don't get the malformed concatenated result
        expected_bad_result = '{"param1": "val1", "param2": "value2", "param3": "value3"}{"param1": "val1", "param2": "value2", "param3": "value3"}'
        assert result[0]["function"]["arguments"] != expected_bad_result
        # Verify we keep the original first complete JSON
        assert result[0]["function"]["arguments"] == '{"param1": "val1", "param2": "value2", "param3": "value3"}'
