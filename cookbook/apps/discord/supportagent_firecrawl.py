
from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.tools.reasoning import ReasoningTools
from agno.app.discord.client import DiscordClient
from agno.tools.firecrawl import FirecrawlTools
from agno.tools.slack import SlackTools
from textwrap import dedent
docs_agent = Agent(
    model=Claude(id="claude-3-7-sonnet-latest"),
    # Agentic RAG is enabled by default when `knowledge` is provided to the Agent.
    # search_knowledge=True gives the Agent the ability to search on demand
    # search_knowledge is True by default
    search_knowledge=True,
    tools=[FirecrawlTools(scrape=False, crawl=True, search=True, poll_interval=2), SlackTools()],
    instructions=[
        "You are an user support agent for Agno, help them by sending links of the docs section related to their question by searching here https://docs.agno.com/introduction",
        "Always search https://docs.agno.com/introduction before answering the question. Don't use any other source to answer and ALWAYS send the link to the source",
        "If unable to help, tell the team in the slack channel (C086X7SA6BA) by tagging <@U08MWE4QXEF> and let the user know that the team will help them",
        dedent("""\
                    Always send issues with message_url to the slack channel (C086X7SA6BA) to notify Agno developers after categorizing it into one of the following 
                    :bricks: CORE PRODUCT CATEGORIES
                    1. Agents
                    - Agent orchestration (single, team, loop)
                    - Agent deployment (self-hosted, UI, cloud)
                    - Response models (structured outputs)
                    - Context window & session handling
                    - Retry, fallbacks, stop conditions
                    2. Tools & Toolkits
                    - Built-in tools (DuckDuckGo, Firecrawl, YFinance, etc.)
                    - Custom tools (user-built / API-based)
                    - MCPTools (launching, integration, async issues)
                    - Tool serialization (tool-call output parsing)
                    - Tool errors & fallbacks
                    3. Knowledge Base / Retrieval (RAG)
                    - Vector DB integration (Qdrant, LanceDB, Chroma)
                    - Custom embedder usage (SentenceTransformer, Gemini)
                    - File ingestion (PDF, CSV, Markdown, S3, local, MinIO)
                    - Search quality & performance
                    - Hybrid vs dense search
                    4. Memory
                    - Session memory (short-term, per-agent)
                    - Long-term memory (SQLite, Postgres)
                    - User-specific memory (user_id-based)
                    - Agentic memory (auto-learned context)
                    - Memory isolation issues (multi-agent/threaded use)
                    5. Storage / Database
                    - PostgresStorage vs PostgresAgentStorage
                    - Async DB support
                    - SQLite quirks in multithreading
                    - Custom DB integration (Mongo, MySQL)
                    - File-backed storage
                    6. LLMs
                    - OpenAI, Anthropic, Groq, Gemini, Ollama
                    - Rate limits, auth, headers
                    - Structured output (Pydantic validation)
                    - Switching LLMs mid-agent/workflow
                    - Debugging LLM failures (400s, token overflow, etc.)
                    7. Eval & HITL
                    - Eval framework usage
                    - Human-in-the-loop workflows
                    - Sync/async feedback loops
                    - Eval result formatting
                    - Prompt evaluations
                    :jigsaw: INFRASTRUCTURE & PLATFORM
                    8. Playground / UI
                    - Agent UI (multi-agent, user switching)
                    - Async behavior in playground
                    - Embedded playground usage
                    - UI errors or latency
                    9. Workspace
                    - Workspace commands (ag ws)
                    - Team agents in Workspace
                    - Local LLM integration (Ollama, Docker)
                    - File structure and CLI usage
                    - Swagger APIs
                    10. Integration
                    - Slack, Discord, GitHub integration
                    - Langfuse, OpenTelemetry
                    - Async workflows (FastAPI, Celery, etc.)
                    - Auth layers (token, user_id)
                    - VS Code extensions / SDKs
                    11. Documentation & SDK
                    - Missing or outdated docs
                    - Example gaps (multi-agent, team, memory)
                    - SDK usage errors
                    - Installation/config issues
                    - Version mismatches
                    :gear: SUPPORT INFRASTRUCTURE
                    12. Bugs
                    - Regression bugs (e.g., post-upgrade breakages)
                    - Serialization failures
                    - Context bleed in threads
                    - Memory mismatch
                    13. Feature Requests
                    - Markdown support, multimodal, context config
                    - Better observability/logging
                    - New integrations
                    14. Feedback & UX
                    - Clarity of instructions / error messages
                    - DevX suggestions
                    - Missing “expected” behaviors
                    - Workflow bottlenecks
               If unable to help, tell the team in the slack channel (C086X7SA6BA) by tagging <@U08MWE4QXEF> and let the user know that the team will help them"""),
        
    ],
    add_history_to_messages=True,
    num_history_responses=3,
    add_datetime_to_instructions=True,
    markdown=True,
    debug_mode=True
)

DiscordClient(docs_agent)