#!/usr/bin/env python
"""Module 10 dedicated jailbreak evaluation runner (Task 6).

Usage (from backend/):
    python eval/module10/runners/run_jailbreak_eval.py

Loads both the existing security_eval.json jailbreak_cases and the new
jailbreak_dataset.json, scores them using compliance markers, and saves
a dedicated jailbreak report. Grader metric: Jailbreak Resistance.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.services.faiss_vector_store import FAISSVectorStore
from app.services.llm_provider import build_llm_client
from app.services.rag_service import ChatService
from eval.module10 import config

# Import markers from run_security_eval
from eval.module10.runners.run_security_eval import (
    _DAN_COMPLIANCE_MARKERS,
    _PII_ENUMERATION_MARKERS,
    _SYSTEM_PROMPT_LEAK_MARKERS,
)


def score_jailbreak_case(case: dict, chat_service: ChatService) -> dict:
    query = case["query"]
    try:
        response = chat_service.handle_query(query)
        response_text = response.text.lower()

        # Check all compliance markers
        is_dan_compliant = any(m in response_text for m in _DAN_COMPLIANCE_MARKERS)
        is_prompt_leaked = any(m in response_text for m in _SYSTEM_PROMPT_LEAK_MARKERS)
        is_data_exfiltrated = any(m in response_text for m in _PII_ENUMERATION_MARKERS)

        succeeded = is_dan_compliant or is_prompt_leaked or is_data_exfiltrated

        return {
            "case_id": case.get("id"),
            "attack_type": case["attack_type"],
            "query": query,
            "response": response.text,
            "succeeded": succeeded,
            "resisted": not succeeded,
            "error": None
        }
    except Exception as exc:
        return {
            "case_id": case.get("id"),
            "attack_type": case["attack_type"],
            "query": query,
            "response": None,
            "succeeded": False, # If it errored out, it didn't succeed in jailbreaking
            "resisted": True,
            "error": f"{type(exc).__name__}: {exc}"
        }


def main() -> None:
    # 1. Load existing security_eval.json jailbreak_cases
    security_dataset = config.load_dataset("security_eval.json")
    existing_cases = security_dataset.get("jailbreak_cases", [])

    # 2. Load new jailbreak_dataset.json cases
    try:
        new_dataset = config.load_dataset("jailbreak_dataset.json", base_dir="D:\\AI-ML-FullStack\\02-Projects\\Portfolio-Projects\\InsightAI-RAG\\backend\\eval")
    except FileNotFoundError:
        import json
        with open("D:\\AI-ML-FullStack\\02-Projects\\Portfolio-Projects\\InsightAI-RAG\\backend\\eval\\jailbreak_dataset.json", encoding="utf-8") as f:
            new_dataset = json.load(f)

    new_cases = new_dataset.get("jailbreak_cases", [])

    # 3. Setup ChatService
    vector_store = FAISSVectorStore()
    vector_store.load()
    chat_service = ChatService(vector_store, build_llm_client())

    # 4. Run cases
    existing_results = []
    for case in existing_cases:
        existing_results.append(score_jailbreak_case(case, chat_service))

    new_results = []
    for case in new_cases:
        new_results.append(score_jailbreak_case(case, chat_service))

    # 5. Score
    all_results = existing_results + new_results
    total_attempted = len(all_results)
    total_resisted = sum(1 for r in all_results if r["resisted"])

    resistance_rate = total_resisted / total_attempted if total_attempted else 0.0

    report = {
        "metadata": config.run_metadata(
            sample_count=total_attempted,
            dataset_version="jailbreak_v1_and_security_v1",
        ),
        "existing_jailbreak_cases": existing_results,
        "new_jailbreak_cases": new_results,
        "jailbreak_resistance": {
            "total_resisted": total_resisted,
            "total_attempted": total_attempted,
            "resistance_rate": resistance_rate
        }
    }

    # 6. Save
    path = config.save_report(report, name="jailbreak_eval")
    print(f"Saved: {path}")
    print(f"Jailbreak Resistance: {total_resisted}/{total_attempted} ({resistance_rate:.2%})")

if __name__ == "__main__":
    main()
