"""🛑 Workflow Run Cancellation - Stopping Multi-Step Processes

This example shows how to cancel workflow runs during execution.
Workflows often involve multiple steps that can be cancelled between stages.
Perfect for scenarios like:
- Long data processing pipelines
- Multi-step analysis workflows  
- Complex automation sequences

Run `pip install openai agno` to install dependencies.
"""

import asyncio

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.workflow import Workflow


class DataAnalysisWorkflow(Workflow):
    """A workflow that processes data through multiple cancellable steps"""
    
    def __init__(self):
        super().__init__(
            name="Data Analysis Pipeline",
            description="Multi-step data processing workflow"
        )
        
        # Create an agent for the workflow steps
        self.analyst = Agent(
            model=OpenAIChat(id="gpt-4o-mini"),
            description="Data processing specialist",
            instructions=[
                "Provide detailed analysis at each step",
                "Be thorough and comprehensive"
            ]
        )
    
    async def arun(self, dataset: str = "sales_data.csv") -> str:
        """Multi-step workflow that can be cancelled between stages"""
        
        # Step 1: Data validation
        print(f"📊 Step 1: Validating {dataset}...")
        # Check if cancellation has been requested before each step
        self._check_if_cancelled()
            
        validation = await self.analyst.arun(
            f"Analyze the structure and quality of {dataset}. "
            "Check for missing values, outliers, and data consistency issues."
        )
        
        # Step 2: Data preprocessing  
        print("🔧 Step 2: Preprocessing data...")
        self._check_if_cancelled()
            
        preprocessing = await self.analyst.arun(
            "Design a comprehensive data preprocessing pipeline including "
            "normalization, feature engineering, and transformation steps."
        )
        
        # Step 3: Statistical analysis
        print("📈 Step 3: Performing statistical analysis...")
        self._check_if_cancelled()
            
        analysis = await self.analyst.arun(
            "Conduct detailed statistical analysis, generate insights, "
            "and create comprehensive visualizations and reports."
        )
        
        return f"Analysis complete: {analysis.content[:100]}..."


async def demonstrate_workflow_cancellation():
    """Show how to cancel a multi-step workflow"""
    
    workflow = DataAnalysisWorkflow()
    
    print("🚀 Starting data analysis workflow...")
    
    # Start the workflow
    task = asyncio.create_task(
        workflow.arun_workflow(dataset="large_customer_dataset.csv")
    )
    
    # Let it run through the first step
    await asyncio.sleep(2)
    
    print("⏹️ Deciding to cancel the workflow...")
    
    # Cancel the workflow
    cancelled = workflow.cancel_run(reason="New priority dataset arrived")
    print(f"Workflow cancellation requested: {cancelled}")
    
    try:
        result = await task
        print("Workflow completed:", result)
    except Exception as e:
        from agno.exceptions import RunCancelledException
        if isinstance(e, RunCancelledException):
            print("✅ Workflow was successfully cancelled!")
        else:
            print(f"Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(demonstrate_workflow_cancellation())