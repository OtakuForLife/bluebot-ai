"""Tests for the QA Tester Agent."""

import asyncio
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from src.agents.base import AgentStatus, Message, MessageType
from src.agents.qa_tester_agent import QATesterAgent


@pytest.mark.asyncio
async def test_qa_tester_agent_initialization() -> None:
    """Test that the agent initializes correctly."""
    agent = QATesterAgent()

    assert agent.name == "QATester"
    assert agent.role == "qa_tester"
    assert agent.status == AgentStatus.IDLE
    assert agent.knowledge_base is not None
    assert agent.project_path is None
    assert len(agent.bug_reports) == 0
    assert len(agent.test_results) == 0


@pytest.mark.asyncio
async def test_run_tests() -> None:
    """Test running automated tests."""
    agent = QATesterAgent()

    # Start the agent
    agent_task = asyncio.create_task(agent.start())
    await asyncio.sleep(0.1)

    # Send a run tests request
    message = Message(
        id=uuid4(),
        type=MessageType.TASK_REQUEST,
        sender_id=uuid4(),
        recipient_id=agent.id,
        payload={"task_type": "run_tests", "test_suite": "gameplay"},
    )

    await agent.receive_message(message)
    await asyncio.sleep(0.2)

    # Check that the test was recorded
    results = agent.get_test_results()
    assert "test_gameplay" in results
    assert results["test_gameplay"]["suite"] == "gameplay"

    # Clean up
    await agent.stop()
    agent_task.cancel()
    try:
        await agent_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_report_bug() -> None:
    """Test reporting a bug."""
    agent = QATesterAgent()

    # Start the agent
    agent_task = asyncio.create_task(agent.start())
    await asyncio.sleep(0.1)

    # Send a report bug request
    message = Message(
        id=uuid4(),
        type=MessageType.TASK_REQUEST,
        sender_id=uuid4(),
        recipient_id=agent.id,
        payload={
            "task_type": "report_bug",
            "bug_id": "BUG-001",
            "severity": "high",
            "description": "Player falls through floor",
        },
    )

    await agent.receive_message(message)
    await asyncio.sleep(0.2)

    # Check that the bug was reported
    bugs = agent.get_bug_reports()
    assert "BUG-001" in bugs
    assert bugs["BUG-001"]["severity"] == "high"
    assert bugs["BUG-001"]["status"] == "reported"

    # Clean up
    await agent.stop()
    agent_task.cancel()
    try:
        await agent_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_verify_fix() -> None:
    """Test verifying a bug fix."""
    agent = QATesterAgent()

    # First create a bug report
    agent.bug_reports["BUG-001"] = {
        "severity": "high",
        "description": "Test bug",
        "status": "reported",
    }

    # Start the agent
    agent_task = asyncio.create_task(agent.start())
    await asyncio.sleep(0.1)

    # Send a verify fix request
    message = Message(
        id=uuid4(),
        type=MessageType.TASK_REQUEST,
        sender_id=uuid4(),
        recipient_id=agent.id,
        payload={"task_type": "verify_fix", "bug_id": "BUG-001"},
    )

    await agent.receive_message(message)
    await asyncio.sleep(0.2)

    # Check that the bug status was updated
    bugs = agent.get_bug_reports()
    assert bugs["BUG-001"]["status"] == "verified"

    # Clean up
    await agent.stop()
    agent_task.cancel()
    try:
        await agent_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_handle_test_result() -> None:
    """Test handling test results."""
    agent = QATesterAgent()

    # Start the agent
    agent_task = asyncio.create_task(agent.start())
    await asyncio.sleep(0.1)

    # Send a test result message
    message = Message(
        id=uuid4(),
        type=MessageType.TEST_RESULT,
        sender_id=uuid4(),
        recipient_id=agent.id,
        payload={
            "test_id": "test_001",
            "passed": False,
            "errors": ["Error 1", "Error 2"],
        },
    )

    await agent.receive_message(message)
    await asyncio.sleep(0.2)

    # Check that the test result was stored
    results = agent.get_test_results()
    assert "test_001" in results
    assert results["test_001"]["passed"] is False
    assert len(results["test_001"]["errors"]) == 2

    # Clean up
    await agent.stop()
    agent_task.cancel()
    try:
        await agent_task
    except asyncio.CancelledError:
        pass

