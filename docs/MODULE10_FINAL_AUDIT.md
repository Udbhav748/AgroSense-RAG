# Module 10 — Final Technical Audit

**Branch**: `module10-final-pdf-compliance` (not merged to `main`) · **Commit**: verify with `git rev-parse HEAD` · **Regression**: 1035 passed, 1 skipped, 0 failed (1036 collected) · **Date**: 2026-09-21–22 (P9 consolidation; same-day follow-ups for real parallel execution, expanded encryption at rest, code-enforced secrets, a real faithfulness root-cause fix, and a real paired significance test for Provider A/B)

This is the detailed technical companion to `docs/MODULE10_FINAL_SUBMISSION.md` (the evaluator-facing overview). It gives checklist coverage, evidence locations, reproduction commands, measured metrics, and limitations per Module 10 section, without duplicating raw JSON results — those are linked, not pasted. The literal Module 10 PDF checklist (14 sections + 10-question design review) was provided directly in this pass and is mapped row-by-row in `docs/MODULE10_PDF_TRACEABILITY_MATRIX.md`; this document organizes evidence by the same section numbers.

**Evidence quality rule applied throughout**: a row is only ✅ if an evaluator could reproduce it from the repository without trusting prose. If not, it is ⚠️ or ❌, never upgraded because a function with the right name exists.

---

## §1 Agentic AI Foundations

| Item | Status | Evidence | Command |
|---|---|---|---|
| Planner | ✅ | `rag_service.py::_plan/_route` (deterministic keyword routing) | `pytest tests/test_agent_graph.py -q` |
| ≥2 tools | ✅ | retrieval, summarization, web search, vision QA (`tools/registry.py`) | same |
| Memory | ✅ | `session_store.py` (LRU, session-scoped), `agent_memory.py` | `agent_eval_*.json`'s `memory_session_boundary` |
| Retry | ✅ | `tenacity` on LLM/embedding/web-search calls | `pytest tests/test_groq_client.py tests/test_gemini_client.py -q` |
| Reflection | ✅ | `_correct` corrective loop, capped at 3 LLM calls | `pytest tests/test_agent_graph_production.py -q` |
| Human approval | ✅ | `human_approval_node` wired into live routing for web-search escalation; document-delete requires a resolved `ApprovalStore` record | `pytest -k approval -q` |
| Structured output | ✅ (now production, P4) | `structured_output.py`, `Settings.structured_output_enabled=True` default | `python eval/module10/runners/run_structured_output_eval.py` |
| Error handling | ✅ | `AppError` taxonomy + global handler (`core/error_handlers.py`) | full suite |
| Logging | ✅ | Structured JSON, `request_id`/`trace_id` per line | `core/logging.py` |

Metrics: Tool Selection Accuracy 1.0, Task Success Rate 1.0 (`agent_eval_20260919T112455Z.json`).

## §2 LangChain, LangGraph and CrewAI

Not used as third-party frameworks. Equivalent concepts implemented natively: nodes/edges/state/conditional-routing → `app/services/agent_graph/{engine,graph,state,nodes,routing}.py` (dependency-free `StateGraph`, confirmed via `requirements.txt` — no `langgraph`/`langchain-core`/`crewai` dependency). Workflow Completion Rate 1.0, Node Success Rate 1.0, Agent Handoff Accuracy N/A (single-agent design — no multi-agent handoffs occur), Average Node Latency measured per `agent_node_trace` events. Parallel execution: **implemented** for one real workflow — non-streaming `handle_diagnose` runs vision classification and the weather/microclimate lookup as genuinely concurrent `asyncio` branches via a new reusable primitive, `run_concurrent_branches`/`BranchResult` (`agent_graph/engine.py`). The main `/chat` corrective loop and tool calls remain sequential by design (each step depends on the previous one's output — no independent work exists there to parallelize), and the streaming diagnose path (`stream_diagnose`) was not converted (disclosed limitation, not hidden). Proven via mutual-wait tests (not wall-clock thresholds): `pytest tests/test_agent_graph_parallel_execution.py tests/test_handle_diagnose_parallel.py -q` (19 tests). Measured evidence (real serial-vs-parallel comparison, identical mocked I/O): `backend/eval/module10/reports/parallel_execution_final_20260921T180758Z.json` — serial mean 0.6598s vs parallel mean 0.3544s, 46.3% measured reduction, reproduce via `python eval/module10/runners/run_parallel_execution_final.py`.

## §3 Practical Agent Integration

Tools documented (docstrings + `tools/registry.py` schemas), input/output schemas via Pydantic, retry (`tenacity`), timeout (per-service `*_timeout_seconds` settings), authentication (API key/JWT on every route). Metrics: API Success Rate, Retry Success Rate, Timeout Rate, Argument Accuracy — measured in `tool_reliability_final_20260920T015928Z.json` and `tool_validation_final_20260920T012315Z.json`. **Limitation**: not every tool shares one universal envelope; argument accuracy is measured only on the subset with ground-truth values (`agent_eval_*.json`).

## §4 Retrieval-Augmented Generation

Chunking (1000/200), embedding (`all-MiniLM-L6-v2`), FAISS `IndexFlatIP`, hybrid BM25+FAISS+RRF, optional cross-encoder reranking, citation via `_source_references`. Metrics — see `docs/MODULE10_FINAL_SUBMISSION.md` §6 for the full P@5/Recall@5/Hit@5/MRR/Faithfulness table. Groundedness/citation accuracy are lexical proxies, labeled as such.

## §5 Structured Outputs

See `docs/MODULE10_FINAL_SUBMISSION.md` §8. Schema Compliance Rate 0.4118 is an evaluator-artifact of the 17-case dataset's own valid/malformed mix, not a defect — Parser Correctness and Field Accuracy are both 1.0.

## §6 Classification Evaluation

Applied where genuinely applicable — planner intent classification (confusion matrix, per-class P/R/F1, Macro F1 0.9475, Weighted F1 0.9325, `agent_eval_20260919T103533Z.json`). TP/FP/TN/FN-style confusion-matrix reporting is **not applicable** to the core RAG answer-quality problem itself (there is no fixed positive/negative class for "is this answer correct") — used only where a real classification task exists.

## §7 Agent Evaluation

See `docs/MODULE10_FINAL_SUBMISSION.md` §7 for the full table. Hallucination detection: a proxy lexical-groundedness check (`_detect_hallucination`) plus a dedicated hallucination-taxonomy evaluation pass (`hallucination_taxonomy_final_20260920T014121Z.json`) — disclosed as proxy-based, not a full dedicated model.

## §8 Human Evaluation

24 cases, 7 dimensions, 1 real reviewer. **Two-reviewer/IAA infrastructure implemented and tested (P8)** — not the same as IAA measured. See `docs/MODULE10_FINAL_SUBMISSION.md` §9 and `docs/HUMAN_EVAL.md`'s own Inter-Annotator Agreement section for the full, explicit distinction. **Status must remain**: Human Evaluation = ✅ (infrastructure + real reviewer-1 evidence); Two-reviewer IAA = ⚠️ (pending actual reviewer-2 completion). The weighted-Cohen's-kappa unit-test fixtures (`tests/test_human_eval_p8.py`) are evidence of **metric correctness**, not project agreement — never conflated.

## §9 Debugging

Full pipeline trace (input→planner→retriever→tool→LLM→output) via structured logs; prompt version always recorded (`generation_requested`), exact prompt content is debug-only (`Settings.log_prompt_content`, off by default, tested in `tests/test_prompt_capture_boundary.py`); tool logs include names/args/outputs/failures; token logs per generation; error taxonomy matches `core/exceptions.py`'s categories (input/intent/planner/tool/retriever/memory/prompt/reasoning/output/deployment — mapped via `AppError.taxonomy_category`).

## §10 Observability

See `docs/MODULE10_FINAL_SUBMISSION.md` §11. Real finding: cache-hit responses bypass `chat_query_handled` logging (disclosed, regression-pinned, not silently patched). `AlertEngine` real and tested, not continuously scheduled. Dashboard real, on-demand, not a hosted live service. Availability bounded-local, not an SLO.

## §11 LLMOps

Every artifact carries git commit, dataset version, model/provider, timestamp (`eval/module10/config.py::run_metadata()`); no artifact ever overwritten. A/B testing: real, controlled provider comparison (P5, see `docs/MODULE10_FINAL_SUBMISSION.md` §13) — no winner declared. Rollback: documented procedure in `docs/OPERATIONS.md`, exercised historically on a version tag. Regression gate wired into `eval.yml`.

## §12 Cloud Deployment

Docker + docker-compose exist. HTTPS is a documented Caddy-overlay path, not independently validated against a live TLS endpoint this pass. Secrets: `.env`-based, SSM path documented, **not enforced by code**. Load balancer/autoscaling: N/A — genuinely single-instance design, not attempted. Requests-per-second/latency/availability: measured **locally only** (P7) — see `docs/MODULE10_FINAL_SUBMISSION.md` §14; not cloud-validated. CPU/GPU/memory utilization: local `psutil` sampling attempted in P7 but measured the wrong process (client, not server) — disclosed, not corrected in this pass. Cost/hour: not measured (no live deployment to meter).

## §13 Privacy, Security and Responsible AI

See `docs/MODULE10_FINAL_SUBMISSION.md` §10 for the full metrics table. Authentication (API key/JWT), authorization (RBAC, `core/permissions.py`), PII detection, encryption at rest (`ChatTurn.content` **and** `ChatSession.title`, AES-256-GCM, expanded 2026-09-21 — see below), secret management (documented, not code-enforced), RBAC, human approval, audit logs (`core/logging.py`'s `audit_event` lines) all present. **No GDPR/DPDP/HIPAA compliance certification is claimed** — having these controls is not the same as a compliance assessment.

## §14 Production Readiness

Architecture diagram: `docs/ARCHITECTURE.md`. AI: agent/planner/tools/memory/RAG all documented with rationale. Evaluation: normal/edge/failure/adversarial datasets exist (`dataset_v1/v2/v3.json`, `hard_cases.json`); metrics selected by cost-of-failure rationale (`eval/README.md`); human evaluation with explicit rubric. Debugging: logs/traces/error taxonomy all present. Deployment: Docker packaged; cloud path documented, not deployed; monitoring real but local/on-demand. Security: auth/authz/secrets/encryption all present, scoped as disclosed above. Reliability: retry/timeout/fallback (`FallbackLLMClient`)/cache (`SemanticQueryCache`) all present. Cost: tokens/latency/model-routing/cache all tracked. Documentation: README, API docs (`/docs` via FastAPI), architecture docs, a real demo video, and this final-submission package's own Limitations section for future work.

**Production AI Design Review (10 questions)**: answered in full in `docs/MODULE10_FINAL_SUBMISSION.md` §18, with question 9 explicitly separating current measured local behavior from unvalidated future scaling architecture.

---

## Full Backend Regression

```
cd backend && pytest -q
```
**1035 passed, 1 skipped, 0 failed** (1036 collected) — includes the 19 new parallel-execution tests, 12 new encryption-at-rest tests, 14 new secrets-validation tests, 3 new retrieval-signature-regression tests, and 5 new provider-A/B-significance-test tests, all added across 2026-09-21–22; verify with `git rev-parse HEAD` and `cd backend && pytest -q`. (Historical: 982 passed, 1 skipped at commit `7159169`, before any of the additions below.)

## Reproduction Index

See `docs/MODULE10_FINAL_SUBMISSION.md` §20 for the complete command list (every command was verified to exist and run during this pass's own inspection — none is a hypothetical).

## Evidence Artifact Index

All under `backend/eval/module10/reports/` (35 artifacts as of this pass, never overwritten): RAG (5), agent (6), security (3), failure (2), memory (1), multimodal (1), faithfulness (3), structured output (2), tool reliability/validation (2), encryption (2), hallucination taxonomy (1), load test (2), observability (2), availability (1), provider A/B (1), human evaluation (2), diagnose reliability (1), alerting (1).

## Known Doc Drift Corrected This Pass (P9)

- `README.md`: test-count badge/text (819/820 → 983 collected, 982 passed), stale faithfulness figure (0.6485 presented as current → 0.7093, with historical baseline properly labeled), stale "no field-level encryption" claim (→ documents the real `ChatTurn.content` AES-256-GCM encryption), stale alerting/dashboard "NOT DEPLOYED" wording (→ distinguishes "implemented, tested, run on demand" from "not continuously scheduled/hosted").
- `docs/MODULE10_FINAL_SUBMISSION.md` and this document: both were last substantively written after Phase 5 (referencing "819 passed") and never updated through P2–P8 — fully rewritten this pass to reflect the current state.
- `docs/MODULE10_PDF_TRACEABILITY_MATRIX.md`: rebuilt against the literal PDF checklist (provided this pass) rather than a reconstructed approximation — see that document's own revision note.

## Remaining ⚠️/❌ Items (not resolved by this pass, by design — P9 is a documentation/audit pass, not new feature work)

1. Human IAA — infrastructure complete, real measurement pending an independent second reviewer.
2. Faithfulness 0.7809 (raised from 0.7093 on 2026-09-22 after fixing a real eval-script bug that resolved `eval-potato-02`); `eval-potato-01` and `eval-apple-01` remain weak under a disclosed retrieval-ranking limitation.
3. No cloud-validated RPS/autoscaling/load-balancer/cost-per-hour.
4. `AlertEngine` not continuously scheduled; no hosted dashboard/centralized logging.
5. Cache-hit responses invisible to log-based aggregation (disclosed, not patched).
6. Encryption at rest now covers `ChatTurn.content` and `ChatSession.title` (expanded 2026-09-21, see below); FAISS metadata/vectors, uploaded PDF files, and feedback records remain unencrypted for disclosed technical reasons. No key rotation.
7. HTTPS path documented, not independently tested against a live TLS endpoint.
8. Secret management documented, not code-enforced.
9. No formal GDPR/DPDP/HIPAA compliance assessment.
10. Provider A/B: a real paired significance test is now applied (2026-09-22, see below) — still a single frozen dataset/domain (n=20 queries), and this run's result is substantially confounded by gemini's elevated provider-failure rate at run time, disclosed as such.

## Same-Day Addition After P9: Real Parallel Execution

Closed the "Parallel execution" gap in §2 above (previously ❌, disclosed as a real gap rather than skipped). See §2 and `docs/MODULE10_PDF_TRACEABILITY_MATRIX.md` §2 for the full disclosure of scope: implemented for the non-streaming diagnose workflow only; the streaming diagnose path was not converted. This did not touch any of the 10 items listed above.

## Same-Day Addition After Parallel Execution: Expanded Encryption at Rest

Extended encryption-at-rest coverage (item 6 above) from `ChatTurn.content` only to also cover `ChatSession.title` — real, sensitive user-authored content (populated verbatim from a user's first message) that was sitting in plaintext in the same table as the already-encrypted content column. Implementation: a new shared `encrypt_text_field`/`decrypt_text_field` helper pair in `app/core/encryption.py` (factored out to avoid duplicating the AES-256-GCM/marker/backward-compatibility logic across two call sites), used by both `postgres_session_store.py` (refactored, behavior-preserving) and `session_repository.py` (new). Same `session_id`-bound AAD, same `enc1:` on-disk marker, same legacy-plaintext-passthrough backward compatibility, same fail-closed behavior on a missing/wrong key.

**Explicitly NOT encrypted, with reasons** (see `docs/MODULE10_PDF_TRACEABILITY_MATRIX.md` §13 for the full coverage matrix): FAISS metadata.json chunk text and the FAISS vector index (would require decrypting on every retrieval call across many call sites, or make similarity search itself impossible), uploaded raw PDF files on disk (PyMuPDF reads them directly by path; would require a decrypt-to-tempfile step plus a migration story for already-uploaded files), feedback.jsonl (an evaluation artifact read in bulk by `metrics_report.py`, not primary user-content storage), Tenant/User/ApiKey metadata (not free-text content; email is looked up by an equality index that transparent encryption would break without a blind-index scheme). Encryption in transit (HTTPS/TLS) was explicitly out of scope for this pass and is tracked separately.

Evidence: `backend/eval/module10/reports/encryption_at_rest_final_20260921T193344Z.json` — real executed checks (encrypted-on-disk, round-trip, wrong-key, tamper, missing-key fail-closed, cross-session AAD isolation, legacy backward compatibility), all passed. Tests: 33 passed (21 pre-existing + 12 new, `tests/test_session_repository_encryption.py`).

## Same-Day Addition: Secrets Now Code-Enforced

Closed the "Secret management" gap (previously "documented, not code-enforced"). `Settings._reject_weak_secrets_in_production` (`app/core/config.py`, a `pydantic` `model_validator`) refuses to construct `Settings` when `DEBUG=false` (production) and `API_KEY`/`API_KEYS`/`JWT_SECRET_KEY`/`DATABASE_URL` are missing, a known placeholder from `.env.example`, or below a minimum length — failing fast at process startup, before a single request can be served, matching the codebase's existing "fail loud, not silently insecure" posture (`EncryptionKeyMissingError`, `AuthConfigurationError`). `DEBUG=true` (the local-dev default) leaves placeholder secrets untouched — this only activates for a run explicitly claiming to be production. Scope, stated honestly: this is **application-level** enforcement (weak values in the app's own config), not a managed secret-manager integration — the AWS SSM path remains documented, not newly built.

A real bug was caught and fixed during this change's own regression run: the validator initially flagged the single `API_KEY` field even when `API_KEYS` (the per-client map) was set and actually superseded it — this crashed a real uvicorn subprocess in `tests/test_load_concurrency_eval.py`'s smoke test. Fixed by only validating `API_KEY` when `API_KEYS` is unset. `tests/conftest.py` was also updated to set `DEBUG=true` explicitly for the test session rather than relying on the ambient `backend/.env`, so the suite doesn't silently start failing closed in a clean checkout with no `.env` file.

Tests: 14 new (`tests/test_settings_secret_validation.py`).

## Same-Day Addition: Real Second Root-Cause Fix for Faithfulness (`eval-potato-02`)

Investigated the disclosed-unresolved `eval-potato-02` case and found it was never a RAG-pipeline defect: a real bug in `scripts/run_rag_eval.py` itself. `execute_retrieval()` called `retrieval_service.retrieve()` with a keyword argument (`rerank_candidates`) that doesn't exist on the real function — the actual parameter is `rerank`. Every retrieval call in this script's history raised a `TypeError`, silently caught by a broad `except Exception` logged only at `DEBUG` level, degrading every retrieval to a raw-vector/file-based fallback (no hybrid BM25, no collection filter, no reranking) without ever surfacing an error. Fixed with a one-line change; the exception log was also elevated from `debug` to `warning` so this class of bug can't hide silently again.

Verified: `eval-potato-02` faithfulness 0.0 → **0.6** (all 8 expected active ingredients/organic remedies now correctly retrieved and cited, context recall 0.125 → 1.0). Full 20-case re-run: mean faithfulness 0.7093 → **0.7809**, mean context recall → **0.91**. Two cases remain weak under the now-correctly-exercised retrieval path — `eval-potato-01` (0.4) and a newly-visible `eval-apple-01` (0.0, was 0.3333 under the broken fallback) — both the same already-disclosed cross-encoder/dosage-table-chunk ranking limitation, not fixed by this pass, not hidden either.

Regression test (calls the real `retrieve()`, not a mock, so a signature mismatch fails loudly): `tests/test_run_rag_eval_retrieval_signature.py` (3 tests). Evidence: `backend/eval/module10/reports/rag_eval_retrieve_signature_fix_20260922T145928Z.json`.

## Same-Day Addition: Real Paired Significance Test for Provider A/B

Closed the "single run, no significance claimed" gap (item 10 above). The prior framing conflated "single run per configuration" with "no valid significance test is possible" — the correct unit of comparison for this A/B design is the *pair* (the same query, run once under each configuration), and 20 matched pairs is a valid sample for a paired test. New `_paired_significance_test` function (`eval/module10/runners/run_provider_ab_eval.py`): a paired Wilcoxon signed-rank test plus a percentile bootstrap 95% CI on the mean paired difference, computed on faithfulness and composite score. 5 new deterministic unit tests on synthetic data (no live calls): `tests/test_provider_ab_eval.py::TestPairedSignificanceTest`.

A fresh live re-run (real API calls, user-approved given the cost) was required to capture per-case pairs correctly measured against the also-just-fixed retrieval bug (reusing the prior run's stale per-case data would have built a "correct" statistical test on top of known-degraded retrieval numbers). Result (`provider_ab_eval_20260922T153548Z.json`): faithfulness groq=0.7641 vs gemini=0.21, **p=0.0009**, 95% CI [-0.76, -0.34] — significant, but gemini's provider failure rate was 0.7 this run (14/20 `GENERATION_ERROR_REPLY`), so most of the gap reflects provider reliability at run time, not a stable model-quality claim — disclosed prominently in `docs/MODULE10_RESULTS.md`, not buried. Production default unchanged; no provider declared superior.
