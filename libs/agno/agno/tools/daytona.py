import json
from os import getenv
from typing import Any, Dict, List, Optional

from agno.tools import Toolkit
from agno.utils.code_execution import prepare_python_code
from agno.utils.log import logger

try:
    from daytona import (
        CodeLanguage,
        CreateSandboxFromSnapshotParams,
        Daytona,
        DaytonaConfig,
        Sandbox,
    )

    # Import ExecuteResponse from the process module
    from daytona.common.process import ExecuteResponse  # type: ignore[import-untyped]
except ImportError:
    raise ImportError("`daytona` not installed. Please install using `pip install daytona`")


class DaytonaTools(Toolkit):
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        sandbox_id: Optional[str] = None,
        sandbox_language: Optional[CodeLanguage] = None,
        sandbox_target_region: Optional[str] = None,
        sandbox_os: Optional[str] = None,
        sandbox_os_user: Optional[str] = None,
        sandbox_env_vars: Optional[Dict[str, str]] = None,
        sandbox_labels: Optional[Dict[str, str]] = None,
        sandbox_public: Optional[bool] = None,
        sandbox_auto_stop_interval: Optional[int] = None,
        organization_id: Optional[str] = None,
        timeout: int = 300,  # 5 minutes default timeout
        persistent: bool = False,
        verify_ssl: bool = True,
        **kwargs,
    ):
        self.api_key = api_key or getenv("DAYTONA_API_KEY")
        if not self.api_key:
            raise ValueError("DAYTONA_API_KEY not set. Please set the DAYTONA_API_KEY environment variable.")

        self.api_url = api_url or getenv("DAYTONA_API_URL")
        self.sandbox_target_region = sandbox_target_region
        self.organization_id = organization_id
        self.sandbox_language = sandbox_language or CodeLanguage.PYTHON
        self.sandbox_os = sandbox_os
        self.sandbox_os_user = sandbox_os_user
        self.sandbox_env_vars = sandbox_env_vars
        self.sandbox_labels = sandbox_labels or {}
        self.sandbox_public = sandbox_public
        self.sandbox_auto_stop_interval = sandbox_auto_stop_interval
        self.timeout = timeout
        self.persistent = persistent
        self.requested_sandbox_id = sandbox_id
        self.verify_ssl = verify_ssl

        self.config = DaytonaConfig(
            api_key=self.api_key,
            api_url=self.api_url,
            target=self.sandbox_target_region,
            organization_id=self.organization_id,
            verify_ssl=self.verify_ssl,
        )
        self.daytona = Daytona(self.config)
        self.sandbox: Optional[Sandbox] = None
        self.last_execution: Optional[ExecuteResponse] = None

        tools: List[Any] = []

        if self.sandbox_language == CodeLanguage.PYTHON:
            tools.append(self.run_python_code)
        else:
            tools.append(self.run_code)

        tools.append(self.get_sandbox_info)

        super().__init__(name="daytona_tools", tools=tools, **kwargs)

        self._initialize_sandbox()

    def _initialize_sandbox(self) -> None:
        """Initialize sandbox - either reuse existing or create new one."""
        try:
            # Try to reuse specific sandbox if ID provided
            if self.requested_sandbox_id:
                try:
                    self.sandbox = self.daytona.get(self.requested_sandbox_id)
                    logger.info(f"Reusing specified sandbox: {self.requested_sandbox_id}")
                    if self.sandbox.state != "started":
                        logger.info(f"Starting sandbox {self.sandbox.id}")
                        self.sandbox.start()
                    return
                except Exception as e:
                    logger.warning(f"Could not reuse sandbox {self.requested_sandbox_id}: {e}")

            # Try to find and reuse existing sandbox in persistent mode
            if self.persistent:
                try:
                    sandboxes = self.daytona.list()

                    for sandbox in sandboxes:
                        if sandbox.state in ["started", "stopped"]:
                            if self.sandbox_language and sandbox.labels.get("language") != self.sandbox_language.value:
                                continue

                            self.sandbox = sandbox
                            logger.info(f"Reusing existing sandbox: {self.sandbox.id}")
                            if self.sandbox.state != "started":
                                logger.info(f"Starting sandbox {self.sandbox.id}")
                                self.sandbox.start()
                            return

                except Exception as e:
                    logger.warning(f"Error finding reusable sandbox: {e}")

            # Create new sandbox
            labels = {"language": self.sandbox_language.value}

            params = CreateSandboxFromSnapshotParams(
                language=self.sandbox_language,
                os_user=self.sandbox_os_user,
                env_vars=self.sandbox_env_vars,
                labels=labels,
                public=self.sandbox_public,
                auto_stop_interval=self.sandbox_auto_stop_interval,
            )

            self.sandbox = self.daytona.create(params, timeout=self.timeout)
            logger.info(f"Created new sandbox: {self.sandbox.id}")

        except Exception as e:
            logger.error(f"Error initializing Daytona sandbox: {e}")
            raise

    def run_python_code(self, code: str) -> str:
        """Execute Python code in the Daytona sandbox.

        Args:
            code: Python code to execute

        Returns:
            str: JSON string containing execution result or error

        For file operations, you can use standard Python:
        - List files: import os; print(os.listdir('.'))
        - Create files: with open('file.py', 'w') as f: f.write('content')
        - Read files: with open('file.py', 'r') as f: print(f.read())
        - Delete files: import os; os.remove('file.py')
        """
        try:
            if not self.sandbox:
                return json.dumps({"status": "error", "message": "No sandbox available"})

            executable_code = prepare_python_code(code)
            execution = self.sandbox.process.code_run(executable_code)
            self.last_execution = execution

            return json.dumps(
                {
                    "status": "success",
                    "result": execution.result,
                    "execution_time": getattr(execution, "execution_time", None),
                }
            )

        except Exception as e:
            error_msg = f"Error executing Python code: {str(e)}"
            logger.error(error_msg)
            return json.dumps({"status": "error", "message": error_msg})

    def run_code(self, code: str) -> str:
        """Execute general code in the Daytona sandbox.

        Args:
            code: Code to execute

        Returns:
            str: JSON string containing execution result or error

        For file operations, you can use standard shell commands:
        - List files: ls -la
        - Create files: echo 'content' > file.txt
        - Read files: cat file.txt
        - Delete files: rm file.txt
        """
        try:
            if not self.sandbox:
                return json.dumps({"status": "error", "message": "No sandbox available"})

            response = self.sandbox.process.code_run(code)
            self.last_execution = response

            return json.dumps(
                {
                    "status": "success",
                    "result": response.result,
                    "execution_time": getattr(response, "execution_time", None),
                }
            )

        except Exception as e:
            error_msg = f"Error executing code: {str(e)}"
            logger.error(error_msg)
            return json.dumps({"status": "error", "message": error_msg})

    def get_sandbox_info(self) -> str:
        """Get information about the current sandbox.

        Returns:
            str: JSON string containing sandbox information or error
        """
        try:
            if not self.sandbox:
                return json.dumps({"status": "error", "message": "No sandbox available"})

            self.sandbox.refresh_data()

            info = {
                "id": self.sandbox.id,
                "state": self.sandbox.state,
                "language": self.sandbox.labels.get("language", "unknown"),
                "user": self.sandbox.user,
                "cpu": self.sandbox.cpu,
                "memory": self.sandbox.memory,
                "disk": self.sandbox.disk,
                "created_at": self.sandbox.created_at,
                "labels": self.sandbox.labels,
                "root_dir": self.sandbox.get_user_root_dir(),
            }

            return json.dumps({"status": "success", "sandbox": info})

        except Exception as e:
            error_msg = f"Error getting sandbox info: {str(e)}"
            logger.error(error_msg)
            return json.dumps({"status": "error", "message": error_msg})
