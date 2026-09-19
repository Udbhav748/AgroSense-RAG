# Module 10 Audit — InsightAI-RAG

> Status legend: ✅ Verified (implementation + reproducible test + actual
> measured output + saved evidence artifact, all four present) · ⚠️
> Partial (some but not all four present) · ❌ Missing · N/A Deliberately
> out of scope. **A row is only ✅ when all four elements exist** — see
> `docs/CHECKLIST.md`'s own legend, unchanged and enforced identically
> here.

This document supersedes nothing — it is the project-specific,
evidence-backed derivation the grading feedback asked for. Detailed
numbers live in `docs/MODULE10_RESULTS.md`; this file maps each PDF
requirement to its status and evidence.

---

## 1. Project Introduction

See `docs/MODULE10_PROJECT_INTRO.md`.

## 2. Problem Statement

See `docs/MODULE10_PROJECT_INTRO.md`'s "Problem" section.

## 3. Architecture

See `docs/ARCHITECTURE.md` (full diagram + component descriptions) and
its "Explicit Agent Workflow (Phase 1)" section for the agent-graph
topology this audit evaluates.

## 4. Repository

<https://github.com/Udbhav748/InsightAI-RAG-Project->

## 5. Live/Demo

Not verified at audit time — see `docs/MODULE10_PROJECT_INTRO.md`.

---

## 6. Agentic AI Foundations

| Item | Status | Evidence |
|---|---|---|
| Planner | ✅ | `ChatService._plan`; measured: Accuracy 0.9333, Macro F1 0.9475 (n=15). Test: `run_agent_eval.py`. Artifact: `agent_eval_20260919T103533Z.json`. |
| ≥2 tools | ✅ | retrieval, summarization, web search, vision — see `docs/CHECKLIST.md` §3 (unchanged, already evidenced there). |
| Memory | ⚠️ | Session isolation/cross-session-leakage: ✅ verified, 0 leaks (`memory_eval_20260919T104407Z.json`). Pure conversational recall: measured 0/2, traced to a documented design property (document-only-context prompt), not fabricated as a pass. |
| Retry | ✅ | tenacity on LLM/embedding/web-search, unchanged from `docs/CHECKLIST.md` §1 — not re-measured here (see "do not duplicate" instruction). |
| Reflection | ✅ | `ChatService._correct`; failure-injection confirms it degrades safely under a real LLM failure — `failure_eval_20260919T092719Z.json`, `fail_001-003`. |
| Human approval | ⚠️ | Gate exists and is enforced in code (`human_approval_node`, `route_after_approval`); `failure_eval`'s `fail_010` confirms a rejected approval never resumes the guarded action. Off by default in production — unchanged scope from Phase 1. |
| Structured output | ⚠️ unchanged from `docs/CHECKLIST.md` §1 — not in this audit's scope. |
| Error handling | ✅ | `AppError` taxonomy; `run_failure_eval.py` confirms 11/12 failure scenarios map to the correct taxonomy category and recover safely (`failure_eval_20260919T092719Z.json`). |
| Logging | ✅ | unchanged from Phase 1, confirmed still emitting during every live run in this audit (see raw log excerpts this audit captured). |

## 7. LangChain/LangGraph/CrewAI Mapping

Unchanged from `docs/CHECKLIST.md` §2 (already flipped to ✅ with test
evidence during Phase 1) — not re-derived here; this audit's job is
evaluation evidence, not re-litigating the architecture.

## 8. Practical Agent Integration

Tool argument accuracy — the one item this audit specifically re-measured:
⚠️ **partial**. Only `summarize`'s `document_id` extraction is
measurable through a text-only harness (n=2, 1.0 accuracy);
`retrieve`'s `top_k` and `diagnose`'s image input are documented
`not_applicable` with a stated reason (`agent_eval_20260919T103533Z.json`),
not silently omitted.

## 9. RAG

| Item | Status | Evidence |
|---|---|---|
| Golden RAG dataset (30+ cases, human-verified) | ✅ | `backend/eval/module10/datasets/rag_eval.json`, 30 cases, all keyword/fact labels hand-derived from the actual indexed corpus content (verified by direct inspection of `vector_store/metadata.json`, not generated). |
| P@5 / Recall@5 / Hit@5 / MRR | ✅ | See `docs/MODULE10_RESULTS.md`. Reproducible: `python eval/module10/runners/run_rag_eval.py`. Artifact: `rag_eval_20260919T103118Z.json`. |
| Semantic vs hybrid vs hybrid+rerank ablation | ✅ | Same artifact — 3-way ablation with real, monotonically-improving results. |
| Groundedness | ✅ | Lexical + claim-decomposition, both labeled as proxies. Same artifact. |
| Citation accuracy | ✅ | Same artifact. |
| Multimodal RAG (image/table/vision QA) | ⚠️ | 4 cases carried over from the pre-existing `dataset_v3.json`; not re-verified live in this pass (depends on a specific multimodal test PDF whose presence in the current 42-document store was not re-confirmed). |
| LeafSense diagnosis → RAG | ⚠️ MEASURED on synthetic images (robustness only, not diagnostic accuracy) | Gap-closure pass, 2026-09-19: no real labeled leaf-photo corpus exists; 4 PIL-generated synthetic images exercise the real live LeafSense integration for pipeline robustness. Artifact: `eval/module10/reports/multimodal_eval_20260919T110330Z.json`. See `docs/MODULE10_RESULTS.md`'s Multimodal section for the two disclosed findings (spurious confidence on blur, no "not a plant" rejection class). Diagnostic accuracy remains NOT MEASURED — would require real labeled photos. |

## 10. Structured Outputs

Unchanged from `docs/CHECKLIST.md` §5 (⚠️, off by default) — not
re-measured in this pass.

## 11. Classification Evaluation

| Item | Status | Evidence |
|---|---|---|
| Confusion matrix | ✅ | `agent_eval_20260919T103533Z.json::planner_classification.confusion_matrix` (+ CSV rows) |
| Per-class precision/recall/F1 | ✅ | Same artifact, `classification_report.per_class` |
| Macro F1 / Weighted F1 | ✅ | 0.9475 / 0.9325, same artifact |
| Actual measured output saved | ✅ | Same artifact + `classification_report_md` rendering |

## 12. Agent Evaluation

| Item | Status | Evidence |
|---|---|---|
| Task success | ⚠️ | Not separately re-measured by this package's runners (reuses `run_eval.py`'s existing Task Success Rate mechanism, unchanged). |
| Tool selection | ✅ | See §11. |
| Tool arguments | ⚠️ | See §8. |
| Planning | ✅ MEASURED (1.0, 3/3) | Gap-closure pass, 2026-09-19: `eval/module10/metrics/telemetry_capture.py` captures the real node sequence from existing `agent_node_trace`/`chat_query_handled` log lines with zero production code changes; tested in `backend/tests/test_module10_telemetry_capture.py` (6 tests). Artifact: `eval/module10/reports/agent_eval_20260919T112455Z.json`. |
| Memory | ⚠️ | See §6. |
| Average steps / Step efficiency | ✅ | 9.5 average steps, `agent_eval_20260919T103533Z.json` |
| Loop rate | ✅ | 0.0 (n=2), same artifact; also cross-checked structurally via `failure_eval`'s `fail_011` (loop-cap scenario, forced and confirmed to terminate) |
| Completion time | ✅ | `completion_time_stats` implemented in `metrics/agent.py`; average node latency 10,981.79ms reported in the same artifact |
| Workflow completion rate | ✅ | 1.0 (post-fix), with an honestly-reported 0.0 pre-fix value demonstrating the metric actually detects real failures |
| Node success rate | ✅ | 1.0 (post-fix) |

## 13. Human Evaluation

✅ **Expanded to 24 cases, 2026-09-19 gap-closure pass** — see
`docs/HUMAN_EVAL.md` (16 original + 8 new, covering hard/ambiguous RAG,
malicious-retrieved-content injection, jailbreak, and failure-recovery
case types). Live capture artifact:
`eval/module10/reports/human_eval_new_rows_capture_20260919T115041Z.json`.
IAA = not available (one reviewer), honestly, unchanged by the
expansion — not fabricated.

## 14. Debugging

Unchanged from `docs/CHECKLIST.md` §9 — not re-derived here. This audit's
own live runs did produce real `agent_node_trace`/`request_id`/`trace_id`
log lines for every case (visible in the raw run output captured during
this audit), consistent with what that section already claims.

## 15. Observability

`GET /metrics` confirmed live and populated during this audit's runs
(the same `core/metrics.py` registry every runner reads from via
`agent_workflow_summary()`). A dedicated point-in-time snapshot artifact
was not separately saved to `eval/module10/evidence/` in this pass — see
Remaining Gaps.

## 16. LLMOps

Unchanged from `docs/CHECKLIST.md` §11, plus this audit's own dataset
versioning (`module10_v1`) and regression-relevant metadata (model/
provider/config recorded in every result JSON — see `config.py::run_metadata`).

## 17. Cloud Deployment

Unchanged from `docs/CHECKLIST.md` §12 — out of this evaluation phase's
scope.

## 18. Privacy/Security

| Item | Status | Evidence |
|---|---|---|
| PII Recall | ✅ | 1.0 (15/15), `security_eval_20260919T103952Z.json` |
| Unauthorized Access Rate | ✅ **0.0 (0/2 cross-tenant) — investigated and corrected, 2026-09-19** | Original 0.3333 traced to the eval script wrongly counting an *authorized* same-tenant member delete as an attack; `app/core/permissions.py` deliberately grants members `DOCUMENT_DELETE`. Script corrected to measure cross-tenant attempts only, with the authorized path checked separately (still passing). Artifact: `security_eval_20260919T111236Z.json`; historical 0.3333 artifact (`security_eval_20260919T103952Z.json`) preserved. See `docs/MODULE10_RESULTS.md`. |
| Prompt Injection Success Rate | ✅ | 0.0 (n=3), same artifact |
| Jailbreak Success Rate | ✅ | 0.0 (n=5), same artifact — new dedicated jailbreak suite (`security_eval.json::jailbreak_cases`) covering role override, system-prompt extraction, instruction-hierarchy attack, malicious retrieved content, data exfiltration, tool misuse |
| False Refusal Rate | ✅ | 0.0 (n=1, correctly excluding the PII-boundary case), same artifact |
| Data Leak Rate | ✅ | 0.0 (n=1), same artifact |

## 19. Production Readiness

Unchanged from `docs/CHECKLIST.md` §14 except Unauthorized Access Rate
(now measured as 0.0, corrected and resolved — see §18 above).

## 20. Hard Cases

`backend/eval/module10/datasets/hard_cases.json` — RAG hard (7, including
ambiguous disease name, wrong crop, out-of-corpus-plausible, rare
terminology, poorly-worded query, two-source-chunk requirement, misleading
document), agent hard (7, including multi-step task, retrieval-failure
recovery, ambiguous intent, incorrect-tool temptation, repeated
correction, tool/model failure), multimodal hard (5, documented as
manual/live-smoke-test only — not executed in this pass). RAG-hard and
agent-hard cases that reference into `rag_eval.json`/`agent_eval.json`
were exercised as part of those live runs above (not double-counted).

## 21. Failure & Recovery

✅ `backend/eval/module10/datasets/failure_cases.json` — all 12 PDF-listed
scenarios present. 11/12 measured (1 honestly `not_applicable`, already
covered by existing tests). Failure Detection Rate 1.0, Recovery Success
Rate 1.0, Unhandled Failure Rate 0.0. Artifact: `failure_eval_20260919T092719Z.json`.

## 22. Actual Measured Results

See `docs/MODULE10_RESULTS.md` in full.

## 23. Evidence Matrix

See `backend/eval/module10/evidence_manifest.json` (machine-checkable)
and the per-section tables above.

## 24. Remaining Gaps

See `docs/MODULE10_RESULTS.md`'s "Remaining Gaps" section — reproduced
in full there, not duplicated here to avoid drift between two copies.
