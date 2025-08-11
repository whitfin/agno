from datetime import datetime
from textwrap import dedent

from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.models.openai import OpenAIChat
from agno.tools.exa import ExaTools

# ************* Agent Database *************
db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"
db = PostgresDb(db_url=db_url)
# *******************************

# ************* Agent Instructions *************
instructions = dedent(
    """\
    You are a distinguished research tasked with conducting research and answering questions about the research.
    You are passed past conversation history. If you have not provided the user with a research report, conduct research and provide a report in the <expected_output> format provided below.

    If you've already provided the user with a research report, answer questions about the research report in a natural, conversational manner.
    If the user asks you to update or conduct more research, you should conduct the research and provide a new report in the <expected_output> format provided below.

    You should exercise judgement and help user understand the research report and prepare a report they can submit to their supervisor.

    1. Research Methodology
        - Conduct 1-3 distinct academic searches. Prefer less searches.
        - Focus on peer-reviewed publications and recent breakthrough findings
        - Identify key researchers and institutions

    2. Analysis Framework
        - Synthesize findings across sources.
        - Identify consensus and controversies.
        - Assess practical implications.

    3. Quality Standards
        - Ensure accurate citations.
        - Maintain academic rigor.
        - Present balanced perspectives.
        - Highlight future research directions.\
"""
)

expected_output = dedent(
    """\
    # {Engaging Title}

    ## {Overview}
    {Concise overview of the research and key findings}

    ## {Introduction}
    {Context and significance}
    {Report objectives}

    ## {Section Name}
    {Section content}

    {% if there are more sections %}
    ## {Section Name}
    {Section content}
    {% endif %}

    ## Conclusion
    {Conclusion based on the findings}
    ---\
"""
)
# *******************************

# ************* Create Agent *************
research_agent = Agent(
    name="Research Agent",
    agent_id="research-agent",
    model=OpenAIChat(id="gpt-5"),
    db=db,
    instructions=instructions,
    expected_output=expected_output,
    enable_user_memories=True,
    tools=[
        ExaTools(
            start_published_date=datetime.now().strftime("%Y-%m-%d"), type="keyword"
        )
    ],
    add_datetime_to_context=True,
    add_history_to_context=True,
    num_history_runs=3,
    markdown=True,
)
# *******************************
