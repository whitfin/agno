import json
from typing import Any, Dict, List

import pytest

from agno.models.ibm import WatsonX


class TestWatsonXParseToolCalls:
    """Test suite for IBM WatsonX parse_tool_calls method to ensure our concatenation fix works correctly"""

    def test_parse_single_complete_tool_call(self):
        """Test parsing a single complete tool call - should work normally"""
        tool_calls_data = [
            {
                "index": 0,
                "id": "call_123",
                "type": "function",
                "function": {
                    "name": "test_function",
                    "arguments": '{"param1": "value1", "param2": "value2"}'
                }
            }
        ]
        
        result = WatsonX.parse_tool_calls(tool_calls_data)
        
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
            {
                "index": 0,
                "id": "call_123",
                "function": {"name": "test_function", "arguments": ""}
            },
            # Second chunk with partial arguments
            {
                "index": 0,
                "function": {"arguments": '{"param1": "val'}
            },
            # Third chunk completing arguments
            {
                "index": 0,
                "function": {"arguments": 'ue1", "param2": "value2"}'}
            },
        ]
        
        result = WatsonX.parse_tool_calls(tool_calls_data)
        
        assert len(result) == 1
        assert result[0]["id"] == "call_123"
        assert result[0]["function"]["name"] == "test_function"
        assert result[0]["function"]["arguments"] == '{"param1": "value1", "param2": "value2"}'

    def test_prevent_complete_json_concatenation(self):
        """Test our fix: prevent concatenation when both current and new arguments are complete JSON"""
        tool_calls_data = [
            # First complete tool call
            {
                "index": 0,
                "id": "call_123",
                "function": {
                    "name": "test_function",
                    "arguments": '{"param1": "value1", "param2": "value2"}'
                }
            },
            # Second complete tool call (this should NOT be concatenated)
            {
                "index": 0,
                "function": {"arguments": '{"param3": "value3", "param4": "value4"}'}
            },
        ]
        
        result = WatsonX.parse_tool_calls(tool_calls_data)
        
        assert len(result) == 1
        # Should have the first complete JSON, not concatenated
        assert result[0]["function"]["arguments"] == '{"param1": "value1", "param2": "value2"}'
        # Should NOT contain the concatenated malformed JSON
        assert '{"param1": "value1", "param2": "value2"}{"param3": "value3", "param4": "value4"}' not in result[0]["function"]["arguments"]

    def test_allow_fragment_to_complete_concatenation(self):
        """Test that fragments can still be added to complete JSON (edge case)"""
        tool_calls_data = [
            # First chunk with complete JSON
            {
                "index": 0,
                "id": "call_123",
                "function": {
                    "name": "test_function",
                    "arguments": '{"param1": "value1"}'
                }
            },
            # Second chunk with invalid JSON fragment (should concatenate)
            {
                "index": 0,
                "function": {"arguments": ', "param2": "value2"}'}
            },
        ]
        
        result = WatsonX.parse_tool_calls(tool_calls_data)
        
        assert len(result) == 1
        # Should allow concatenation since second chunk is not valid JSON
        assert '{"param1": "value1"}, "param2": "value2"}' in result[0]["function"]["arguments"]

    def test_multiple_tool_calls_different_indices(self):
        """Test multiple tool calls with different indices work correctly"""
        tool_calls_data = [
            {
                "index": 0,
                "id": "call_123",
                "function": {"name": "function1", "arguments": '{"param1": "value1"}'}
            },
            {
                "index": 1,
                "id": "call_456",
                "function": {"name": "function2", "arguments": '{"param2": "value2"}'}
            },
        ]
        
        result = WatsonX.parse_tool_calls(tool_calls_data)
        
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
            {
                "index": 0,
                "id": "call_123",
                "function": {"name": "test_function", "arguments": ""}
            },
            {
                "index": 0,
                "function": {"arguments": None}
            },
        ]
        
        result = WatsonX.parse_tool_calls(tool_calls_data)
        
        assert len(result) == 1
        assert result[0]["function"]["arguments"] == ""

    def test_edge_case_user_reported_issue(self):
        """Test the exact scenario from the user's issue report"""
        # This simulates the user's reported issue
        tool_calls_data = [
            {
                "index": 0,
                "id": "call_123",
                "function": {
                    "name": "test_function",
                    "arguments": '{"param1": "val1", "param2": "value2", "param3": "value3"}'
                }
            },
            # This would have caused the duplication in the old code
            {
                "index": 0,
                "function": {"arguments": '{"param1": "val1", "param2": "value2", "param3": "value3"}'}
            },
        ]
        
        result = WatsonX.parse_tool_calls(tool_calls_data)
        
        assert len(result) == 1
        # Verify we don't get the malformed concatenated result
        expected_bad_result = '{"param1": "val1", "param2": "value2", "param3": "value3"}{"param1": "val1", "param2": "value2", "param3": "value3"}'
        assert result[0]["function"]["arguments"] != expected_bad_result
        # Verify we keep the original first complete JSON
        assert result[0]["function"]["arguments"] == '{"param1": "val1", "param2": "value2", "param3": "value3"}'

    def test_missing_function_structure_handling(self):
        """Test handling of malformed tool call data"""
        tool_calls_data = [
            {
                "index": 0,
                "id": "call_123",
                "function": {"name": "test_function", "arguments": '{"param1": "value1"}'}
            },
            # Missing function key
            {
                "index": 0,
                "id": "call_124"
            },
        ]
        
        result = WatsonX.parse_tool_calls(tool_calls_data)
        
        assert len(result) == 2
        assert result[0]["function"]["arguments"] == '{"param1": "value1"}'
        # Second tool call should have empty function structure
        assert result[1]["function"]["name"] == ""
        assert result[1]["function"]["arguments"] == ""
        
    def test_complex_nested_json_no_concatenation(self):
        """Test complex nested JSON objects don't get concatenated"""
        complex_json = '{"user": {"name": "test", "settings": {"theme": "dark", "notifications": true}}}'
        
        tool_calls_data = [
            {
                "index": 0,
                "id": "call_123",
                "function": {"name": "test_function", "arguments": complex_json}
            },
            # Another complete JSON that should not be concatenated
            {
                "index": 0,
                "function": {"arguments": '{"another": "complete", "json": {"object": "here"}}'}
            },
        ]
        
        result = WatsonX.parse_tool_calls(tool_calls_data)
        
        assert len(result) == 1
        assert result[0]["function"]["arguments"] == complex_json
        # Ensure no concatenation occurred
        assert "another" not in result[0]["function"]["arguments"]
