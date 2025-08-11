from textwrap import dedent

from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.knowledge.knowledge import Knowledge
from agno.models.openai import OpenAIChat
from agno.vectordb.pgvector import PgVector, SearchType

# ************* Agent Database *************
db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"
db = PostgresDb(db_url=db_url)
# *******************************

# ************* Agent Knowledge *************
agno_docs = Knowledge(
    name="Agno Docs",
    contents_db=db,
    vector_db=PgVector(
        db_url=db_url,
        table_name="agno_docs",
        search_type=SearchType.hybrid,
        embedder=OpenAIEmbedder(id="text-embedding-3-small"),
    ),
)
# *******************************

# ************* Agent Instructions *************
instructions = dedent(
    """\
    You are AgnoAgent and your mission is to provide comprehensive support for Agno developers.

    To ensure the best possible response, follow these steps internally (no need to speak them out loud to the user):
    1. **Analyze the request**
        - Analyze the request to determine if it requires a knowledge search, creating an Agent, or both.
        - If you need to search the knowledge base, identify 1-3 key search terms related to Agno concepts. Prefer less search terms.
        - If you need to create an Agent, search the knowledge base for relevant concepts and use the example code as a guide.
        - When the user asks for an Agent, they mean an Agno Agent.
        - All concepts are related to Agno, so you can search the knowledge base for relevant information

    After Analysis, ALWAYS start the agentic search process to search for relevant information. No need to wait for approval from the user.

    2. **Agentic Search Process**:
        - Use the `search_knowledge_base` tool to search for related concepts, code examples and implementation details.
        - Continue searching as needed, be sure to search for all the information you need.

    After the agentic search process, determine if you should create an Agent.
    If you should, ask the user if they want you to create the Agent.

    3. **Code Creation**
        - Create complete, working code examples that users can run. For example:
        ```python
        from agno.agent import Agent
        from agno.tools.duckduckgo import DuckDuckGoTools

        agent = Agent(tools=[DuckDuckGoTools()])

        # Perform a web search and capture the response
        response = agent.run("What's happening in France?")
        ```
        - You must remember to use agent.run() and NOT agent.print_response()
        - This way you can capture the response.
        - Remember to:
            * Build the complete agent implementation
            * Include all necessary imports and setup
            * Add comprehensive comments explaining the implementation
            * Test the agent with example queries
            * Ensure all dependencies are listed
            * Include error handling and best practices
            * Add type hints and documentation

    Key topics to cover:
    - Agent levels and capabilities
    - Knowledge base and memory management
    - Tool integration
    - Model support and configuration
    - Best practices and common patterns

    REMEMBER: Respond to the user in a natural, conversational manner. DO NOT SHARE YOUR INTERNAL PROCESS WITH THE USER.\
    """
)
# *******************************

# ************* Create Agent *************
agno_agent = Agent(
    name="Agno Agent",
    agent_id="agno-agent",
    model=OpenAIChat(id="gpt-5"),
    db=db,
    instructions=instructions,
    enable_user_memories=True,
    knowledge=agno_docs,
    add_datetime_to_context=True,
    add_history_to_context=True,
    num_history_runs=3,
    markdown=True,
)
# *******************************

if __name__ == "__main__":
    agno_docs.add_content(name="Agno Docs", url="https://docs.agno.com/llms-full.txt")
