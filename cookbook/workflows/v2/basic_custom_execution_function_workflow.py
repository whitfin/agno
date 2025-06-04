from typing import Any, Dict

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.run.response import RunResponse
from agno.storage.sqlite import SqliteStorage
from agno.team import Team
from agno.tools.googlesearch import GoogleSearchTools
from agno.workflow.v2.sequence import Sequence
from agno.workflow.v2.task import Task
from agno.workflow.v2.trigger import ManualTrigger
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

# Custom execution functions that wrap agent/team calls with additional logic


def custom_blog_analysis_function(inputs: Dict[str, Any]) -> RunResponse:
    """
    Custom function that does preprocessing, calls an agent, and does postprocessing
    """
    query = inputs.get("query", "No query provided")

    # Custom preprocessing
    print(f"🔍 Starting custom blog analysis for: {query}")

    # Add custom context and formatting
    enhanced_query = f"""
        BLOG ANALYSIS REQUEST:
        Topic: {query}
        
        Please provide:
        1. Key themes and trends
        2. Target audience insights  
        3. Content opportunities
        4. SEO considerations
        
        Additional context from previous tasks:
        {inputs.get("context", "No previous context")}
    """

    # Call the agent with enhanced input
    try:
        response = blog_analyzer.run(enhanced_query)

        # Custom postprocessing
        enhanced_content = f"""
            ## Custom Blog Analysis Results

            **Original Query:** {query}

            **Analysis:**
            {response.content}

            **Custom Insights:**
            - Analysis completed with enhanced context
            - Ready for next stage processing
            - Confidence level: High
        """.strip()

        # Return enhanced response
        return RunResponse(
            content=enhanced_content,
            messages=response.messages,
            metrics=response.metrics,
        )

    except Exception as e:
        return RunResponse(
            content=f"Custom blog analysis failed: {str(e)}",
            event="custom_analysis_error",
        )


def custom_team_research_function(inputs: Dict[str, Any]) -> RunResponse:
    """
    Custom function that coordinates team execution with custom logic
    """
    query = inputs.get("query", "No query provided")

    print(f"🔬 Starting custom team research for: {query}")
    print(f"Available inputs: {list(inputs.keys())}")

    # Get the output from the previous task (custom_analysis)
    previous_analysis = inputs.get("custom_analysis", "")
    if not previous_analysis:
        # Fallback keys
        previous_analysis = inputs.get("output", "") or inputs.get("content", "")

    # Create enhanced team prompt
    team_prompt = f"""
        RESEARCH COORDINATION REQUEST:
        
        Primary Topic: {query}
        
        Previous Analysis: {previous_analysis[:500] if previous_analysis else "No previous analysis"}
        
        Team Mission:
        1. Build upon the previous analysis
        2. Conduct deeper research on the topic
        3. Validate and expand findings
        4. Provide actionable recommendations
        
        Please coordinate effectively and provide a unified research report.
    """

    try:
        response = research_team.run(team_prompt)

        enhanced_content = f"""
            ## Custom Team Research Report

            **Research Topic:** {query}

            **Previous Analysis Integration:** {"✓ Integrated" if previous_analysis else "✗ No previous context"}

            **Team Coordination Results:**
            {response.content}

            **Custom Team Insights:**
            - Multi-agent coordination completed
            - Cross-validated findings included
            - Ready for strategic planning phase
        """.strip()

        return RunResponse(
            content=enhanced_content,
            messages=response.messages,
            metrics=response.metrics,
        )

    except Exception as e:
        return RunResponse(
            content=f"Custom team research failed: {str(e)}", event="custom_team_error"
        )


def custom_content_planning_function(inputs: Dict[str, Any]) -> RunResponse:
    """
    Custom function that does intelligent content planning with context awareness
    """
    query = inputs.get("query", "No query provided")

    print(f"📝 Starting custom content planning for: {query}")
    print(f"Available inputs: {list(inputs.keys())}")

    # Get the output from the previous task (custom_research)
    previous_research = inputs.get("custom_research", "")
    if not previous_research:
        # Fallback keys
        previous_research = inputs.get("output", "") or inputs.get("content", "")

    # Create intelligent planning prompt
    planning_prompt = f"""
        STRATEGIC CONTENT PLANNING REQUEST:
        
        Core Topic: {query}
        
        Research Foundation: {previous_research[:500] if previous_research else "No research foundation"}
        
        Planning Requirements:
        1. Create a comprehensive content strategy based on the research
        2. Leverage the research findings effectively
        3. Identify content formats and channels
        4. Provide timeline and priority recommendations
        5. Include engagement and distribution strategies
        
        Please create a detailed, actionable content plan.
    """

    try:
        response = content_planner.run(planning_prompt)

        enhanced_content = f"""
            ## Strategic Content Plan

            **Planning Topic:** {query}

            **Research Integration:** {"✓ Research-based" if previous_research else "✗ No research foundation"}

            **Content Strategy:**
            {response.content}

            **Custom Planning Enhancements:**
            - Research Integration: {"High" if previous_research else "Baseline"}
            - Strategic Alignment: Optimized for multi-channel distribution
            - Execution Ready: Detailed action items included
        """.strip()

        return RunResponse(
            content=enhanced_content,
            messages=response.messages,
            metrics=response.metrics,
        )

    except Exception as e:
        return RunResponse(
            content=f"Custom content planning failed: {str(e)}",
            event="custom_planning_error",
        )


# Define tasks using different executor types
custom_analysis_task = Task(
    name="custom_analysis",
    execution_function=custom_blog_analysis_function,  # Custom function with agent
    description="Custom blog analysis with preprocessing and postprocessing",
)

research_task = Task(
    name="research_content",
    team=research_team,  # Direct team execution
    description="Deep research and analysis of content",
)

custom_research_task = Task(
    name="custom_research",
    execution_function=custom_team_research_function,  # Custom function with team
    description="Custom team research with coordination logic",
)

custom_planning_task = Task(
    name="custom_planning",
    execution_function=custom_content_planning_function,  # Custom function with agent
    description="Custom content planning with context integration",
)

# Define sequences showcasing different approaches
custom_sequence = Sequence(
    name="custom_sequence",
    description="Custom workflow using execution functions",
    tasks=[custom_analysis_task, custom_research_task, custom_planning_task],
)

mixed_sequence = Sequence(
    name="mixed_sequence",
    description="Mixed workflow combining direct and custom execution",
    tasks=[custom_analysis_task, research_task, custom_planning_task],
)

# Define workflow


class ContentCreationWorkflow(Workflow):
    name = "Content Creation Workflow"
    description = "Automated content creation with custom execution options"
    trigger = ManualTrigger()
    storage = SqliteStorage(
        table_name="content_workflows_v2", db_file="tmp/workflow_data_v2.db"
    )
    sequences = [custom_sequence, mixed_sequence]


# Usage examples
if __name__ == "__main__":
    workflow = ContentCreationWorkflow()
    print("=== Custom Sequence (Custom Execution Functions) ===")
    try:
        workflow.print_response(
            query="AI trends in 2024",
            sequence_name="custom_sequence",
            markdown=True,
            show_time=True,
            show_task_details=True,
        )
    except Exception as e:
        print(f"Custom sequence failed: {e}")

    print("\n" + "=" * 60 + "\n")

    # print("=== Mixed Sequence (Combination Approach) ===")
    # try:
    #     workflow.print_response(
    #         query="AI trends in 2024",
    #         sequence_name="mixed_sequence",
    #         markdown=True,
    #         show_time=True,
    #         show_task_details=True,
    #     )
    # except Exception as e:
    #     print(f"Mixed sequence failed: {e}")
