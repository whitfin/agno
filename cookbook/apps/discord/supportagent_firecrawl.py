
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
                Always send issues with message_url to the slack channel (C086X7SA6BA) to notify Agno developers after categorizing it into one of the following categories:

                Task type:
                - Bug
                - Feature Request
                - Question
                - Improvement
                - Followup

                Product Area:
                - Docs
                - Agents
                - Agent orchestration
                - Agent deployment
                - Response models
                - fallbacks
                - stop conditions
                - Context window
                - session handling
                - Tools & Toolkits
                - Integrated tools
                - Custom tools (user-built/API)
                - MCPTools
                - Tool serialization/errors
                - Knowledge Base / Retrieval (RAG)
                - Vector DB integration
                - Custom embedders
                - File ingestion
                - Search quality & hybrid search
                - Memory
                - Session
                - User-specific or agentic memory
                - Memory isolation issues
                - Storage / Database
                - VectorDBs
                - Async DB support
                - File-backed/custom DB
                - LLMs
                - Model usage
                - Structured outputs
                - Rate limits/auth/debugging failures
                - Eval & HITL
                - Eval framework
                - Human-in-the-loop
                - Prompt evals and formatting
                - Workspace
                - Teams
                - Workflows
                - Integrations
                - AWS
               If category not listed create custom category
               If unable to help, tell the team in the slack channel (C086X7SA6BA) by tagging <@U08MWE4QXEF> and let the user know that the team will help them"""),
        
    ],
    add_history_to_messages=True,
    num_history_responses=3,
    add_datetime_to_instructions=True,
    markdown=True,
    debug_mode=True
)

DiscordClient(docs_agent)