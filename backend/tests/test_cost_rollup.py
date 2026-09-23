"""Tests for cost-per-successful-task log rollup — Task 5 (Module 10 gap-closure)."""

from __future__ import annotations

import json
from pathlib import Path

from eval.metrics_report import rollup_cost_per_successful_task


def test_rollup_with_synthetic_log(tmp_path: Path):
    """Test standard rollup behavior with a mix of cost and no-cost records."""
    log_file = tmp_path / "test.log"
    lines = [
        json.dumps({"message": "chat_query_handled", "estimated_cost_usd": 0.001, "steps_taken": 2}),
        json.dumps({"message": "chat_query_handled", "estimated_cost_usd": 0.002, "steps_taken": 3}),
        json.dumps({"message": "chat_query_handled"}),  # no cost
        json.dumps({"message": "some_other_event"}),
    ]
    log_file.write_text("\n".join(lines), encoding="utf-8")

    result = rollup_cost_per_successful_task(log_file)
    assert result["successful_tasks"] == 2
    assert result["total_cost_usd"] == 0.003
    assert result["cost_per_successful_task_usd"] == 0.0015
    assert result["n_with_cost"] == 2
    assert result["n_total_log_entries"] == 4
    assert result["note"] == "Success"


def test_rollup_empty_log(tmp_path: Path):
    """Test behavior with an empty log file."""
    log_file = tmp_path / "empty.log"
    log_file.write_text("", encoding="utf-8")

    result = rollup_cost_per_successful_task(log_file)
    assert result["cost_per_successful_task_usd"] is None
    assert "No chat_query_handled entries" in result["note"]


def test_rollup_no_chat_handled_lines(tmp_path: Path):
    """Test behavior when no chat_query_handled lines are present."""
    log_file = tmp_path / "other.log"
    lines = [
        json.dumps({"message": "some_other_event"}),
        json.dumps({"message": "llm_generation_completed"}),
    ]
    log_file.write_text("\n".join(lines), encoding="utf-8")

    result = rollup_cost_per_successful_task(log_file)
    assert result["cost_per_successful_task_usd"] is None
    assert "No chat_query_handled entries" in result["note"]


def test_rollup_cost_formula(tmp_path: Path):
    """Test the exact cost computation and criteria for 'successful'."""
    log_file = tmp_path / "test_formula.log"
    lines = [
        # Successful: cost >= 0 and steps > 0
        json.dumps({"message": "chat_query_handled", "estimated_cost_usd": 0.001, "steps_taken": 1}),
        json.dumps({"message": "chat_query_handled", "estimated_cost_usd": 0.002, "steps_taken": 5}),
        json.dumps({"message": "chat_query_handled", "estimated_cost_usd": 0.003, "steps_taken": 2}),
        
        # Not successful: steps = 0
        json.dumps({"message": "chat_query_handled", "estimated_cost_usd": 0.005, "steps_taken": 0}),
        
        # Not successful: cost < 0 (error case)
        json.dumps({"message": "chat_query_handled", "estimated_cost_usd": -1.0, "steps_taken": 3}),
    ]
    log_file.write_text("\n".join(lines), encoding="utf-8")

    result = rollup_cost_per_successful_task(log_file)
    
    # Only 3 successful tasks
    assert result["successful_tasks"] == 3
    # Total cost of successful tasks: 0.001 + 0.002 + 0.003 = 0.006
    assert result["total_cost_usd"] == 0.006
    # Cost per successful task: 0.006 / 3 = 0.002
    assert result["cost_per_successful_task_usd"] == 0.002
    # Total chat_query_handled lines with estimated_cost_usd (including negative)
    assert result["n_with_cost"] == 5
