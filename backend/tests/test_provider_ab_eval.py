"""Regression tests for the Module 10 provider A-B evaluation harness
(eval/module10/runners/run_provider_ab_eval.py).

These do NOT re-run the live evaluation (that requires real Groq/Gemini
API calls and is intentionally not part of the offline test suite).
They guard the parts of the harness that would silently corrupt a real
run if they regressed:
- provider/model selection actually flips Settings.llm_provider
- both configurations run under the same frozen evaluation contract
  (same dataset, same disabled-fallback/routing settings)
- fallback/routing settings are restored after the script runs, so the
  evaluation never leaves the process's real configuration mutated
- the response cache is cleared between legs, since it is not
  provider-aware and would otherwise silently serve configuration A's
  cached answers back for configuration B (the exact bug this test
  suite exists to prevent a silent regression of -- caught empirically
  on this harness's first live run: see run_provider_ab_eval.py's
  run_configuration() docstring/comment).
"""

from unittest.mock import MagicMock, patch

from app.core.config import settings
from eval.module10.runners.run_provider_ab_eval import CONFIGS, run_configuration


class _FakeChunk:
    def __init__(self, text: str):
        self.text = text
        self.metadata = {"text": text}


def _make_fake_response(answer: str):
    from app.models.schemas import ChatResponse

    return ChatResponse(
        answer=answer,
        retrieved_chunks=[],
        sources=[],
        processing_time=0.01,
        tool_used="retrieval",
        steps_taken=2,
        session_id="s1",
    )


class TestConfigurationSelection:
    def test_config_a_and_b_use_distinct_documented_providers(self):
        assert CONFIGS["A"]["llm_provider"] != CONFIGS["B"]["llm_provider"]
        assert {CONFIGS["A"]["llm_provider"], CONFIGS["B"]["llm_provider"]} == {"groq", "gemini"}

    def test_run_configuration_sets_settings_llm_provider(self, monkeypatch):
        seen_providers = []

        def fake_build_llm_client():
            seen_providers.append(settings.llm_provider)
            return MagicMock()

        with patch(
            "eval.module10.runners.run_provider_ab_eval.run_evaluation",
            return_value=MagicMock(
                item_results=[],
                mean_faithfulness=0.5,
                mean_context_recall=0.5,
                mean_context_precision=0.5,
                mean_answer_relevance=0.5,
                mean_composite_score=0.5,
                mean_latency_sec=1.0,
            ),
        ), patch(
            "app.services.faiss_vector_store.FAISSVectorStore"
        ) as mock_store_cls, patch(
            "app.services.llm_provider.build_llm_client", side_effect=fake_build_llm_client
        ), patch(
            "eval.module10.runners.run_provider_ab_eval.discover_document_id", return_value="doc-1"
        ), patch(
            "eval.module10.runners.run_provider_ab_eval._run_planner_and_planning_legs",
            return_value={
                "planner_classification": {},
                "planning": {},
                "tool_selection_accuracy": None,
                "planning_success_rate": None,
                "average_steps": None,
                "loop_rate": None,
            },
        ):
            mock_store_cls.return_value.load.return_value = None
            run_configuration("A")
            run_configuration("B")

        assert seen_providers == ["groq", "gemini"]


class TestFallbackAndRoutingDisabledDuringEvaluation:
    def test_run_configuration_disables_fallback_and_routing(self, monkeypatch):
        monkeypatch.setattr(settings, "fallback_llm_provider", "gemini")
        monkeypatch.setattr(settings, "model_routing_enabled", True)

        with patch(
            "eval.module10.runners.run_provider_ab_eval.run_evaluation",
            return_value=MagicMock(
                item_results=[],
                mean_faithfulness=0.5,
                mean_context_recall=0.5,
                mean_context_precision=0.5,
                mean_answer_relevance=0.5,
                mean_composite_score=0.5,
                mean_latency_sec=1.0,
            ),
        ), patch("app.services.faiss_vector_store.FAISSVectorStore") as mock_store_cls, patch(
            "app.services.llm_provider.build_llm_client", return_value=MagicMock()
        ), patch(
            "eval.module10.runners.run_provider_ab_eval.discover_document_id", return_value="doc-1"
        ), patch(
            "eval.module10.runners.run_provider_ab_eval._run_planner_and_planning_legs",
            return_value={
                "planner_classification": {},
                "planning": {},
                "tool_selection_accuracy": None,
                "planning_success_rate": None,
                "average_steps": None,
                "loop_rate": None,
            },
        ):
            mock_store_cls.return_value.load.return_value = None
            result = run_configuration("A")

        assert result["configuration"]["fallback_llm_provider"] is None
        assert result["configuration"]["fallback_disabled_for_this_evaluation"] is True
        assert result["configuration"]["model_routing_enabled"] is False
        assert settings.fallback_llm_provider is None  # actually mutated on settings, not just reported
        assert settings.model_routing_enabled is False


class TestResponseCacheIsolation:
    def test_cache_is_cleared_at_the_start_of_each_configuration_run(self):
        """The exact bug this evaluation hit on its first live run: the
        response cache is a process-wide singleton not keyed by provider,
        so without an explicit clear, configuration B would silently be
        served configuration A's cached answers."""
        with patch("eval.module10.runners.run_provider_ab_eval.cache_service") as mock_cache, patch(
            "eval.module10.runners.run_provider_ab_eval.run_evaluation",
            return_value=MagicMock(
                item_results=[],
                mean_faithfulness=0.5,
                mean_context_recall=0.5,
                mean_context_precision=0.5,
                mean_answer_relevance=0.5,
                mean_composite_score=0.5,
                mean_latency_sec=1.0,
            ),
        ), patch("app.services.faiss_vector_store.FAISSVectorStore") as mock_store_cls, patch(
            "app.services.llm_provider.build_llm_client", return_value=MagicMock()
        ), patch(
            "eval.module10.runners.run_provider_ab_eval.discover_document_id", return_value="doc-1"
        ), patch(
            "eval.module10.runners.run_provider_ab_eval._run_planner_and_planning_legs",
            return_value={
                "planner_classification": {},
                "planning": {},
                "tool_selection_accuracy": None,
                "planning_success_rate": None,
                "average_steps": None,
                "loop_rate": None,
            },
        ):
            mock_store_cls.return_value.load.return_value = None
            run_configuration("A")
            run_configuration("B")

        assert mock_cache.clear.call_count == 2


class TestFrozenEvaluationContract:
    def test_both_configurations_use_the_same_golden_dataset(self):
        import inspect

        from eval.module10.runners import run_provider_ab_eval as mod

        source = inspect.getsource(mod._run_rag_leg)
        # Both legs go through the same run_evaluation(dataset=GOLDEN_DATASET, ...)
        # call inside _run_rag_leg -- there is exactly one dataset reference,
        # not a per-configuration dataset branch.
        assert "GOLDEN_DATASET" in source
        assert source.count("dataset=GOLDEN_DATASET") == 1


class TestClassifyAnswer:
    def test_classifies_generation_error_reply(self):
        from app.services.prompt_builder import GENERATION_ERROR_REPLY
        from eval.module10.runners.run_provider_ab_eval import _classify_answer

        assert _classify_answer(GENERATION_ERROR_REPLY) == "provider_generation_error"

    def test_classifies_fallback_reply(self):
        from app.services.prompt_builder import FALLBACK_REPLY
        from eval.module10.runners.run_provider_ab_eval import _classify_answer

        assert _classify_answer(FALLBACK_REPLY) == "not_in_documents_fallback"

    def test_classifies_real_answer(self):
        from eval.module10.runners.run_provider_ab_eval import _classify_answer

        assert _classify_answer("Sulfur fungicide treats apple scab [1].") == "real_generated_answer"
