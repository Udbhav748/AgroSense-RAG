"""Tests for tool argument expansion — Task 7 (Module 10 gap-closure)."""

from __future__ import annotations

import json
from pathlib import Path

from eval.module10.metrics import agent as ametrics


def test_new_tool_argument_cases_exist_in_dataset():
    dataset_path = Path(__file__).resolve().parents[1] / "eval" / "module10" / "datasets" / "agent_eval.json"
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    tool_arg_cases = data.get("tool_argument_cases", [])
    case_ids = {c["id"] for c in tool_arg_cases}
    
    assert "agent_arg_010" in case_ids
    assert "agent_arg_011" in case_ids


def test_new_cases_score_correctly():
    """Verify tool_argument_accuracy logic handles the new cases."""
    cases = [
        ametrics.ToolArgCase(
            case_id="agent_arg_010",
            tool="conversational",
            expected="conversational",
            actual="conversational",
            applicable=True
        ),
        ametrics.ToolArgCase(
            case_id="agent_arg_011",
            tool="retrieve",
            expected="apple",
            actual="apple",
            applicable=True
        )
    ]
    
    report = ametrics.tool_argument_accuracy(cases)
    
    assert report["tool_argument_accuracy"] == 1.0
    assert report["n_applicable"] == 2
    assert "conversational" in report["per_tool"]
    assert "retrieve" in report["per_tool"]
    assert report["per_tool"]["conversational"] == 1.0
    assert report["per_tool"]["retrieve"] == 1.0
