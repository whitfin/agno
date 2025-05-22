"""CopilotKit FastAPI router (synchronous).

This first iteration supports a basic `/status` health-check and a `/run` endpoint
that executes an Agno Agent or Team **without streaming** and returns an array of
AG-UI BaseEvent JSON dicts.

Once the SSE streaming milestone is tackled we can migrate the implementation to
`async` helpers similar to `agno.app.fastapi.async_router`.
"""
from __future__ import annotations

import uuid
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, UploadFile, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from agno.agent.agent import Agent, RunResponse
from agno.run.response import RunEvent
from agno.team.team import Team
from agno.utils.log import logger
from agno.tools.function import Function
from ag_ui.core.events import (
    BaseEvent,
    EventType,
    RunStartedEvent,
    RunFinishedEvent,
    RunErrorEvent,
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    ToolCallStartEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
)
from ag_ui.encoder.encoder import EventEncoder

__all__ = ["get_router"]


def _run_response_to_events(
    *,
    response: RunResponse,
    run_id: str,
    thread_id: str,
) -> List[BaseEvent]:
    """Convert a non-streaming RunResponse to a minimal AG-UI event list."""

    events: List[BaseEvent] = []

    # Lifecycle – run started
    events.append(
        RunStartedEvent(type=EventType.RUN_STARTED, thread_id=thread_id, run_id=run_id)
    )

    # Text message (assistant)
    message_id = str(uuid.uuid4())
    events.append(
        TextMessageStartEvent(
            type=EventType.TEXT_MESSAGE_START, message_id=message_id, role="assistant"
        )
    )

    content_str = response.get_content_as_string() if response.content else ""
    if content_str:
        events.append(
            TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT, message_id=message_id, delta=content_str
            )
        )

    events.append(
        TextMessageEndEvent(type=EventType.TEXT_MESSAGE_END, message_id=message_id)
    )

    # Lifecycle – run finished
    events.append(
        RunFinishedEvent(type=EventType.RUN_FINISHED, thread_id=thread_id, run_id=run_id)
    )

    return events


encoder = EventEncoder(accept="text/event-stream")


# ---------------------------------------------------------------------------
# Request schema helpers
# ---------------------------------------------------------------------------


class RunRequest(BaseModel):
    """Schema for application/json requests to the /run endpoint.

    This mirrors the form fields accepted by the traditional multipart/form-data
    version so that clients can choose either encoding.
    """

    message: str
    stream: bool = True
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    monitor: bool = False


def get_router(*, agent: Optional[Agent] = None, team: Optional[Team] = None) -> APIRouter:
    if agent is None and team is None:
        raise ValueError("Either `agent` or `team` must be provided.")

    router = APIRouter()

    @router.get("/status")
    def status():
        return {"status": "available"}

    @router.post("/run")
    async def run_agent_or_team(
        request: Request,
    ):
        """Execute the agent/team and return AG-UI events.

        If `stream` is True (default) we send a text/event-stream response; otherwise we
        aggregate events into a JSON array (mainly for testing).
        """
        # -------------------------------------------------------------------
        # Resolve payload values – prefer JSON body when provided, else form.
        # -------------------------------------------------------------------

        content_type = request.headers.get("content-type", "").lower()
        logger.debug(f"/run content-type={content_type}")

        json_body: Optional[Dict[str, Any]] = None
        form_data = None
        files: Optional[List[UploadFile]] = None

        if content_type.startswith("application/json"):
            json_body = await request.json()
            logger.debug(f"/run received JSON: {str(json_body)[:500]}")
        else:
            # Handle multipart/form-data or application/x-www-form-urlencoded
            form_data = await request.form()
            # Separate text fields and files
            files = [v for v in form_data.values() if isinstance(v, UploadFile)]

        if json_body is not None:
            # Try to parse as our simple RunRequest model first.
            try:
                payload = RunRequest.model_validate(json_body)  # type: ignore[arg-type]
                _message = payload.message
                _stream = payload.stream
                _session_id = payload.session_id or str(uuid.uuid4())
                _user_id = payload.user_id
                _monitor = payload.monitor

                _tools = json_body.get("tools", [])  # type: ignore[index]
                _context = json_body.get("context", [])  # type: ignore[index]
                _forwarded_props = json_body.get("forwardedProps", {})  # type: ignore[index]
            except Exception:
                # Fallback: assume AG-UI RunAgentInput-like payload structure.
                keys = list(json_body.keys())
                msg_count = len(json_body.get("messages", [])) if isinstance(json_body.get("messages", []), list) else 0
                logger.debug(f"Received AG-UI RunAgentInput payload with keys={keys} and messages={msg_count}")

                _session_id = (
                    json_body.get("threadId")  # type: ignore[index]
                    or json_body.get("session_id")  # type: ignore[index]
                    or str(uuid.uuid4())
                )

                # Extract the latest user message content
                _message = ""
                try:
                    for msg in reversed(json_body.get("messages", [])):  # type: ignore[index]
                        if msg.get("role") == "user":
                            _message = msg.get("content", "")
                            break
                except Exception as e:
                    logger.debug(f"Failed to extract user message from payload: {e}")

                if not _message:
                    raise HTTPException(
                        status_code=400,
                        detail="No user message found in 'messages' array of payload",
                    )

                _stream = True  # default to SSE when using AG-UI client
                _user_id = None
                _monitor = False

                _tools = json_body.get("tools", [])  # type: ignore[index]
                _context = json_body.get("context", [])  # type: ignore[index]
                _forwarded_props = json_body.get("forwardedProps", {})  # type: ignore[index]

        else:
            if form_data is None:
                raise HTTPException(status_code=422, detail="Unsupported content type")

            # Extract simple scalar fields
            _message = form_data.get("message")
            if _message is None or _message == "":
                raise HTTPException(status_code=400, detail="`message` form field is required")

            _stream_val = form_data.get("stream", "true")
            _stream = str(_stream_val).lower() not in ("false", "0", "no")

            _session_id = form_data.get("session_id") or form_data.get("sessionId") or str(uuid.uuid4())
            _user_id = form_data.get("user_id") or form_data.get("userId")
            _monitor = False  # monitor flag not supported via form in this router

            # Initialize optional fields so later logic has predictable values
            _tools = []  # No dynamic tools via plain form-data path
            _context = None
            _forwarded_props = None

        run_id = str(uuid.uuid4())
        logger.debug(
            f"CopilotKit /run invoked run_id={run_id} session_id={_session_id} stream={_stream} json_body={json_body is not None}",
        )

        # -------------------------------------------------------------------
        # Merge dynamic tools with existing agent tools instead of overwriting
        # -------------------------------------------------------------------

        # Helper to combine tool lists while preserving order and uniqueness by name (if available)
        def _merge_tool_lists(original: Optional[list[Any]], incoming: list[Any]) -> list[Any]:  # noqa: ANN401
            if not original:
                return incoming
            # Build a set of existing tool names where possible
            names: set[str] = set()
            merged: list[Any] = []
            for t in original + incoming:
                name = None
                try:
                    # Function or Toolkit has .name attribute; dict uses key
                    if isinstance(t, dict):
                        name = t.get("name")
                    else:
                        name = getattr(t, "name", None)
                except Exception:
                    pass
                if name is not None and name in names:
                    continue
                if name is not None:
                    names.add(name)
                merged.append(t)
            return merged

        # Normalize a single tool object (dict) so OpenAI always receives the
        # `{type:"function", function:{...}}` wrapper that it requires.
        def _normalize_tool_obj(tool: Any) -> Any:  # noqa: ANN401
            if not isinstance(tool, dict):
                return tool  # Already Function / Toolkit etc.

            # If already has "type" field, assume compliant
            if "type" in tool:
                return tool

            # If wrapped schema present under "function", just add type
            if "function" in tool:
                return {"type": "function", **tool}

            # Otherwise assume flat function definition coming from AG-UI
            if "name" in tool:
                return {
                    "type": "function",
                    "function": {
                        "name": tool.get("name"),
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {"type": "object", "properties": {}, "required": []}),
                    },
                }

            # Fallback – return unchanged
            return tool

        try:
            if _tools and len(_tools) > 0:
                # Drop agent placeholders (e.g. "agenticChatAgent") that come from frontend runtime mapping
                _tools = [t for t in _tools if not (isinstance(t, dict) and t.get("name", "").endswith("Agent"))]
                if not _tools:
                    _tools = []
                if agent is not None:
                    combined = _merge_tool_lists(agent.tools, _tools)
                    combined = [_normalize_tool_obj(t) for t in combined]
                    try:
                        local_agent = agent.deep_copy(update={"tools": combined})  # type: ignore[attr-defined]
                    except Exception as e:
                        logger.warning(
                            f"Failed to deep copy agent for dynamic tools – falling back to mutation: {e}"
                        )
                        agent.tools = combined  # type: ignore[attr-defined]
                        local_agent = agent
                elif team is not None:
                    combined = _merge_tool_lists(team.tools, _tools)
                    combined = [_normalize_tool_obj(t) for t in combined]
                    try:
                        local_team = team.deep_copy(update={"tools": combined})  # type: ignore[attr-defined]
                    except Exception as e:
                        logger.warning(
                            f"Failed to deep copy team for dynamic tools – falling back to mutation: {e}"
                        )
                        team.tools = combined  # type: ignore[attr-defined]
                        local_team = team
            # If no dynamic tools, keep originals
        except Exception as e:
            # Log and proceed without tools if something unexpected happened.
            logger.warning(f"Unable to merge dynamic tools: {e}")

        try:
            if local_agent is not None:
                run_response_iter = local_agent.run(
                    message=_message,
                    session_id=_session_id,
                    user_id=_user_id,
                    stream=_stream,
                    context=_context if json_body is not None else None,
                    forwarded_props=_forwarded_props if json_body is not None else None,
                )
            else:
                run_response_iter = local_team.run(
                    message=_message,
                    session_id=_session_id,
                    user_id=_user_id,
                    stream=_stream,
                    context=_context if json_body is not None else None,
                    forwarded_props=_forwarded_props if json_body is not None else None,
                )
        except Exception as exc:
            logger.exception("Error during agent run")
            err_event = RunErrorEvent(
                type=EventType.RUN_ERROR, message=str(exc), code="runtime_error"
            )
            return JSONResponse([err_event.model_dump(exclude_none=True)], status_code=500)

        # Helper to yield SSE lines
        def sse_event_generator():
            # If the underlying run returned an iterator/generator, iterate;
            # else wrap in list for non-stream runs.
            iterator = run_response_iter if hasattr(run_response_iter, "__iter__") else [run_response_iter]

            # Send run started lifecycle
            yield encoder.encode(
                RunStartedEvent(type=EventType.RUN_STARTED, thread_id=_session_id, run_id=run_id)
            )

            # Prepare single message lifecycle across all content chunks
            message_id = str(uuid.uuid4())
            message_started = False

            for chunk in iterator:
                if chunk is None:
                    continue

                try:
                    content_str = chunk.get_content_as_string() if chunk.content else ""
                except Exception:
                    content_str = ""

                # Skip empty chunks
                if content_str == "":
                    continue

                # On first non-empty chunk emit TEXT_MESSAGE_START
                if not message_started:
                    yield encoder.encode(
                        TextMessageStartEvent(
                            type=EventType.TEXT_MESSAGE_START,
                            message_id=message_id,
                            role="assistant",
                        )
                    )
                    message_started = True

                # Emit content delta
                yield encoder.encode(
                    TextMessageContentEvent(
                        type=EventType.TEXT_MESSAGE_CONTENT,
                        message_id=message_id,
                        delta=content_str,
                    )
                )

                # If this chunk contains tool calls, emit tool call events
                if hasattr(chunk, "formatted_tool_calls") and chunk.formatted_tool_calls:
                    # formatted_tool_calls is already a list of strings (legacy); treat as single args
                    for idx, call_args in enumerate(chunk.formatted_tool_calls):
                        call_id = str(uuid.uuid4())
                        tool_name = "tool"  # unknown
                        yield encoder.encode(
                            ToolCallStartEvent(
                                type=EventType.TOOL_CALL_START,
                                tool_call_id=call_id,
                                tool_call_name=tool_name,
                                parent_message_id=message_id,
                            )
                        )
                        yield encoder.encode(
                            ToolCallArgsEvent(
                                type=EventType.TOOL_CALL_ARGS,
                                tool_call_id=call_id,
                                delta=call_args,
                            )
                        )
                        yield encoder.encode(
                            ToolCallEndEvent(
                                type=EventType.TOOL_CALL_END,
                                tool_call_id=call_id,
                            )
                        )

                elif hasattr(chunk, "tool_calls") and chunk.tool_calls:
                    for tc in chunk.tool_calls:
                        call_id = tc.get("id", str(uuid.uuid4()))
                        tool_name = tc.get("function", {}).get("name", "tool")
                        args_str = tc.get("function", {}).get("arguments", "{}")

                        yield encoder.encode(
                            ToolCallStartEvent(
                                type=EventType.TOOL_CALL_START,
                                tool_call_id=call_id,
                                tool_call_name=tool_name,
                                parent_message_id=message_id,
                            )
                        )
                        yield encoder.encode(
                            ToolCallArgsEvent(
                                type=EventType.TOOL_CALL_ARGS,
                                tool_call_id=call_id,
                                delta=args_str,
                            )
                        )
                        yield encoder.encode(
                            ToolCallEndEvent(
                                type=EventType.TOOL_CALL_END,
                                tool_call_id=call_id,
                            )
                        )

            # After stream ends, close message if started
            if message_started:
                yield encoder.encode(
                    TextMessageEndEvent(type=EventType.TEXT_MESSAGE_END, message_id=message_id)
                )

            # Run finished lifecycle
            yield encoder.encode(
                RunFinishedEvent(type=EventType.RUN_FINISHED, thread_id=_session_id, run_id=run_id)
            )

        if _stream:
            from fastapi.responses import StreamingResponse

            return StreamingResponse(
                sse_event_generator(), media_type="text/event-stream"
            )

        # Else aggregate non-stream response
        if isinstance(run_response_iter, RunResponse):
            events = _run_response_to_events(
                response=run_response_iter, run_id=run_id, thread_id=_session_id
            )
            json_events = [e.model_dump(exclude_none=True) for e in events]
            return JSONResponse(content=json_events)
        else:
            # Already streamed but caller requested JSON; aggregate all
            accumulated: List[BaseEvent] = []
            for chunk in run_response_iter:
                accumulated.extend(
                    _run_response_to_events(
                        response=chunk, run_id=run_id, thread_id=_session_id
                    )[1:-1]
                )
            # Add lifecycle
            accumulated.insert(
                0,
                RunStartedEvent(type=EventType.RUN_STARTED, thread_id=_session_id, run_id=run_id),
            )
            accumulated.append(
                RunFinishedEvent(type=EventType.RUN_FINISHED, thread_id=_session_id, run_id=run_id)
            )
            return JSONResponse(
                [ev.model_dump(exclude_none=True) for ev in accumulated]
            )

    return router 