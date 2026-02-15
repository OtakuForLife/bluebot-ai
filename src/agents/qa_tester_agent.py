"""QA Tester Agent for testing and quality assurance.

This agent is responsible for:
- Testing for bugs and glitches
- Verifying game balance and mechanics
- Ensuring game stability and performance
- Reporting issues and tracking fixes
"""

import logging
from pathlib import Path
from typing import Optional

from src.agents.base import Agent, Message, MessageType
from src.agents.knowledge_base import KnowledgeBase
from src.llm import BaseLLMProvider, LLMMessage
from src.llm.prompt_templates import QATesterPrompts


class QATesterAgent(Agent):
    """Agent specialized in quality assurance and testing.

    This agent handles all QA tasks including bug testing, balance verification,
    stability checks, and issue reporting. It uses a knowledge base loaded
    with testing methodologies and QA best practices.

    Attributes:
        knowledge_base: Knowledge base containing QA and testing documentation.
        project_path: Path to the Godot project being worked on.
        bug_reports: Dictionary storing bug reports and issues.
        test_results: Dictionary storing test execution results.
    """

    def __init__(
        self,
        name: str = "QATester",
        qa_docs_path: Optional[Path] = None,
        llm_provider: Optional[BaseLLMProvider] = None,
    ) -> None:
        """Initialize the QA Tester Agent.

        Args:
            name: Name for this agent instance.
            qa_docs_path: Optional path to QA documentation markdown files.
            llm_provider: Optional LLM provider for AI-powered test plan generation.
        """
        super().__init__(name=name, role="qa_tester")
        self.knowledge_base = KnowledgeBase(name="qa_docs")
        self.project_path: Optional[Path] = None
        self.bug_reports: dict[str, dict] = {}
        self.test_results: dict[str, dict] = {}
        self.llm_provider = llm_provider

        # Load QA documentation if path provided
        if qa_docs_path and qa_docs_path.exists():
            try:
                count = self.knowledge_base.load_from_directory(qa_docs_path)
                self.logger.info(f"Loaded {count} QA documentation files")
            except Exception as e:
                self.logger.error(f"Failed to load QA docs: {e}")

    async def process_message(self, message: Message) -> None:
        """Process incoming messages.

        Args:
            message: The message to process.
        """
        self.logger.debug(f"Processing message: {message.type.value}")

        if message.type == MessageType.TASK_REQUEST:
            await self._handle_task_request(message)
        elif message.type == MessageType.FILE_MODIFIED:
            await self._handle_file_modified(message)
        elif message.type == MessageType.TEST_RESULT:
            await self._handle_test_result(message)
        else:
            self.logger.debug(f"Ignoring message type: {message.type.value}")

    async def _handle_task_request(self, message: Message) -> None:
        """Handle a task request message.

        Args:
            message: The task request message.
        """
        task_type = message.payload.get("task_type")
        self.logger.info(f"Received task request: {task_type}")

        if task_type == "run_tests":
            await self._run_tests(message.payload)
        elif task_type == "report_bug":
            await self._report_bug(message.payload)
        elif task_type == "verify_fix":
            await self._verify_fix(message.payload)
        elif task_type == "test_balance":
            await self._test_balance(message.payload)
        else:
            self.logger.warning(f"Unknown task type: {task_type}")

    async def _handle_file_modified(self, message: Message) -> None:
        """Handle notification that a file was modified - trigger retesting.

        Args:
            message: The file modified message.
        """
        file_path = message.payload.get("file_path")
        self.logger.info(f"File modified, scheduling retest: {file_path}")
        # Could trigger automatic regression testing here

    async def _handle_test_result(self, message: Message) -> None:
        """Handle test results from test execution.

        Args:
            message: The test result message.
        """
        test_id = message.payload.get("test_id", "unknown")
        passed = message.payload.get("passed", False)
        errors = message.payload.get("errors", [])
        
        self.logger.info(f"Test {test_id}: {'PASSED' if passed else 'FAILED'}")
        
        # Store test results
        self.test_results[test_id] = {
            "passed": passed,
            "errors": errors,
            "payload": message.payload,
        }

    async def _run_tests(self, payload: dict) -> None:
        """Run automated tests on the game.

        Args:
            payload: Task payload with test execution details.
        """
        test_suite = payload.get("test_suite", "all")
        self.logger.info(f"Running test suite: {test_suite}")
        
        # Search knowledge base for testing strategies
        test_docs = self.knowledge_base.search("testing")
        self.logger.debug(f"Found {len(test_docs)} relevant docs")
        
        # Simulate test execution
        test_id = f"test_{test_suite}"
        self.test_results[test_id] = {
            "suite": test_suite,
            "status": "running",
            "payload": payload,
        }

    async def _report_bug(self, payload: dict) -> None:
        """Report a bug or issue.

        Args:
            payload: Task payload with bug details.
        """
        bug_id = payload.get("bug_id", "unknown")
        severity = payload.get("severity", "medium")
        description = payload.get("description", "")
        
        self.logger.info(f"Reporting bug {bug_id} (severity: {severity})")
        
        # Search knowledge base for bug reporting best practices
        bug_docs = self.knowledge_base.search("bug report")
        self.logger.debug(f"Found {len(bug_docs)} relevant docs")
        
        # Store the bug report
        self.bug_reports[bug_id] = {
            "severity": severity,
            "description": description,
            "status": "reported",
            "payload": payload,
        }

    async def _verify_fix(self, payload: dict) -> None:
        """Verify that a bug fix works correctly.

        Args:
            payload: Task payload with fix verification details.
        """
        bug_id = payload.get("bug_id", "unknown")
        self.logger.info(f"Verifying fix for bug: {bug_id}")
        
        # Search knowledge base for verification techniques
        verify_docs = self.knowledge_base.search("verification")
        self.logger.debug(f"Found {len(verify_docs)} relevant docs")
        
        # Update bug report if it exists
        if bug_id in self.bug_reports:
            self.bug_reports[bug_id]["status"] = "verified"

    async def _test_balance(self, payload: dict) -> None:
        """Test game balance and mechanics.

        Args:
            payload: Task payload with balance testing details.
        """
        system_name = payload.get("system", "general")
        self.logger.info(f"Testing balance for: {system_name}")
        
        # Search knowledge base for balance testing techniques
        balance_docs = self.knowledge_base.search("balance testing")
        self.logger.debug(f"Found {len(balance_docs)} relevant docs")

    def set_project_path(self, path: Path) -> None:
        """Set the Godot project path.

        Args:
            path: Path to the Godot project directory.
        """
        self.project_path = path
        self.logger.info(f"Project path set to: {path}")

    def get_knowledge_summary(self) -> dict:
        """Get a summary of the loaded knowledge base.

        Returns:
            Dictionary with knowledge base statistics.
        """
        return self.knowledge_base.get_summary()

    def get_bug_reports(self) -> dict[str, dict]:
        """Get all bug reports.

        Returns:
            Dictionary of bug reports.
        """
        return self.bug_reports.copy()

    def get_test_results(self) -> dict[str, dict]:
        """Get all test results.

        Returns:
            Dictionary of test results.
        """
        return self.test_results.copy()

