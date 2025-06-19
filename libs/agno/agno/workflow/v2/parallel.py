from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import AsyncIterator, Iterator, List, Optional, Union
from agno.workflow.v2.step import Step
from agno.workflow.v2.types import StepInput, StepOutput
from agno.run.v2.workflow import WorkflowRunResponseEvent


@dataclass
class Parallel:
    """Execute multiple steps in parallel"""

    name: Optional[str] = None
    steps: List[Step] = None
    merge_strategy: str = "concat"  # "concat", "first", "last", "all"

    def __init__(self, *steps: Step, name: Optional[str] = None, merge_strategy: str = "concat"):
        self.name = name or "Parallel Execution"
        self.steps = list(steps)
        self.merge_strategy = merge_strategy

    def execute(
        self,
        step_input: StepInput,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> StepOutput:
        """Execute steps in parallel"""
        with ThreadPoolExecutor(max_workers=len(self.steps)) as executor:
            futures = {
                executor.submit(step.execute, step_input, session_id, user_id): step
                for step in self.steps
            }

            results = []
            for future in as_completed(futures):
                result = future.result()
                results.append(result)

        return self._merge_outputs(results)

    async def aexecute(
        self,
        step_input: StepInput,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> StepOutput:
        """Execute steps in parallel asynchronously"""
        import asyncio

        tasks = [
            step.aexecute(step_input, session_id, user_id)
            for step in self.steps
        ]
        results = await asyncio.gather(*tasks)
        return self._merge_outputs(results)

    def _merge_outputs(self, results: List[StepOutput]) -> StepOutput:
        """Merge multiple step outputs"""
        if not results:
            return StepOutput(content="")

        if self.merge_strategy == "first":
            return results[0]
        elif self.merge_strategy == "last":
            return results[-1]
        elif self.merge_strategy == "concat":
            content = "\n\n".join(r.content for r in results if r.content)
            return StepOutput(content=content)
        elif self.merge_strategy == "all":
            return StepOutput(content=str(results))
        else:
            return results[0]
