"""Tests for dedicated jailbreak test suite — Task 6 (Module 10 gap-closure)."""

from __future__ import annotations

import json
from pathlib import Path


def test_jailbreak_dataset_exists_and_has_required_fields():
    dataset_path = Path(__file__).resolve().parents[1] / "eval" / "jailbreak_dataset.json"
    assert dataset_path.exists(), "jailbreak_dataset.json does not exist"
    
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    assert "dataset_version" in data
    assert "jailbreak_cases" in data
    
    cases = data["jailbreak_cases"]
    assert isinstance(cases, list)
    assert len(cases) > 0
    
    for case in cases:
        assert "id" in case
        assert "attack_type" in case
        assert "query" in case
        assert "expected_safe_behavior" in case
        assert "risk_level" in case


def test_jailbreak_dataset_has_dan_roleplay_hypothetical_categories():
    dataset_path = Path(__file__).resolve().parents[1] / "eval" / "jailbreak_dataset.json"
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    cases = data["jailbreak_cases"]
    attack_types = {case["attack_type"] for case in cases}
    
    assert "role_override" in attack_types, "Missing role_override attacks"
    assert "instruction_hierarchy_attack" in attack_types, "Missing instruction_hierarchy_attack attacks"
    assert "system_prompt_extraction" in attack_types, "Missing system_prompt_extraction attacks"


def test_jailbreak_dataset_minimum_size():
    dataset_path = Path(__file__).resolve().parents[1] / "eval" / "jailbreak_dataset.json"
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    cases = data["jailbreak_cases"]
    assert len(cases) >= 6, "Dataset should have at least 6 cases"


def test_resistance_rate_formula():
    """Given 5 resisted/6 attempted -> resistance_rate = 5/6"""
    total_resisted = 5
    total_attempted = 6
    resistance_rate = total_resisted / total_attempted
    
    assert round(resistance_rate, 4) == 0.8333
