import json
from typing import Any, Dict, List

import pytest


def parse_tool_calls_openai_logic(tool_calls_data):
    """
    Extracted core logic from OpenAI parse_tool_calls method for testing
    This tests our concatenation fix without requiring external dependencies
    """
    tool_calls: List[Dict[str, Any]] = []
    for _tool_call in tool_calls_data:
        _index = getattr(_tool_call, 'index', 0) or 0
        _tool_call_id = getattr(_tool_call, 'id', None)
        _tool_call_type = getattr(_tool_call, 'type', None)
        _function_name = getattr(_tool_call.function, 'name', None) if hasattr(_tool_call, 'function') and _tool_call.function else None
        _function_arguments = getattr(_tool_call.function, 'arguments', None) if hasattr(_tool_call, 'function') and _tool_call.function else None

        if len(tool_calls) <= _index:
            tool_calls.extend([{}] * (_index - len(tool_calls) + 1))
        tool_call_entry = tool_calls[_index]
        if not tool_call_entry:
            tool_call_entry["id"] = _tool_call_id
            tool_call_entry["type"] = _tool_call_type
            tool_call_entry["function"] = {
                "name": _function_name or "",
                "arguments": _function_arguments or "",
            }
        else:
            if _function_name:
                tool_call_entry["function"]["name"] += _function_name
            if _function_arguments:
                # Check if current arguments are complete JSON to avoid concatenation duplication
                current_args = tool_call_entry["function"]["arguments"]
                should_concatenate = True
                
                if current_args and current_args.strip():
                    try:
                        # If current args are valid JSON, this might be a separate tool call
                        json.loads(current_args)
                        
                        # Try to parse the new arguments too
                        try:
                            json.loads(_function_arguments)
                            # Both are complete JSON objects - this is likely a duplication issue
                            should_concatenate = False
                        except json.JSONDecodeError:
                            # New arguments are fragments, safe to concatenate
                            pass
                    except json.JSONDecodeError:
                        # Current args are incomplete fragments, safe to concatenate
                        pass
                
                if should_concatenate:
                    tool_call_entry["function"]["arguments"] += _function_arguments
                    
            if _tool_call_id:
                tool_call_entry["id"] = _tool_call_id
            if _tool_call_type:
                tool_call_entry["type"] = _tool_call_type
    return tool_calls


class MockToolCall:
    """Mock object to simulate tool call structure"""
    
    def __init__(self, index: int = 0, id: str = None, type: str = "function", name: str = None, arguments: str = None):
        self.index = index
        self.id = id
        self.type = type
        self.function = MockFunction(name, arguments)


class MockFunction:
    """Mock object to simulate function structure"""
    
    def __init__(self, name: str = None, arguments: str = None):
        self.name = name
        self.arguments = arguments


class TestParseToolCallsCore:
    """Core tests for the parse_tool_calls concatenation fix logic"""

    def test_prevent_complete_json_concatenation_core_fix(self):
        """Test our main fix: prevent concatenation when both current and new arguments are complete JSON"""
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
        
        result = parse_tool_calls_openai_logic(tool_calls_data)
        
        assert len(result) == 1
        # Should have the first complete JSON, not concatenated
        assert result[0]["function"]["arguments"] == '{"param1": "value1", "param2": "value2"}'
        # Should NOT contain the concatenated malformed JSON
        expected_bad_result = '{"param1": "value1", "param2": "value2"}{"param3": "value3", "param4": "value4"}'
        assert result[0]["function"]["arguments"] != expected_bad_result

    def test_preserve_streaming_fragment_concatenation(self):
        """Test that legitimate streaming fragments still get concatenated correctly"""
        tool_calls_data = [
            # First chunk with function name
            MockToolCall(index=0, id="call_123", name="test_function", arguments=""),
            # Second chunk with partial arguments
            MockToolCall(index=0, arguments='{"param1": "val'),
            # Third chunk completing arguments
            MockToolCall(index=0, arguments='ue1", "param2": "value2"}'),
        ]
        
        result = parse_tool_calls_openai_logic(tool_calls_data)
        
        assert len(result) == 1
        assert result[0]["id"] == "call_123"
        assert result[0]["function"]["name"] == "test_function"
        assert result[0]["function"]["arguments"] == '{"param1": "value1", "param2": "value2"}'

    def test_exact_user_reported_issue_scenario(self):
        """Test the exact scenario from the user's issue report"""
        # This simulates the user's reported issue:
        # Parameters being submitted as:
        # {"text": "{"param1": "val1", "param2": "value2", "param3": "value3"}{"param1": "val1", "param2": "value2", "param3": "value3"}"}
        # instead of 2 separate tool calls
        
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
        
        result = parse_tool_calls_openai_logic(tool_calls_data)
        
        assert len(result) == 1
        # Verify we don't get the malformed concatenated result from the user's report
        expected_bad_result = '{"param1": "val1", "param2": "value2", "param3": "value3"}{"param1": "val1", "param2": "value2", "param3": "value3"}'
        assert result[0]["function"]["arguments"] != expected_bad_result
        # Verify we keep the original first complete JSON
        assert result[0]["function"]["arguments"] == '{"param1": "val1", "param2": "value2", "param3": "value3"}'

    def test_fragment_plus_complete_json_edge_case(self):
        """Test edge case where a fragment can be added to complete JSON"""
        tool_calls_data = [
            # First chunk with complete JSON but actually incomplete due to missing closing
            MockToolCall(
                index=0,
                id="call_123",
                name="test_function", 
                arguments='{"param1": "value1"'  # Missing closing }
            ),
            # Second chunk with fragment that completes it (should concatenate)
            MockToolCall(
                index=0,
                arguments=', "param2": "value2"}'
            ),
        ]
        
        result = parse_tool_calls_openai_logic(tool_calls_data)
        
        assert len(result) == 1
        # Should allow concatenation since first chunk is not valid JSON
        assert result[0]["function"]["arguments"] == '{"param1": "value1", "param2": "value2"}'

    def test_complete_json_plus_fragment_should_concatenate(self):
        """Test that fragments can still be added to complete JSON when the fragment is invalid JSON"""
        tool_calls_data = [
            MockToolCall(
                index=0,
                id="call_123",
                name="test_function",
                arguments='{"param1": "value1"}'  # Valid JSON
            ),
            # Fragment that's not valid JSON by itself (should concatenate)
            MockToolCall(
                index=0,
                arguments=', "param2": "value2"}'  # Not valid JSON alone
            ),
        ]
        
        result = parse_tool_calls_openai_logic(tool_calls_data)
        
        assert len(result) == 1
        # Should concatenate because second part is not valid JSON
        assert '{"param1": "value1"}, "param2": "value2"}' in result[0]["function"]["arguments"]

    def test_multiple_complete_json_objects_no_concatenation(self):
        """Test multiple separate complete JSON objects don't get concatenated"""
        json1 = '{"action": "search", "query": "test"}'
        json2 = '{"action": "filter", "criteria": "date"}'
        
        tool_calls_data = [
            MockToolCall(index=0, id="call_123", name="tool1", arguments=json1),
            MockToolCall(index=0, arguments=json2),  # Should NOT concatenate
        ]
        
        result = parse_tool_calls_openai_logic(tool_calls_data)
        
        assert len(result) == 1
        assert result[0]["function"]["arguments"] == json1
        # Ensure the second JSON is not concatenated
        assert "filter" not in result[0]["function"]["arguments"]
        assert "criteria" not in result[0]["function"]["arguments"]

    def test_whitespace_handling_in_complete_json(self):
        """Test that JSON with whitespace is still recognized as complete"""
        json_with_whitespace = '  {"param": "value"}  '
        
        tool_calls_data = [
            MockToolCall(index=0, id="call_123", name="test", arguments=json_with_whitespace),
            MockToolCall(index=0, arguments='{"other": "value"}'),  # Should NOT concatenate
        ]
        
        result = parse_tool_calls_openai_logic(tool_calls_data)
        
        assert len(result) == 1
        assert result[0]["function"]["arguments"] == json_with_whitespace
        # Ensure no concatenation
        assert "other" not in result[0]["function"]["arguments"]
