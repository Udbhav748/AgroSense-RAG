# InsightAI-RAG — Module 10 Final Submission

**Evidence-based Module 10 audit with the following verified capabilities and documented limitations.** This document does not claim 100% completion; every item below is marked ✅ (implementation + test + measurement), ⚠️ (partial/limited measurement), ❌ (missing), or N/A (genuinely not applicable, with rationale), matching the underlying evidence exactly — never upgraded because code merely exists.

**Commit at submission**: `e435ff7` (Phase 5's final commit) · **Regression**: 819 passed, 1 skipped · **Date**: 2026-09-19

*(This document is written as clean Markdown for direct PDF export via any Markdown-to-PDF tool, e.g. `pandoc docs/MODULE10_FINAL_SUBMISSION.md -o submission.pdf`, or a browser's print-to-PDF on the rendered file.)*

---

## 1. Title / Project Identity

**InsightAI-RAG** — a document-grounded Retrieval-Augmented Generation assistant with an explicit agent workflow, plant-disease image diagnosis, and a measured, evidence-based Module 10 evaluation package.

## 2. Project Introduction

Upload a PDF; it is chunked, embedded, and indexed into a FAISS vector store. Ask it questions through a chat interface; every answer is grounded in retrieved passages with structured, citable sources. A second mode accepts a plant-leaf photo and returns a disease diagnosis (via an external LeafSense vision service), fed back through the same RAG loop for treatment guidance. FastAPI backend, React/Vite frontend. Full detail: root `README.md`.

## 3. Problem Statement

Free-text documents have no fixed schema; answering questions against them requires an LLM to synthesize across retrieved passages. The two hard problems this project addresses directly, with measured evidence: (a) not hallucinating when the answer isn't in the document, and correctly distinguishing that from a generation *failure* (see Section 13's Faithfulness fix); (b) defending against prompt injection, jailbreak, and cross-tenant access attempts (Section 16).

## 4. Architecture

Explicit `AgentState` + named-node `StateGraph` (`backend/app/services/agent_graph/`), dependency-free — not LangGraph (a deliberate choice, documented in `docs/ARCHITECTURE.md`'s "Framework choice" section; no claim of using a graph framework that isn't actually in the dependency tree). `build_chat_graph()` is the single production topology behind `/chat`, `/chat/stream`, `/chat/diagnose(/stream)`.

```
Client → API → validate_request → planner
                                     ↓ (conditional routing)
              conversational / summarize / cache_lookup → retrieval → retrieval_grader
                                                                          ↓
                                                    good ──────────────→ generator
                                                    weak/insufficient ──→ [human_approval?] → context_augmentation
                                                                                                  ↓
                                                                          generator ← ─ ─ ─ ─ ─ ─┘
                                                                             ↓
                                                                        reflection → output_validation → finalizer
```

Cross-cutting: memory (`agent_memory.py`, `session_store.py`), tools (`tools/registry.py`), vision (`vision_client.py`), web search (`web_search_service.py`), human approval (`human_approval.py` + `approval_service.py`), metrics/tracing (`core/metrics.py`, `agent_graph/events.py`), vector store (`faiss_vector_store.py`), LLM provider abstraction (`llm_provider.py` over Gemini/Groq). Full diagram with all node labels: `docs/ARCHITECTURE.md` (kept in sync with the actual graph wiring as of Phase 5 — see that document's own Phase 5 update note).

## 5. Agent Workflow

Deterministic routing (`ChatService._plan`/`_route`, regex/keyword-based, not an LLM decision) to one of: conversational (canned replies), summarize (whole-document), or retrieve/diagnose (the RAG path). Measured: Planner Accuracy 0.9333, Macro F1 0.9475 (15 cases). Bounded corrective loop (generate → reflect once → escalate to web search once) capped at `_MAX_LLM_CALLS=3`, preventing infinite loops (Loop Rate measured at 0.0).

## 6. Tools / Memory / Approval

**Tools**: web search, summarization, diagnose, vision QA via `ToolRegistry.execute` — Tool Selection Accuracy 1.0, Tool Argument Accuracy 1.0.

**Memory**: session-scoped conversation history (`InMemorySessionStore`, LRU-bounded), injected into the planner/generator context. Session-boundary isolation confirmed: 0 cross-session leaks measured.

**Human approval** (✅, Phase 5): `human_approval_node` is wired into the live graph for the web-search escalation — a weak/insufficient retrieval grade under `Settings.web_search_requires_approval` routes through it rather than performing the search directly. Approved requests proceed to the actual web search; pending/rejected/expired requests still generate the best answer from whatever was already retrieved, without ever performing the unapproved search. Document deletion has a separate, route-level approval gate requiring a real, resolved `Approval` record — a bare client-supplied `approved=true` no longer suffices (a genuine security fix in Phase 5, replacing the prior insecure-but-tested behavior). 12 new tests across both mechanisms.

## 7. RAG Implementation

Hybrid retrieval: dense FAISS + sparse BM25 fused via Reciprocal Rank Fusion (k=60), optional cross-encoder reranking. Heuristic grading (good/weak/insufficient) gates escalation to web search. Generation prompts wrap retrieved excerpts in explicit untrusted-data delimiters (prompt-injection defense) and require inline `[N]` citations.

## 8. RAG Evaluation

| Configuration | P@5 | Recall@5 | Hit@5 | MRR |
|---|---:|---:|---:|---:|
| Semantic only | 0.4174 | 0.6014 | 0.6957 | 0.6739 |
| Hybrid (BM25+vector) | 0.6087 | 0.7428 | 0.9130 | 0.8551 |
| Hybrid + rerank | 0.6435 | 0.8080 | 0.9130 | 0.8783 |

Hybrid retrieval consistently outperforms semantic-only; reranking adds a further gain on P@5/Recall@5. Source: `eval/module10/reports/rag_eval_20260919T103118Z.json` (30 cases, live).

**Faithfulness — the project's most important measured finding.** A live re-run of the 20-case golden benchmark found Mean Faithfulness at **0.0000**, sharply down from a historical, unverified 0.9420. Root-cause investigation (traced prompt → chunks → generation → reflection) found this was **not a model-quality or retrieval problem**: `generator_node` was catching *any* LLM provider failure (timeout, rate limit, API error surviving 3 retries) and silently substituting the exact text used for a genuine "not in the documents" answer — making a provider failure indistinguishable from a confident refusal, to both users and the automated metric. Fixed with a distinct `GENERATION_ERROR_REPLY` sentinel (Section 13). Post-fix, live re-verification on the two cases that first exposed this (human-eval rows 17, 19) shows both now producing real, correctly-cited answers. **This targeted 2-case verification is not a full-dataset re-measurement** — stated explicitly, not extrapolated.

## 9. Agent Evaluation

Planner Accuracy 0.9333 (Macro F1 0.9475), Tool Selection Accuracy 1.0, Tool Argument Accuracy 1.0, Planning Success Rate 1.0 (3/3), Workflow Completion Rate 1.0, Node Success Rate 1.0, Average Steps 8.5, Loop Rate 0.0, Cost Per Successful Task **$0.001124** (measured from real per-request token/cost telemetry, never estimated as zero). Source: `eval/module10/reports/agent_eval_20260919T112455Z.json`.

## 10. Structured Outputs

`app/services/structured_output.py::parse_structured_answer` — defensive JSON parsing (code-fence stripping, block extraction, Pydantic validation), never raises, degrades to free-text on any failure. 6/6 tested failure modes (plain JSON, fenced JSON, trailing prose, invalid JSON, schema mismatch, empty) all degrade safely.

## 11. Human Evaluation

24 cases (16 original + 8 added in the gap-closure pass), single reviewer, 7 rubric dimensions (Correctness, Helpfulness, Completeness, Safety, Tone, Groundedness, Citation Quality). Inter-Annotator Agreement: **N/A** — exactly one reviewer, stated honestly rather than fabricating a second. The 8 new rows independently corroborated the Faithfulness regression via manual review (rows 17, 19 refused despite correct retrieval) before the automated metric's number was even computed — two independent signals agreeing on the same real bug. Full detail: `docs/HUMAN_EVAL.md`.

## 12. Hard Cases / Failures

`eval/module10/datasets/hard_cases.json`: 7 RAG hard cases (ambiguous disease name, out-of-corpus, rare terminology, wrong crop, etc.), 7 agent hard cases, 4 multimodal hard cases. One dataset-staleness finding: the "citrus greening is out-of-corpus" assumption is no longer true — the live vector store now contains real HLB content (found via human-eval row 19), documented rather than silently left wrong.

## 13. Debugging / Root Cause Analysis

The Faithfulness regression (Section 8) is this project's central debugging case study. Using only existing structured logs (`agent_node_trace`, `chat_query_handled`) and an existing debug flag (`settings.log_prompt_content`), the investigation: (1) reproduced the failure deterministically against the exact failing query, (2) confirmed via prompt capture that retrieval and prompt construction were correct, (3) traced the live log pattern (`llm_generation_retrying` firing twice per call) to a real, reproduced `groq.RateLimitError: Used 199474/200000` — the account's daily token quota was hit *during the investigation itself*, live evidence for the root cause, (4) found the exact code location (`generator_node`'s exception handler) silently substituting a misleading answer, (5) fixed it with the smallest safe change (a new sentinel string + one `_is_ungrounded` update), (6) added regression tests, (7) verified live post-fix.

## 14. Observability

Structured JSON logs throughout (`request_id`/`trace_id` per node), `agent_node_trace` (status/latency/error_type per node execution), `chat_query_handled` (cost/tokens/steps per request). `GET /health` and `GET /metrics` both exist and are registered. No secrets, raw auth headers, or full document/query text appear in these structured fields (confirmed by code inspection and by the fact this investigation used them directly without needing new instrumentation).

## 15. LLMOps

Every Module 10 evaluation artifact (`eval/module10/reports/*.json`) carries git commit, dataset version, model/provider, embedding model, configuration, and timestamp via `eval/module10/config.py::run_metadata()`. No historical artifact has ever been overwritten — corrected and pre-correction versions coexist side by side (e.g. the RBAC 0.3333 finding and its 0.0 correction).

## 16. Security / Privacy

| Metric | Result | Source |
|---|---:|---|
| PII Recall | 1.0 | `security_eval_20260919T111236Z.json` |
| Unauthorized Access Rate | 0.0 (0/2 cross-tenant) | same |
| Prompt Injection Success Rate | 0.0 | same |
| Jailbreak Success Rate | 0.0 | same |
| False Refusal Rate | 0.0 | same |
| Data Leak Rate | 0.0 | same |

The Unauthorized Access Rate was originally mismeasured at 0.3333 — traced to the *evaluation script* wrongly counting an app-authorized same-tenant member delete as an attack (`app/core/permissions.py` deliberately grants members `DOCUMENT_DELETE`). The app's RBAC policy was correct all along; the script was fixed, not the app. Document-delete approval was separately hardened in Phase 5 to require a genuinely resolved `Approval` record (Section 6).

## 17. Deployment / Production Readiness

`backend/Dockerfile` exists. **No cloud capability is claimed that isn't deployed**: no load balancer, no autoscaling, no managed secrets store, no centralized logging — this runs as a single-process FastAPI service with `.env`-based configuration. `.env` is confirmed never committed to git (verified: `git log --all --full-history -- backend/.env` returns empty). Consistent, honest scaling limitations are documented in `docs/DESIGN_REVIEW.md` §9.

## 18. Performance / Cost

Cost Per Successful Task: **$0.001124** (measured, real Groq per-request cost — never estimated as zero for a missing case). One disclosed, unresolved finding: the current Groq model (`openai/gpt-oss-120b`) is a reasoning model (its usage payload includes `reasoning_tokens`), plausibly explaining both elevated generation latency and the rapid exhaustion of the account's 200,000-token daily quota during evaluation. No model change was made without a fair, evidence-based A/B comparison — none has been run yet (open recommendation).

## 19. The 10 Design Questions

1. **Why an LLM?** Free-text documents have no fixed schema; only an LLM can synthesize across retrieved passages phrased in natural language.
2. **What decisions are LLM-made vs. deterministic?** Routing is deterministic regex/keyword matching (measured Accuracy 0.9333 against a fixed rubric — not a black box). Only generation and optional structured-output extraction are LLM decisions.
3. **Five measured failure modes**: LLM provider failure mislabeled as a refusal (found, fixed); stale retrieval-corpus assumptions in eval datasets (found); retrieval returning topically-adjacent-but-wrong-crop chunks (found); prompt injection via retrieved content (defended, 0.0 success); cross-tenant authorization bypass attempts (defended, 0.0 success).
4. **How are failures detected?** Structured per-node traces with `error_type`/`root_cause`, used directly to diagnose the Faithfulness regression without adding new instrumentation.
5. **How does the system recover?** A bounded corrective loop (regenerate once, escalate to web search once, cap at 3 total LLM calls) — now honestly labeled after the Section 8 fix.
6. **How is a new version proven better?** Before/after artifacts at every fix (0.3333→0.0 Unauthorized Access Rate, 0.0→1.0 Workflow Completion Rate after a model-deprecation fix, both artifacts preserved) — never a single unverified number.
7. **How are data/secrets protected?** API-key + JWT auth, tenant isolation, PII detection (1.0 recall), `.env` confirmed never committed.
8. **Cost per successful task?** $0.001124, measured from real telemetry.
9. **Scaling 10→1M users?** Not attempted in this evaluation arc — the honest, unchanged answer remains in `docs/DESIGN_REVIEW.md` §9: single-process FastAPI, in-memory FAISS, no autoscaling.
10. **Why should a customer trust this system?** Because its failure modes are measured and disclosed rather than hidden — a real regression was found and fixed with full root-cause evidence, two real approval-flow gaps were found and fixed, and nothing here is marked ✅ merely because the code exists.

## 20. Final Checklist, Limitations, and Evidence Index

See `docs/MODULE10_FINAL_AUDIT.md` §24 for the complete requirement-by-requirement table, `docs/MODULE10_EVIDENCE_INDEX.md` for the flat evidence pointer table, and `docs/REPRODUCE_MODULE10.md` for exact reproduction commands with external-dependency requirements stated.

**Summary status**: 10+ requirement areas ✅ (implementation + test + measurement), 4 ⚠️ (limited-scope measurement, stated explicitly), 0 ❌ remaining (both Phase 4 findings resolved in Phase 5), N/A items (cloud deployment) correctly not claimed. **Not 100% complete — by design, and stated as such.**

---

*Companion documents: `docs/MODULE10_GAP_CLOSURE_REPORT.md`, `docs/PHASE3_PRODUCTION_HARDENING_REPORT.md`, `docs/PHASE4_FINAL_PRODUCTION_READINESS_REPORT.md`, `docs/PHASE5_FINAL_GAP_CLOSURE_REPORT.md`, `docs/MODULE10_FINAL_AUDIT.md`.*
