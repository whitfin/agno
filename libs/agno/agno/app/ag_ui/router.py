"""AG-UI FastAPI router for AGno agents and teams - simplified version."""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional, Iterator, AsyncIterator, Union

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from agno.agent.agent import Agent, RunResponse
from agno.team.team import Team
from agno.utils.log import logger

from agno.app.ag_ui.events import (
    BaseEvent,
    EventType,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    StateSnapshotEvent,
    StateDeltaEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallStartEvent,
    StepStartedEvent,
    StepFinishedEvent,
    MessagesSnapshotEvent,
    CustomEvent,
)
from agno.app.ag_ui.utils import CaseConverter, SSEFormatter
from agno.app.ag_ui.tools import ToolManager, ToolCallParser
from agno.app.ag_ui.frontend_tools import FrontendToolHandler

# Valid event types that the frontend expects
VALID_EVENT_TYPES = {
    EventType.TEXT_MESSAGE_START.value,
    EventType.TEXT_MESSAGE_CONTENT.value,
    EventType.TEXT_MESSAGE_END.value,
    EventType.TEXT_MESSAGE_CHUNK.value,
    EventType.TOOL_CALL_START.value,
    EventType.TOOL_CALL_ARGS.value,
    EventType.TOOL_CALL_END.value,
    EventType.TOOL_CALL_CHUNK.value,
    EventType.STATE_SNAPSHOT.value,
    EventType.STATE_DELTA.value,
    EventType.MESSAGES_SNAPSHOT.value,
    EventType.RUN_STARTED.value,
    EventType.RUN_FINISHED.value,
    EventType.RUN_ERROR.value,
    EventType.STEP_STARTED.value,
    EventType.STEP_FINISHED.value,
    EventType.RAW.value,
    EventType.CUSTOM.value,
}

__all__ = ["get_router"]


class RunRequest(BaseModel):
    """Standard request format for the /run endpoint."""
    message: str
    stream: bool = True
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    monitor: bool = False
    state: Optional[Dict[str, Any]] = None  # Add state support
    tools: Optional[List[Dict[str, Any]]] = None  # Add tools support


def get_router(*, agent: Optional[Agent] = None, team: Optional[Team] = None) -> APIRouter:
    """Create a FastAPI router for AG-UI integration.
    
    Args:
        agent: An AGno Agent instance
        team: An AGno Team instance
        
    Returns:
        FastAPI router with the /run endpoint configured
        
    Raises:
        ValueError: If neither agent nor team is provided
    """
    if agent is None and team is None:
        raise ValueError("Either `agent` or `team` must be provided.")
    
    router = APIRouter()
    formatter = SSEFormatter()
    case_converter = CaseConverter()
    tool_manager = ToolManager()
    frontend_tool_handler = FrontendToolHandler()
    
    @router.post("/run")
    async def run_agent_or_team(request: Request):
        """Execute the Agent or Team and return AG-UI events."""
        logger.info("🚀 [AG-UI Router] Starting new /run request")
        
        # Parse request
        try:
            json_body = await request.json()
            logger.debug(f"📥 [AG-UI Router] Raw request body: {json.dumps(json_body, indent=2)}")
            
            # Extract message
            message = json_body.get("message", "")
            if not message:
                # Try to extract from messages array
                messages = json_body.get("messages", [])
                for msg in reversed(messages):
                    if msg.get("role") == "user":
                        message = msg.get("content", "")
                        break
            
            if not message:
                raise HTTPException(status_code=400, detail="No user message found")
            
            # Extract other parameters
            stream = json_body.get("stream", True)
            session_id = json_body.get("threadId") or json_body.get("session_id") or str(uuid.uuid4())
            user_id = json_body.get("user_id")
            state = json_body.get("state")  # Extract state from request
            tools = json_body.get("tools", [])  # Extract tools from request
            
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Failed to parse request")
            err_event = RunErrorEvent(
                type=EventType.RUN_ERROR,
                message=str(e),
                code="parse_error"
            )
            return JSONResponse([err_event.model_dump(exclude_none=True)], status_code=400)
        
        run_id = str(uuid.uuid4())
        logger.info(f"🎯 [AG-UI Router] Processing request: run_id={run_id}, session_id={session_id}, stream={stream}")
        logger.info(f"📝 [AG-UI Router] Message: '{message}'")
        
        # Log tools for debugging
        if tools:
            logger.info(f"🔧 [AG-UI Router] Request includes {len(tools)} tools:")
            for i, tool in enumerate(tools):
                tool_name = tool.get("name", "unnamed")
                tool_desc = tool.get("description", "no description")
                logger.info(f"  Tool {i+1}: '{tool_name}' - {tool_desc[:50]}...")
                logger.debug(f"  Tool {i+1} full definition: {json.dumps(tool, indent=2)}")
        
        # Execute agent or team
        base_obj = agent if agent is not None else team
        
        # Store original tools to restore after execution
        original_tools = None
        
        try:
            # Handle dynamic tool injection for agents
            if tools and isinstance(base_obj, Agent):
                logger.info("🔨 [AG-UI Router] Starting dynamic tool injection process")
                
                # Convert AG-UI tools to AGno Function tools
                from agno.tools.function import Function
                dynamic_functions = []
                
                for tool_idx, tool in enumerate(tools):
                    if isinstance(tool, dict) and "name" in tool:
                        try:
                            tool_name = tool["name"]
                            logger.debug(f"🔍 [AG-UI Router] Processing tool #{tool_idx+1}: '{tool_name}'")
                            
                            # Check if this is a frontend-only tool by name
                            frontend_only_tools = ['update_steps', 'start_step', 'complete_step', 'generate_haiku']
                            is_frontend_only = tool_name in frontend_only_tools
                            
                            # Skip tools that are not frontend tools - they shouldn't be injected
                            if not is_frontend_only:
                                logger.info(f"⏭️ [AG-UI Router] Skipping non-frontend tool: '{tool_name}'")
                                continue
                            
                            logger.info(f"🎨 [AG-UI Router] Tool '{tool_name}' is frontend-only: {is_frontend_only}")
                            
                            if is_frontend_only:
                                # Create frontend-only tool with dummy entrypoint for OpenAI compatibility
                                def make_frontend_placeholder(tool_name):
                                    def frontend_placeholder(**kwargs):
                                        logger.info(f"🎭 [FRONTEND TOOL CALLED] '{tool_name}' with args: {kwargs}")
                                        # This should never be called - frontend handles these tools
                                        return {"frontend_tool": tool_name, "args": kwargs}
                                    return frontend_placeholder
                                
                                func = Function(
                                    name=tool_name,
                                    description=tool.get("description", ""),
                                    parameters=tool.get("parameters", {}),
                                    entrypoint=make_frontend_placeholder(tool_name)
                                )
                                func._frontend_only = True
                                logger.info(f"✅ [AG-UI Router] Created frontend-only tool: '{tool_name}'")
                                dynamic_functions.append(func)
                            
                        except Exception as e:
                            logger.error(f"❌ [AG-UI Router] Failed to convert tool '{tool.get('name', 'unnamed')}': {e}")
                
                if dynamic_functions:
                    logger.info(f"📦 [AG-UI Router] Successfully created {len(dynamic_functions)} dynamic tools")
                    
                    # Store original tools
                    original_tools = base_obj.tools
                    logger.info(f"💾 [AG-UI Router] Stored {len(original_tools) if original_tools else 0} original tools")
                    
                    # Merge dynamic tools with existing tools, replacing duplicates by name
                    if original_tools:
                        # Create a map of existing tool names for efficient lookup
                        existing_tool_names = set()
                        for tool in original_tools:
                            if hasattr(tool, 'name'):
                                existing_tool_names.add(tool.name)
                        
                        # Keep only original tools that don't have dynamic replacements
                        filtered_original_tools = []
                        replaced_tools = []
                        for tool in original_tools:
                            tool_name = getattr(tool, 'name', None)
                            if tool_name and tool_name not in [df.name for df in dynamic_functions]:
                                filtered_original_tools.append(tool)
                            else:
                                replaced_tools.append(tool_name)
                        
                        if replaced_tools:
                            logger.info(f"🔄 [AG-UI Router] Replacing existing tools: {replaced_tools}")
                        
                        # Set the new tools list
                        base_obj.tools = filtered_original_tools + dynamic_functions
                    else:
                        base_obj.tools = dynamic_functions
                    
                    # Clear cached tools so they get recomputed with the new dynamic tools
                    base_obj._tools_for_model = None
                    base_obj._functions_for_model = None
                    
                    logger.info(f"📊 [AG-UI Router] Final tool count: {len(base_obj.tools)} tools")
                    
                    # Log final tool list
                    logger.info("📋 [AG-UI Router] Final tool list:")
                    for i, tool in enumerate(base_obj.tools):
                        tool_name = getattr(tool, 'name', 'unnamed')
                        is_frontend = getattr(tool, '_frontend_only', False)
                        logger.info(f"  {i+1}. '{tool_name}' (frontend: {is_frontend})")
                    
                    # Force tool determination to ensure tools are properly prepared
                    logger.info("🔧 [AG-UI Router] Forcing tool determination for model...")
                    try:
                        base_obj.determine_tools_for_model(base_obj.model, session_id=session_id)
                        logger.info(f"✅ [AG-UI Router] Tool determination complete")
                        
                        # Log what tools were prepared for the model
                        if base_obj._tools_for_model:
                            logger.debug(f"📋 [AG-UI Router] Tools prepared for model: {len(base_obj._tools_for_model)}")
                            for i, tool_dict in enumerate(base_obj._tools_for_model):
                                logger.debug(f"  Model Tool {i+1}: {json.dumps(tool_dict, indent=2)}")
                    except Exception as e:
                        logger.error(f"❌ [AG-UI Router] Error in determine_tools_for_model: {e}", exc_info=True)
            
            # Build run kwargs
            run_kwargs = {
                "message": message,
                "session_id": session_id,
                "stream": stream,
            }
            if user_id:
                run_kwargs["user_id"] = user_id
            if state:
                run_kwargs["state"] = state
            
            logger.info("🏃 [AG-UI Router] Executing agent/team run...")
            logger.debug(f"Run kwargs: {json.dumps({k: v for k, v in run_kwargs.items() if k != 'state'}, indent=2)}")
            
            # Execute
            if hasattr(base_obj, "arun"):
                # arun needs to be awaited
                response_iter = await base_obj.arun(**run_kwargs)
            else:
                response_iter = base_obj.run(**run_kwargs)
            
            logger.info("✅ [AG-UI Router] Agent/team execution started successfully")
                
        except Exception as exc:
            logger.exception("❌ [AG-UI Router] Error during agent/team execution")
            err_event = RunErrorEvent(
                type=EventType.RUN_ERROR,
                message=str(exc),
                code="runtime_error"
            )
            return JSONResponse([err_event.model_dump(exclude_none=True)], status_code=500)
        finally:
            # Restore original tools if we modified them
            if original_tools is not None and isinstance(base_obj, Agent):
                base_obj.tools = original_tools
                # Clear cached tools so they get recomputed with original tools next time
                base_obj._tools_for_model = None
                base_obj._functions_for_model = None
                logger.info(f"♻️ [AG-UI Router] Restored {len(original_tools)} original tools")
        
        # Handle streaming response
        if stream:
            logger.info("📡 [AG-UI Router] Starting streaming response")
            
            async def sse_generator():
                logger.debug("🌊 [SSE Generator] Starting event stream")
                
                # Start event
                start_event = RunStartedEvent(
                    type=EventType.RUN_STARTED,
                    thread_id=session_id,
                    run_id=run_id
                )
                logger.debug(f"📤 [SSE Generator] Emitting RUN_STARTED event: {start_event}")
                yield formatter.format_event(start_event)
                
                message_id = str(uuid.uuid4())
                message_started = False
                current_state = state  # Track current state
                chunk_count = 0
                
                # Track processed tool calls to avoid duplicates
                processed_tool_calls = set()
                
                # Convert to async iterator if needed
                if hasattr(response_iter, "__aiter__"):
                    iterator = response_iter
                else:
                    async def _aiter_sync(sync_iter):
                        for item in sync_iter:
                            yield item
                    iterator = _aiter_sync(response_iter)
                
                # Process chunks
                try:
                    async for chunk in iterator:
                        chunk_count += 1
                        logger.debug(f"📦 [SSE Generator] Processing chunk #{chunk_count}")
                        
                        if chunk is None:
                            logger.debug(f"⚠️ [SSE Generator] Received None chunk, skipping")
                            continue
                        
                        # Log chunk details
                        logger.debug(f"🔍 [SSE Generator] Chunk type: {type(chunk)}")
                        logger.debug(f"🔍 [SSE Generator] Chunk attributes: {dir(chunk)}")
                        
                        # Check for state updates
                        if hasattr(chunk, "agent_state") and chunk.agent_state:
                            current_state = chunk.agent_state
                            logger.info(f"🔄 [SSE Generator] State update detected")
                            state_event = StateSnapshotEvent(
                                type=EventType.STATE_SNAPSHOT,
                                snapshot=current_state
                            )
                            formatted_state = formatter.format_event(state_event)
                            logger.debug(f"📤 [SSE Generator] Sending STATE_SNAPSHOT: {formatted_state.strip()}")
                            yield formatted_state
                        
                        # Check for step events
                        if hasattr(chunk, "event_type"):
                            logger.debug(f"📌 [SSE Generator] Event type in chunk: {chunk.event_type}")
                            if chunk.event_type == "step_started" and hasattr(chunk, "step_name"):
                                logger.info(f"🚦 [SSE Generator] Step started: {chunk.step_name}")
                                yield formatter.format_event(
                                    StepStartedEvent(
                                        type=EventType.STEP_STARTED,
                                        step_name=chunk.step_name
                                    )
                                )
                            elif chunk.event_type == "step_finished" and hasattr(chunk, "step_name"):
                                logger.info(f"🏁 [SSE Generator] Step finished: {chunk.step_name}")
                                yield formatter.format_event(
                                    StepFinishedEvent(
                                        type=EventType.STEP_FINISHED,
                                        step_name=chunk.step_name
                                    )
                                )
                        
                        # Process content
                        content_str = ""
                        try:
                            content_str = chunk.get_content_as_string() if chunk.content else ""
                            if content_str:
                                logger.debug(f"💬 [SSE Generator] Content in chunk: {content_str[:100]}...")
                        except Exception as e:
                            logger.debug(f"⚠️ [SSE Generator] Could not extract content: {e}")
                        
                        if content_str:
                            if not message_started:
                                logger.info(f"📝 [SSE Generator] Starting text message")
                                yield formatter.format_event(
                                    TextMessageStartEvent(
                                        type=EventType.TEXT_MESSAGE_START,
                                        message_id=message_id,
                                        role="assistant"
                                    )
                                )
                                message_started = True
                            
                            yield formatter.format_event(
                                TextMessageContentEvent(
                                    type=EventType.TEXT_MESSAGE_CONTENT,
                                    message_id=message_id,
                                    delta=content_str
                                )
                            )
                        
                        # Process tool calls - CRITICAL SECTION FOR FRONTEND TOOLS
                        if hasattr(chunk, "tools") and chunk.tools:
                            logger.info(f"🔧 [SSE Generator] TOOL CALLS DETECTED! Processing {len(chunk.tools)} tool calls")
                            logger.debug(f"🔧 [SSE Generator] Raw tools data: {chunk.tools}")
                            
                            # End text message if started
                            if message_started:
                                logger.debug(f"📝 [SSE Generator] Ending text message before tool calls")
                                yield formatter.format_event(
                                    TextMessageEndEvent(
                                        type=EventType.TEXT_MESSAGE_END,
                                        message_id=message_id
                                    )
                                )
                                message_started = False
                            
                            # Process tool calls with deduplication
                            for tool_idx, tool_info in enumerate(chunk.tools):
                                logger.info(f"🔨 [SSE Generator] Processing tool call #{tool_idx+1}")
                                logger.debug(f"🔨 [SSE Generator] Tool info type: {type(tool_info)}")
                                
                                # Extract tool call ID for deduplication
                                tool_call_id = None
                                if isinstance(tool_info, dict):
                                    tool_call_id = tool_info.get("tool_call_id")
                                
                                # Skip if we've already processed this tool call
                                if tool_call_id and tool_call_id in processed_tool_calls:
                                    logger.info(f"⏭️ [SSE Generator] Skipping duplicate tool call: {tool_call_id}")
                                    continue
                                
                                # Mark as processed
                                if tool_call_id:
                                    processed_tool_calls.add(tool_call_id)
                                
                                # Safe JSON serialization for debugging
                                try:
                                    if isinstance(tool_info, dict):
                                        # Create a safe version for logging by removing non-serializable objects
                                        safe_tool_info = {k: str(v) if not isinstance(v, (str, int, float, bool, list, dict, type(None))) else v 
                                                        for k, v in tool_info.items()}
                                        logger.debug(f"🔨 [SSE Generator] Tool info content: {json.dumps(safe_tool_info, indent=2)}")
                                    else:
                                        logger.debug(f"🔨 [SSE Generator] Tool info content: {str(tool_info)}")
                                except Exception as e:
                                    logger.debug(f"🔨 [SSE Generator] Tool info (couldn't serialize): {type(tool_info)} - {e}")
                                
                                # Check for custom event types first
                                if isinstance(tool_info, dict) and "type" in tool_info:
                                    event_type = tool_info.get("type")
                                    logger.debug(f"📌 [SSE Generator] Custom event type: {event_type}")
                                    
                                    # Handle state updates
                                    if event_type == "state_update" and "state" in tool_info:
                                        logger.info(f"🔄 [SSE Generator] State update via tool")
                                        yield formatter.format_event(
                                            StateSnapshotEvent(
                                                type=EventType.STATE_SNAPSHOT,
                                                snapshot=tool_info["state"]
                                            )
                                        )
                                    
                                    # Handle step events
                                    elif event_type == "step_started" and "step_name" in tool_info:
                                        logger.info(f"🚦 [SSE Generator] Step started via tool: {tool_info['step_name']}")
                                        # Also emit state if provided
                                        if "state" in tool_info:
                                            yield formatter.format_event(
                                                StateSnapshotEvent(
                                                    type=EventType.STATE_SNAPSHOT,
                                                    snapshot=tool_info["state"]
                                                )
                                            )
                                        yield formatter.format_event(
                                            StepStartedEvent(
                                                type=EventType.STEP_STARTED,
                                                step_name=tool_info["step_name"]
                                            )
                                        )
                                    
                                    elif event_type == "step_finished" and "step_name" in tool_info:
                                        logger.info(f"🏁 [SSE Generator] Step finished via tool: {tool_info['step_name']}")
                                        # Also emit state if provided
                                        if "state" in tool_info:
                                            yield formatter.format_event(
                                                StateSnapshotEvent(
                                                    type=EventType.STATE_SNAPSHOT,
                                                    snapshot=tool_info["state"]
                                                )
                                            )
                                        yield formatter.format_event(
                                            StepFinishedEvent(
                                                type=EventType.STEP_FINISHED,
                                                step_name=tool_info["step_name"]
                                            )
                                        )
                                
                                # Regular tool calls (they have tool_name)
                                elif "tool_name" in tool_info:
                                    tool_name = tool_info.get("tool_name", "")
                                    call_id = tool_info.get("tool_call_id", str(uuid.uuid4()))
                                    
                                    # Check if this is a frontend tool
                                    frontend_tools = ['update_steps', 'start_step', 'complete_step', 'generate_haiku']
                                    is_frontend_tool = tool_name in frontend_tools
                                    logger.info(f"🎨 [SSE Generator] Tool '{tool_name}' is frontend tool: {is_frontend_tool}")
                                    
                                    # Always emit tool call events for all tools
                                    parsed_tool_name, args = ToolCallParser.parse(tool_info)
                                    
                                    logger.info(f"📤 [SSE Generator] Emitting TOOL_CALL_START for '{parsed_tool_name}' (ID: {call_id})")
                                    yield formatter.format_event(
                                        ToolCallStartEvent(
                                            type=EventType.TOOL_CALL_START,
                                            tool_call_id=call_id,
                                            tool_call_name=parsed_tool_name,
                                            parent_message_id=message_id
                                        )
                                    )
                                    
                                    args_str = json.dumps(args) if isinstance(args, dict) else str(args)
                                    logger.info(f"📤 [SSE Generator] Emitting TOOL_CALL_ARGS with: {args_str}")
                                    yield formatter.format_event(
                                        ToolCallArgsEvent(
                                            type=EventType.TOOL_CALL_ARGS,
                                            tool_call_id=call_id,
                                            delta=args_str
                                        )
                                    )
                                    
                                    logger.info(f"📤 [SSE Generator] Emitting TOOL_CALL_END")
                                    yield formatter.format_event(
                                        ToolCallEndEvent(
                                            type=EventType.TOOL_CALL_END,
                                            tool_call_id=call_id
                                        )
                                    )
                                    
                                    logger.info(f"✅ [SSE Generator] Completed emitting events for tool '{parsed_tool_name}'")
                                else:
                                    logger.warning(f"⚠️ [SSE Generator] Unknown tool info format: {tool_info}")
                
                except Exception as e:
                    logger.exception(f"❌ [SSE Generator] Error in event generator after {chunk_count} chunks")
                    yield formatter.format_event(
                        RunErrorEvent(
                            type=EventType.RUN_ERROR,
                            message=str(e),
                            code="stream_error"
                        )
                    )
                
                # End message if still open
                if message_started:
                    logger.info(f"📝 [SSE Generator] Ending text message at stream end")
                    yield formatter.format_event(
                        TextMessageEndEvent(
                            type=EventType.TEXT_MESSAGE_END,
                            message_id=message_id
                        )
                    )
                
                # Finish event
                logger.info(f"🏁 [SSE Generator] Stream complete after {chunk_count} chunks")
                yield formatter.format_event(
                    RunFinishedEvent(
                        type=EventType.RUN_FINISHED,
                        thread_id=session_id,
                        run_id=run_id
                    )
                )
                logger.debug("✅ [SSE Generator] Event stream ended")
            
            return StreamingResponse(sse_generator(), media_type="text/event-stream")
        
        else:
            # Non-streaming response
            logger.info("📦 [AG-UI Router] Processing non-streaming response")
            events = []
            
            # Start event
            events.append(
                RunStartedEvent(
                    type=EventType.RUN_STARTED,
                    thread_id=session_id,
                    run_id=run_id
                )
            )
            
            message_id = str(uuid.uuid4())
            
            # Process response
            if isinstance(response_iter, RunResponse):
                # Single response
                events.append(
                    TextMessageStartEvent(
                        type=EventType.TEXT_MESSAGE_START,
                        message_id=message_id,
                        role="assistant"
                    )
                )
                
                content_str = response_iter.get_content_as_string() if response_iter.content else ""
                if content_str:
                    events.append(
                        TextMessageContentEvent(
                            type=EventType.TEXT_MESSAGE_CONTENT,
                            message_id=message_id,
                            delta=content_str
                        )
                    )
                
                events.append(
                    TextMessageEndEvent(
                        type=EventType.TEXT_MESSAGE_END,
                        message_id=message_id
                    )
                )
                
                # Check for state in response
                if hasattr(response_iter, "agent_state") and response_iter.agent_state:
                    events.append(
                        StateSnapshotEvent(
                            type=EventType.STATE_SNAPSHOT,
                            snapshot=response_iter.agent_state
                        )
                    )
            
            # Finish event
            events.append(
                RunFinishedEvent(
                    type=EventType.RUN_FINISHED,
                    thread_id=session_id,
                    run_id=run_id
                )
            )
            
            # Convert to camelCase and return
            json_events = []
            for event in events:
                event_dict = event.model_dump(exclude_none=True)
                event_dict = case_converter.convert_dict_keys(event_dict)
                json_events.append(event_dict)
            
            logger.info(f"📤 [AG-UI Router] Returning {len(json_events)} events")
            return JSONResponse(json_events)
    
    return router 