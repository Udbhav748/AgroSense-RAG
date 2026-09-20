# InsightAI-RAG — 3-Minute Demo Video Script

This is a shot-by-shot recording script for a self-recorded (screen-capture) walkthrough of InsightAI-RAG, intended for embedding in the README as `docs/assets/demo.mp4`. It is written against the actual implemented routes/pages/endpoints in this repository — no invented features.

**Tooling suggestion:** OBS Studio / ShareX (Windows) or QuickTime (Mac) for screen capture, 1920x1080, cursor highlighting on. Record each scene as a separate clip, then cut together — much easier to redo a bad take than to re-run the whole thing live.

**Total target runtime: ~3:00**

---

## 0:00–0:15 — Cold open / hook

- Show the **Home** page (`/`) after logging in — clean landing, sidebar visible.
- **On-screen caption:** "InsightAI-RAG — upload a PDF, get grounded answers with citations."
- **Voiceover (optional):** "This is InsightAI-RAG — a full-stack RAG app that turns any PDF into a chat interface, with every answer grounded in retrieved passages and cited sources."

## 0:15–0:35 — Auth (JWT login)

- Show `/login` and `/signup` briefly (outside the sidebar layout, per `App.jsx`).
- Log in with a real account to demonstrate JWT-based auth.
- **Caption:** "Individual accounts, JWT auth, protected routes."
- Mention: unauthenticated users get redirected to `/login` (`ProtectedRoute`).

## 0:35–1:05 — Upload & ingestion pipeline

- Navigate to `/upload`.
- Upload a real PDF on camera.
- Show the upload progress / task status (`GET /documents/tasks/{task_id}`) if visible in the UI.
- **Caption sequence (matching the real pipeline, from `document_processing_service.py`):**
  `PyMuPDF text extraction → chunking (1000 chars / 200 overlap) → Sentence-Transformers embeddings (all-MiniLM-L6-v2) → FAISS index`
- Once done, cut to `/documents` to show the uploaded document listed (`GET /documents`).

## 1:05–1:45 — Chat with grounded answers + citations

- Navigate to `/chat`.
- Ask a question that's actually answerable from the uploaded PDF.
- Let the **streamed** response play out on camera (`POST /chat/stream`, SSE) — this is a real differentiator, show the text appearing progressively rather than cutting to the final answer.
- Point out the **cited sources** displayed alongside the answer (structurally surfaced via `retrieved_chunks`/`sources`, not just inline text).
- Ask a second, harder question — ideally one that exercises the small-talk router (e.g. "thanks!") to show it skip retrieval entirely and reply instantly.
- **Caption:** "Every answer is grounded in retrieved passages — not model memory."

## 1:45–2:15 — Multimodal diagnosis

- Navigate to `/diagnose`.
- Use the camera capture / image upload to submit a leaf photo (or whatever the vision feature targets).
- Show the vision prediction flowing into the same RAG loop (`POST /chat/diagnose` or the streaming variant) and the resulting grounded diagnosis answer with sources.
- **Caption:** "Vision predictions get grounded through the same retrieval pipeline as text chat."

## 2:15–2:35 — History & session management

- Navigate to `/history`.
- Show past chat sessions listed (`GET /chat/sessions`), open one, demonstrate resuming a session (`loadSession`).
- Optionally show deleting a session (`DELETE /chat/sessions/{id}`).
- **Caption:** "Conversations persist across sessions — resume anytime."

## 2:35–2:50 — Admin / observability (if the demo account has admin role)

- Navigate to `/admin`.
- Show the usage summary (`GET /admin/usage-summary`) and feedback review view.
- **Caption:** "Role-gated admin view for usage and feedback review."
- If no admin account is available for the recording, skip this beat and extend the Chat/Diagnose sections instead — don't fake a role you don't have.

## 2:50–3:00 — Outro

- Cut back to Home or a clean shot of the sidebar with all nav items visible (Chat, Upload, Diagnose, Documents, History, Settings, Admin).
- **Caption:** "InsightAI-RAG — RAG + multimodal, grounded and cited."
- **On-screen:** GitHub repo URL / README link.

---

## Notes for the recorder

- Don't narrate features that aren't shown on screen — keep captions/voiceover tied 1:1 to what's visibly happening.
- If a feature errors or behaves unexpectedly during recording (e.g. a cold-start embedding model delay), cut it rather than editing around a failure — a demo video should show real, working behavior, not best-case footage stitched from failures.
- Once recorded and edited, save the final file as `docs/assets/demo.mp4` (and a poster frame as `docs/assets/demo-poster.jpg`) — see the follow-up README wiring instructions.
