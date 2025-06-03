from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.storage.sqlite import SqliteStorage
from agno.team import Team
from agno.tools.googlesearch import GoogleSearchTools
from agno.workflow.v2.sequence import Sequence
from agno.workflow.v2.task import Task
from agno.workflow.v2.trigger import TriggerType
from agno.workflow.v2.workflow import Workflow

# Define agents
blog_analyzer = Agent(
    name="Blog Analyzer",
    model=OpenAIChat(id="gpt-4o"),
    tools=[GoogleSearchTools()],
    instructions="Extract key insights and content from blog posts",
)

content_planner = Agent(
    name="Content Planner",
    model=OpenAIChat(id="gpt-4o"),
    instructions="Create engaging social media content plans based on analysis",
)

# Define research team for complex analysis
research_team = Team(
    name="Research Team",
    mode="coordinate",
    members=[blog_analyzer, content_planner],
    instructions="Analyze content and create comprehensive social media strategy",
)

# Define tasks with consistent query-based input
analyze_blog_task = Task(
    name="analyze_blog",
    executor=blog_analyzer,
    description="Analyze the provided topic and extract key insights",
    expected_input={"query": str},
    expected_output="Blog analysis with key points and themes",
    strict_input_validation=False,
)

plan_content_task = Task(
    name="plan_content",
    executor=content_planner,
    description="Create social media content plan based on the research topic",
    expected_input={"query": str},
    expected_output="Structured content plan with posts and timing",
    strict_input_validation=False,
)

research_task = Task(
    name="research_content",
    executor=research_team,
    description="Deep research and analysis of content",
    expected_input={"query": str},
    expected_output="Comprehensive research report",
    strict_input_validation=False,
)

# Define sequences
content_creation_sequence = Sequence(
    name="content_creation",
    description="End-to-end content creation from blog to social media",
    tasks=[analyze_blog_task, plan_content_task],
)

research_sequence = Sequence(
    name="research_sequence", description="Deep research workflow using teams", tasks=[research_task, plan_content_task]
)

# Define workflow


class ContentCreationWorkflow(Workflow):
    name = "Content Creation Workflow"
    description = "Automated content creation from blog posts to social media"
    trigger = TriggerType.MANUAL
    storage = SqliteStorage(table_name="content_workflows",
                            db_file="tmp/workflow_data.db")
    sequences = [research_sequence]


# Usage
if __name__ == "__main__":
    workflow = ContentCreationWorkflow()
    print("=== Research Sequence (Rich Display) ===")
    try:
        workflow.print_response(
            query="AI trends in 2024", markdown=True, show_time=True, show_task_details=True)
    except Exception as e:
        print(f"Research sequence failed: {e}")
