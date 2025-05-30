from agno.agent import Agent
from agno.team import Team
from agno.models.openai import OpenAIChat
from agno.tools.googlesearch import GoogleSearchTools
from agno.storage.postgres import PostgresStorage
from agno.workflow.v2.workflow import Workflow
from agno.workflow.v2.pipeline import Pipeline
from agno.workflow.v2.task import Task
from agno.workflow.v2.trigger import TriggerType
from agno.utils.pprint import pprint_run_response
from typing import Dict, Any

# Define agents
blog_analyzer = Agent(
    name="Blog Analyzer",
    model=OpenAIChat(id="gpt-4o"),
    tools=[GoogleSearchTools()],
    instructions="Extract key insights and content from blog posts"
)

content_planner = Agent(
    name="Content Planner",
    model=OpenAIChat(id="gpt-4o"),
    instructions="Create engaging social media content plans based on analysis"
)

# Define research team for complex analysis
research_team = Team(
    name="Research Team",
    mode="coordinate",
    members=[blog_analyzer, content_planner],
    instructions="Analyze content and create comprehensive social media strategy"
)

# Define tasks with more flexible input validation
analyze_blog_task = Task(
    name="analyze_blog",
    executor=blog_analyzer,
    description="Analyze the provided blog URL and extract key insights",
    expected_input={"blog_url": str},
    expected_output="Blog analysis with key points and themes",
    strict_input_validation=False  # Allow flexible inputs
)

plan_content_task = Task(
    name="plan_content",
    executor=content_planner,
    description="Create social media content plan based on analysis",
    expected_input={"blog_analysis": str, "platform": str},
    expected_output="Structured content plan with posts and timing",
    strict_input_validation=False  # Allow flexible inputs
)

research_task = Task(
    name="research_content",
    executor=research_team,
    description="Deep research and analysis of content",
    expected_input={"topic": str},
    expected_output="Comprehensive research report",
    strict_input_validation=False  # Allow flexible inputs
)

# Define pipelines
content_creation_pipeline = Pipeline(
    name="content_creation",
    description="End-to-end content creation from blog to social media",
    tasks=[analyze_blog_task, plan_content_task]
)

research_pipeline = Pipeline(
    name="research_pipeline",
    description="Deep research workflow using teams",
    tasks=[research_task, plan_content_task]
)

# Define workflow


class ContentCreationWorkflow(Workflow):
    name = "Content Creation Workflow"
    description = "Automated content creation from blog posts to social media"
    trigger = TriggerType.MANUAL
    storage = PostgresStorage(
        table_name="content_workflows",
        db_url="postgresql+psycopg://ai:ai@localhost:5532/ai"
    )
    pipelines = [content_creation_pipeline, research_pipeline]


# Usage
if __name__ == "__main__":
    workflow = ContentCreationWorkflow()

    print("=== Content Creation Pipeline (Rich Display) ===")
    try:
        workflow.print_response(
            pipeline_name="content_creation",
            blog_url="https://docs.agno.com/introduction/agents",
            platform="twitter",
            markdown=True,
            show_time=True,
            show_task_details=True
        )
    except Exception as e:
        print(f"Content creation pipeline failed: {e}")

    print("\n" + "="*60 + "\n")

    print("=== Research Pipeline (Rich Display) ===")
    try:
        workflow.print_response(
            pipeline_name="research_pipeline",
            topic="AI trends in 2024",
            platform="twitter",
            markdown=True,
            show_time=True,
            show_task_details=True
        )
    except Exception as e:
        print(f"Research pipeline failed: {e}")

    print("\n" + "="*60 + "\n")

    print("=== Research Pipeline (Using pprint_workflow_response) ===")
    try:
        result = workflow.run(
            pipeline_name="research_pipeline",
            topic="AI trends in 2024",
            platform="twitter"
        )
        pprint_run_response(result, markdown=True, show_time=True)
    except Exception as e:
        print(f"Research pipeline failed: {e}")
