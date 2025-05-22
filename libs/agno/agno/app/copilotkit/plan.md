# CopilotKit × AG-UI – Implementation Plan

## 1. Objectives
1. Deliver a fully-functional **basic chat application** that complies with the open Agent–User-Interaction (AG-UI) Protocol.
2. Expose the agent backend over **HTTP SSE** so every AG-UI compliant frontend (CopilotKit, etc.) can subscribe to the standard 16 event types.
3. Use **CopilotKit** (React + TypeScript) as the reference client to demonstrate end-to-end streaming, tool invocation and state sync.
4. Publish a reusable **Python package** (`agno.app.copilotkit`) that any Agno agent can mount (similar to `agno.app.fastapi`).

## 2. High-level Architecture
```
                        ┌──────────────┐            ┌──────────────┐
                        │  React App   │            │  React App   │
                        │ (CopilotKit) │            │  …anything… │
                        └──────┬───────┘            └──────┬───────┘
                               │  AG-UI events (SSE, JSON, protobuf)
                               ▼
                    ┌────────────────────────┐
                    │  agno.app.copilotkit   │  ◄── our deliverable
                    │   (FastAPI backend)    │
                    └──────┬─────┬───────────┘
             run_agent()   │     │  EventEncoder
                          ▼      ▼
                ┌────────────────────┐
                │   Agno  Agent/Team │  ← existing
                └────────────────────┘
```

### Key flows
1. Frontend POSTs `/v1/run` → backend validates input, spins up/continues an Agno `Agent.run()` **generator** (`stream=True`).
2. Each `RunResponse` / `TeamRunResponse` chunk is converted to **AG-UI events** and encoded as **SSE** using `EventEncoder` from `ag_ui.encoder`.
3. Frontend (`@ag-ui/client` → CopilotKit `HttpAgent`) renders events in real-time, applies state patches, prompts user for tool input, etc.

## 3. Tasks & Milestones

### 3.1 Backend package (`agno.app.copilotkit`)
1. 🗂 Scaffold module structure – `__init__.py`, `router.py`, `app.py`, `serve.py`, `settings.py`.
2. ♻️ Refactor common logic from `agno.app.fastapi.sync_router` into shared helpers so CopilotKit backend can reuse file-processing & media helpers.
3. 📡 Router endpoints
   • `GET /status` → health-check.
   • `POST /run`   → accepts `RunAgentInput` form-data + optional uploads.
4. 🌊 Streaming implementation
   • Wrap agent/team `run(... stream=True)` generator.
   • Map Agno `RunEvent` → AG-UI `BaseEvent` subclasses.
   • Use `EventEncoder(accept="text/event-stream")` to emit SSE frames.
5. 🧪 Unit tests
   • Encode/Decode round-trip (reuse `ag_ui` test helpers).
   • Happy-path chat run with `TestAgent`.
   • Tool-call lifecycle & state delta edge-cases.
6. 🔌 Dependency glue
   • `pip install ag-ui[python-sdk]>=0.1.0`.
   • Expose `FastAPIApp` style helper (`CopilotKitAPIApp`).

### 3.2 Frontend demo (CopilotKit)
1. 🧰 Create `ag-ui/copilotkit-demo` (Next.js 14, TypeScript).
2. `npm i @ag-ui/client @copilotkit/react-core tailwindcss`.
3. Implement pages:
   • `/` → minimal chat window (message list + input).
   • Stream events through `HttpAgent` pointed at backend.
4. Add code blocks toggling **LLM provider** to showcase forwarded props.
5. (Stretch) showcase **tool-based UI** (use CopilotKit `useCopilotAction`).

### 3.3 Dev & Ops
1. 🛠 `Makefile` targets: `dev-backend`, `dev-frontend`, `lint`, `test`.
2. 🐳 Docker-compose with two services (backend API, Next.js, Caddy for HTTPS local).
3. ☁️ Deploy preview – backend on Fly.io, frontend on Vercel.

### 3.4 Timeline (1 engineer)
| Week | Deliverable |
|-----|-------------|
| 1 | Backend scaffolding, `/status`, `/run` non-streaming path |
| 2 | SSE streaming, EventEncoder integration, unit tests pass |
| 3 | Frontend basic chat via CopilotKit `HttpAgent` |
| 4 | File uploads, tool call demo, documentation, CI/CD |

## 4. Implementation Details

### 4.1 Event Mapping Table (Agno → AG-UI)
| Source | Destination | Notes |
|--------|-------------|-------|
| `RunEvent.run_start` | `RunStartedEvent` | Use `thread_id=session_id` |
| `RunEvent.step_start` | `StepStartedEvent` | `step_name=node.name` |
| `RunEvent.text_start` | `TextMessageStartEvent` | role="assistant" |
| `RunEvent.text_delta` | `TextMessageContentEvent` | chunk streaming |
| `RunEvent.text_end` | `TextMessageEndEvent` | … |
| `RunEvent.tool_start` | `ToolCallStartEvent` | map tool id/name |
| `RunEvent.tool_delta` | `ToolCallArgsEvent` | JSON patch fragments |
| `RunEvent.tool_end` | `ToolCallEndEvent` | … |
| `RunEvent.state_snapshot` | `StateSnapshotEvent` | full state |
| `RunEvent.state_delta` | `StateDeltaEvent` | RFC 6902 patch |
| `RunEvent.run_end` | `RunFinishedEvent` | … |
| exception | `RunErrorEvent` | include traceback in dev |

### 4.2 Validation & Verification
• Reuse `verifyEvents(debug)` RxJS operator (TypeScript SDK) in frontend tests.
• Python side: pydantic validation when constructing `BaseEvent`.

### 4.3 Security & Limits
• Max upload size 20 MB (env `MAX_UPLOAD_MB`).
• Rate-limit `/run` 30 RPM/IP via starlette-middlewares.
• CORS restricted in prod via `CORS_ORIGIN_LIST`.

## 5. Open Questions
1. Do we need WebSocket transport initially? (SSE is sufficient for CopilotKit.)
2. Will agents be long-lived processes or instantiated per request? (Leverage Agno sessions.)
3. How should we expose builder-friendly auth (e.g., bearer token)?

## 6. Next Steps
- Approve this plan 📝
- Create backend scaffolding PR
- Schedule weekly milestones / demos
