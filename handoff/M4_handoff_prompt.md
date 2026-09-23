I'm continuing a project from previous conversations. I'm building the German
Scene-Based SRS app described in the attached project guide, milestone by
milestone, teaching myself with you as a teacher/pair-programmer.

PROCESS — follow this for every milestone, exactly as before:
1. TEACH FIRST. Before any code, explain the concept for the piece we're
   about to build — what it is, why it's needed, how it fits the rest of the
   stack, and what problem it solves in this specific app.
2. CODE IN CHAT, NOT FILES. Give me code as text to type/paste myself — never
   create files or downloads on my behalf. Small chunks, each explained.
3. I DO THE WORK. Tell me exactly what to do, then STOP and wait for me to
   confirm before moving on. Don't assume a step is done — ask me to paste
   real terminal output/file contents to verify.
4. WHOLE FILES, NOT FRAGMENTS. When giving me a file to edit, either give me
   the complete file to paste over the old one, or explicitly show a
   before/after diff — never a bare "changed part" I have to merge myself.
   If you're unsure what my current file looks like, ask me to paste it
   first rather than assume.
5. EXPLAIN TRADEOFFS whenever there's more than one reasonable approach —
   don't silently pick one. When you make a judgment call on my behalf,
   name it explicitly as a call you made and why.
6. CHECK UNDERSTANDING at natural checkpoints with real questions, not just
   "does it run."
7. USE YOUR TOOLS SPARINGLY — only to verify something (syntax, config
   validity, checking current library/security info), never to produce my
   deliverables.
8. Confirm the milestone's input and Definition of Done before starting, and
   confirm the DoD is actually met (via me testing/describing what I see)
   before moving to the next milestone. Break each milestone into clear
   numbered sub-steps up front, and track progress against them.
9. Keep each milestone scoped to exactly what it needs — don't build ahead.
   Where a real scoping decision exists (e.g. "build it properly now vs.
   defer"), present it explicitly as a choice rather than deciding for me.
10. When a library/security choice is being made, verify current
    best-practice/maintenance status via web search rather than relying on
    training data — we've hit real issues before (passlib/bcrypt version
    incompatibility, python-jose being unmaintained/CVE'd, and in M3 a Groq
    rate-limit/reasoning-mode surprise that only surfaced by actually running
    the code) that only surfaced by checking or testing directly.
11. Backend follows the MVP structure in the guide's §5 exactly (routes →
    services → models; services raise plain Python exceptions, never
    HTTPException; routes catch and translate to HTTP status codes).
12. Real evidence, not assumed success. Every claimed "it works" gets backed
    by pasted terminal output, DB query results, pytest output, or
    Network-tab/HTTP status codes — not just "yes it works."

SPECIAL NOTE FOR THIS MILESTONE — M4 is the first milestone whose Definition
of Done explicitly requires automated unit tests (pytest), not just manual
curl/psql verification like M0–M3. Before proposing the sub-step breakdown,
please:
  (a) confirm pytest (and pytest-asyncio, if our async services need it) is
      actually installed and pinned in requirements.txt — don't assume it's
      already there just because the guide's §5 mentions "pytest" as the
      planned tool,
  (b) walk me through how to structure a `tests/` directory for the first
      time in this project, matching the guide's §5 backend code structure,
  (c) confirm whether the SM-2 algorithm needs a web-search check on current
      best-practice implementation details (interval/ease formulas, edge
      cases at reps=0, minimum ease bounds) before writing update_srs(),
      since getting this subtly wrong would silently produce wrong review
      schedules that are hard to notice are wrong just by testing casually.

CURRENT STATE — M0, M1, M2, and M3 are complete and verified:

M0 (scaffolding): FastAPI app with /health, CORS for http://localhost:5173,
async SQLAlchemy (asyncpg) engine, Pydantic Settings reading .env, Alembic
wired for async migrations against a shared declarative Base
(app/models/base.py). Postgres via Docker Compose using pgvector/pgvector:pg16
on host port 5440 (container name immersely-postgres-1, DB user "immersely",
DB name "immersely_db" — see docker-compose.yml for full env). FastAPI
containerized too (api service in docker-compose.yml alongside postgres).
Day-to-day: uvicorn --reload + npm run dev locally; Docker Compose used
occasionally to verify the containerized stack. Frontend: Vite + React (JS,
not TS), React Router, src/api/client.js reading VITE_API_BASE_URL.

M1 (auth & user accounts) — built in these sub-steps, all verified with real
evidence (curl/DBeaver/browser DevTools), not assumed:

Backend:
- users table (UUID PK via Python-side uuid.uuid4, email unique, hashed_password,
  created_at) — migration in alembic/versions/, models registered centrally via
  app/models/__init__.py (required for Alembic autogenerate to see them).
- Password hashing: passlib[bcrypt] — bcrypt pinned to ==4.0.1 specifically,
  since passlib 1.7.4's version-detection code breaks on bcrypt>=4.1. This
  pin is commented in requirements.txt.
- app/core/security.py: hash_password/verify_password (passlib), JWT helpers
  (create_access_token, create_refresh_token, decode_token) using PyJWT
  (chosen over python-jose, unmaintained/CVE'd), hash_token (SHA-256, for
  refresh-token storage), generate_csrf_token.
- JWT: HS256, access tokens ~30min, refresh tokens ~7 days, both carry
  "sub" (user_id) and "type" ("access"/"refresh") claims.
- refresh_tokens table: SHA-256 hash of each refresh token, user_id FK,
  expires_at, revoked_at (nullable timestamp, audit trail), created_at.
- Full refresh token ROTATION with reuse/theft detection.
- Rate limiting, BOTH mechanisms: per-IP via slowapi (shared Limiter instance
  in app/core/limiter.py, imported everywhere needed), and per-email login
  lockout (custom in-memory tracking in app/services/auth.py).
- Services raise plain Python exceptions defined directly in the relevant
  service file — NEVER HTTPException. Routes catch and translate. This is a
  firm architectural rule applied consistently through M2 and M3 as well —
  apply it to every future service (SRS engine, scene generation, grading).
- get_current_user dependency (app/api/deps.py) using HTTPBearer. Routes
  become "protected" via `current_user: User = Depends(get_current_user)`.
- COOKIE-BASED REFRESH DELIVERY: access token in JSON body only, in-memory
  on frontend. Refresh token: httpOnly, SameSite=Lax cookie, Path=/auth.
  CSRF via Double-Submit Cookie pattern.
- Local dev: cookies use secure=False (commented "True once served over
  HTTPS") — must change before real deployment.

Frontend:
- src/api/client.js: apiFetch() attaches Authorization: Bearer <token> from
  in-memory module variable (setAccessToken), sends credentials: 'include',
  auto-retries once on 401 via deduplicated refreshAccessToken(), handles
  204 No Content responses explicitly (returns null).
- src/context/AuthContext.jsx: AuthProvider holds user/isLoading state,
  attempts silent session restore on mount, exposes login/register/logout.
- src/features/auth/: LoginPage.jsx, RegisterPage.jsx, ProtectedRoute.jsx,
  RedirectIfAuthenticated.jsx.
- App.jsx: AuthProvider wraps BrowserRouter's Routes.
- Frontend structure follows the guide's feature-first convention.

M2 (sentence CRUD) — built in these sub-steps, all verified with real
evidence (curl including a full two-user cross-ownership check, browser
DevTools Network tab), not assumed:

Scoping decision made explicitly: sentences table was built with ONLY the
columns M2 needed (id, user_id, de, en, created_at, updated_at); topics,
grammar_tag, embedding were deliberately deferred and added in M3's ALTER
TABLE migration; SRS fields are deferred to M4's migration (an ALTER TABLE,
not a fresh CREATE TABLE — the sentences table already exists and has real
data in it from testing).

Backend:
- app/models/sentence.py: Sentence model — id (UUID PK), user_id (UUID FK ->
  users.id, no ondelete= cascade set — flagged as a known gap, not yet a
  real issue since there's no user-deletion feature), de/en (Text),
  created_at/updated_at (DateTime(timezone=True)).
- app/schemas/sentence.py: SentenceCreate, SentenceUpdate (exclude_unset=True
  used in the service so PATCH only touches fields actually sent),
  SentenceRead. Deliberately no user_id on any schema.
- app/services/sentences.py: SentenceNotFoundError (single exception
  covering both "doesn't exist" and "belongs to another user" — deliberate
  404-for-both convention to avoid leaking existence of other users' data).
  create_sentence, list_sentences (newest-first), get_sentence (the single
  place ownership is checked), update_sentence and delete_sentence both
  call get_sentence() first.
- app/api/sentences.py: full CRUD, all behind Depends(get_current_user).
  DELETE returns 204. No rate limiting on GET/PATCH/DELETE (deliberate —
  not the same risk profile as auth or LLM-calling endpoints); POST IS now
  rate-limited as of M3 (see below), since it calls Groq.

Frontend:
- src/api/sentences.js: thin wrapper functions built on apiFetch.
- src/features/sentences/SentenceForm.jsx: controlled form, reused for
  create and inline-edit via optional initialValues prop.
- src/features/sentences/SentenceListItem.jsx: toggles display/inline-edit
  mode; window.confirm() before delete; known gap — no visible error
  message if delete fails, buttons just re-enable.
- src/features/sentences/SentencesPage.jsx: owns list state, fetches once
  on mount, updates local state directly after mutations rather than
  refetching (deliberate tradeoff, fine for single-user app).
- KNOWN GAP, not yet addressed: no nav link from Home to /sentences — only
  reachable by typing the URL directly.

M3 (embeddings & topic tagging) — built in these sub-steps, all verified
with real evidence (fingerprint comparisons on embedding vectors, real
server logs, curl + psql confirming persistence, functional UI testing
including page-refresh persistence checks), not assumed:

Web-search checks done before building (per rule 10): confirmed current
sentence-transformers model options and dimensions; confirmed langchain-groq
package/import path was current and unbroken; discovered mid-build (via a
real 429 error, not a search) that Groq enforces a separate, much tighter
output-tokens-per-minute limit than request-count limits suggested, and that
qwen/qwen3.6-27b defaults to an expensive "reasoning" mode that must be
explicitly disabled for lightweight classification tasks.

Backend:
- pgvector extension enabled via migration (hand-written, not autogenerated
  — CREATE EXTENSION plus ALTER TABLE in one migration; extension is NOT
  dropped in downgrade(), since it's shared infrastructure, not scoped to
  one migration).
- sentences table gained: embedding VECTOR(768) (nullable), topics
  TEXT[] NOT NULL DEFAULT '{}', grammar_tag TEXT (nullable).
- Embedding model: paraphrase-multilingual-mpnet-base-v2 (768-dim) via the
  sentence-transformers library — chosen over a 384-dim alternative
  deliberately, trading the "no migration change" convenience for better
  retrieval-oriented quality; also deliberately chosen over BGE-M3 (see
  after-v1 backlog below — BGE-M3 benchmarks meaningfully better for
  retrieval-shaped tasks specifically, but costs another dimension change).
- app/services/embeddings.py: module-level lazy-loaded singleton model,
  _encode_sync() is a plain blocking function, embed_text() is async and
  offloads to a worker thread via asyncio.to_thread() — deliberate choice
  to keep the event loop non-blocking, consistent with the app's
  async-everywhere convention, even though a single-user app might never
  actually need this under real concurrency.
- Embedding generation wired into create_sentence() (always) and
  update_sentence() (only when "de" is present in the update payload —
  English-only edits never trigger re-embedding, since the embedding
  represents the German text's meaning specifically). This was proven with
  md5(embedding::text) fingerprint comparisons, not just "the code looks
  right."
- Topic list: app/core/topics.py, a plain Python constant (TOPICS = [...],
  14 snake_case strings) — deliberately NOT a DB table, since it's app-wide
  config, not user data, and changes rarely. A closed/fixed vocabulary was
  chosen deliberately over open-ended LLM-generated tags, specifically to
  avoid topic fragmentation (e.g. "food" vs "eating" vs "hunger" for similar
  sentences) that would silently degrade M5's scene-generation grouping
  later.
- app/schemas/tagging.py: Topic is an Enum built dynamically from TOPICS
  (Enum("Topic", {...}, type=str)) so the two can never drift apart.
  TopicTaggingResult(BaseModel): topics: list[Topic], grammar_tag: str|None,
  suggested_new_topic: str|None (captured by the LLM when nothing in the
  fixed list fits well — NOT currently persisted or surfaced anywhere in
  the UI; a real gap, see after-v1 backlog).
- app/langchain_/topic_tagging.py: the actual LangChain chain — ChatGroq
  with model="qwen/qwen3.6-27b", temperature=0, reasoning_effort="none"
  (critical — without this, the model's default "thinking" mode alone
  exceeded the free tier's output-tokens-per-minute limit on a single
  short-sentence classification call), reasoning_format="hidden" (required
  by Groq when using structured/tool-call output). Uses
  llm.with_structured_output(TopicTaggingResult) and chain.ainvoke() (async
  native, no asyncio.to_thread needed — this is real network I/O, unlike
  the local embedding model).
- app/services/tagging.py: thin wrapper, TaggingError as the single plain
  exception normalizing whatever goes wrong inside the chain call.
- Tagging wired into create_sentence() ONLY — deliberately NOT re-triggered
  on de edits (to avoid silently overwriting a manual tag correction the
  user made). Tagging is BEST-EFFORT: if it fails (rate limit, network,
  validation), sentence creation still succeeds with topics=[] and
  grammar_tag=None — a deliberate deviation from a strict literal reading
  of the guide's DoD, made explicitly, not silently.
- SentenceUpdate schema extended with topics: list[Topic]|None and
  grammar_tag: str|None — this is the manual-override mechanism. Using the
  same Topic enum here (not a plain list[str]) means FastAPI rejects an
  invalid topic with 422 automatically, keeping the fixed-vocabulary
  guarantee intact even when a human, not the LLM, is setting tags.
- Rate limiting: POST /sentences specifically (not GET/PATCH/DELETE) is
  limited to 10/minute via the same slowapi Limiter from M1 — this is the
  one route that calls Groq, protecting the app's own Groq quota from a
  runaway client loop, not really a security/abuse control the way the
  auth rate limits are.
- GET /topics: new small route, deliberately skips the services layer
  (returns the TOPICS constant directly) since there's no real logic to
  isolate — a named, deliberate exception to the routes→services→models
  pattern used everywhere else. No auth required (not user data).
- A temporary print(f"[tagging failed] {exc}") diagnostic currently sits in
  create_sentence() — added mid-milestone to debug a silent tagging
  failure, never removed. Should become real logging (see after-v1
  backlog) but was left as-is since it's genuinely useful during active
  development.

Frontend:
- src/context/TopicsContext.jsx: mirrors AuthContext.jsx's structure exactly
  (createContext, Provider owning state + fetch effect, use* hook with
  guard-and-throw) but read-only (topics/isLoading only, no actions) since
  nothing in the app creates/deletes topics at runtime. Scoped narrowly to
  wrap only the /sentences route in App.jsx (not the whole app), so the
  GET /topics fetch only fires when actually needed.
- src/api/topics.js: thin wrapper, listTopics().
- Topic filter on SentencesPage.jsx: entirely client-side (filters the
  already-loaded in-memory sentence list) — deliberately NOT a server-side
  query param, to stay consistent with M2's "fetch once, work with local
  state" pattern. Flagged for possible revisit if the sentence list ever
  grows large enough for client-side filtering to become a real limitation
  (see after-v1 backlog).
- src/features/sentences/TagEditor.jsx: new component, rendered inside
  SentenceListItem.jsx's display mode (NOT bundled into SentenceForm.jsx —
  editing tags and editing sentence text are different-frequency, different-
  intent actions). Topic chips: add/remove fire an immediate PATCH per
  action (no batching, no separate save button — click and it's done).
  grammar_tag: local draft state, commits via PATCH on blur/Enter, only if
  the trimmed value actually differs from what's saved (avoids pointless
  no-op PATCH calls). Known gap: no per-chip loading/error state, matching
  the same already-accepted pattern as M2's delete-error gap.
- src/index.css was fully replaced — the original was unrelated starter-
  template boilerplate (a marketing-page hero/dark-mode scheme that had
  nothing to do with this app, and was the actual cause of the "everything
  centered and hard to read" complaint). New palette: cool off-white
  background (#F5F7F6), white surfaces, deep petrol/teal accent (#1C4E4A),
  one clean system-sans typeface, real card/list/form/chip layout. OS-level
  prefers-color-scheme dark mode was deliberately DROPPED (the old file had
  it, but it was a low-contrast, un-designed side effect of the leftover
  template, not a real feature) — proper dark mode is a backlog item, not
  something silently half-solved.

Full M3 DoD verified: pgvector + columns confirmed via psql; embedding
generation and de-only re-embed trigger proven via md5 fingerprint
comparison across three states (original, English-edit, German-edit);
topic tagging proven via direct service test showing correct topics/
grammar_tag; auto-tag-on-create and manual-override-via-PATCH both proven
with real curl + psql evidence; rate limit boundary proven via an 11-request
loop showing exactly ten 201s then a 429; frontend filter, tag editor, and
styling all confirmed working by the user directly, including a page-
refresh persistence check on tag edits.

Dev environment (unchanged from M0): conda env `immersely` (Python 3.10),
requirements.txt hand-maintained with version pins (no pip freeze) —
bcrypt==4.0.1, sentence-transformers, langchain==1.4.0,
langchain-core==1.6.2, langchain-groq==1.1.3 (langgraph and its sub-packages
were also pulled in transitively — not used yet, but present in the
environment; relevant again when M5's generate→verify→retry chain is
built, per the guide's own §1 mention of LangGraph for that case). Frontend:
`npm run dev` (Vite, port 5173). Git: committed incrementally after each
real chunk — keep suggesting commit messages after each meaningful step.

RECOMMENDATIONS FROM M3 THAT MAY APPLY TO M4:
- M4 is the first milestone requiring real automated tests (pytest) per the
  guide's own DoD wording — unlike M0–M3, "real evidence" here should mean
  actual pytest output for the SRS engine's grade-by-grade behavior, not
  just curl/psql snapshots. Worth verifying pytest/pytest-asyncio are
  properly installed and a tests/ directory structure exists before writing
  update_srs() itself.
- SM-2 (or whatever scheduling algorithm) is exactly the kind of "training
  data might be subtly stale or just wrong on edge cases" situation rule 10
  exists for — please web-search current, correct SM-2 implementation
  details (especially ease-factor floor, interval calculation at reps=0/1,
  and how "again" should reset state) before writing the function, the same
  way M3 double-checked the embedding model and LangChain/Groq patterns
  rather than assuming.
- srs_state is a closed-vocabulary text field (guide: 'new' | 'learning' |
  'review' | 'relearning') — M3 established a clean pattern for exactly
  this shape (a Python Enum backing a Pydantic field, giving automatic 422
  validation instead of allowing arbitrary strings into the column) via
  app/schemas/tagging.py's Topic enum. Worth reusing that same pattern here
  rather than inventing a new approach.
- M4 has no LLM/Groq involvement, so the rate-limiting and reasoning-mode
  lessons don't directly apply — but the general lesson (verify current
  library/algorithm behavior via search or direct testing rather than
  trusting memory) very much does.
- The "best-effort vs. blocks the request" fork that came up for M3's
  tagging (a network dependency that can fail) doesn't have an obvious
  parallel in M4, since update_srs() should be a pure, deterministic,
  local function with no external dependencies — but if any real design
  fork like that shows up, flag it the same explicit way.

AFTER-V1 BACKLOG (revisit once v1 / M8 is fully done — do not build any of
this now, just keep it in mind and don't let it creep into current
milestones):
- BGE-M3 as a possible embedding model upgrade (1024-dim, real migration
  required) — benchmarks meaningfully better than the current
  paraphrase-multilingual-mpnet-base-v2 specifically for retrieval-shaped
  tasks (duplicate detection, topic clustering), which is exactly what the
  guide's own §3 "later ideas" anticipates needing.
- Deferred/background embedding AND tagging generation (e.g. via
  BackgroundTasks or a real task queue) instead of the current inline/
  blocking approach — was explicitly deferred during M3 for both.
- Re-verify current Groq model recommendations again at M5 and M6
  specifically — Llama models were deprecated mid-cycle once already;
  don't assume qwen/qwen3.6-27b or gpt-oss-20b/120b are still current
  without checking again when we get there.
- RAG over a grammar/vocabulary knowledge base to ground scene generation
  or corrections in real reference material, not just the LLM's raw
  knowledge — a genuinely new feature, not in the guide at all currently.
- Whisper voice input (already in the guide's own §3).
- LangSmith or similar LLM observability/tracing, once there's enough real
  usage to make debugging opaque without it.
- Benchmarking multiple models (Qwen vs. GPT-OSS variants) against actual
  grading/tagging tasks rather than picking one and moving on.
- A swappable LLM provider abstraction (create_llm(provider, model)) —
  nice hygiene if a second provider (e.g. Ollama) is ever added, pure
  speculation until then.
- The "hybrid" tagging flow: TopicTaggingResult.suggested_new_topic is
  already computed by the LLM but currently discarded — never persisted or
  surfaced in the UI. Building real "flag for manual review" functionality
  around it was explicitly deferred to after-v1.
- Replace the temporary print(f"[tagging failed] ...") diagnostic in
  app/services/sentences.py with proper logging.
- Server-side topic filtering (GET /sentences?topic=X) if the sentence
  list ever grows large enough that client-side filtering (M3's current
  approach) becomes a real limitation.
- Real, deliberately-designed dark mode with a user-controlled toggle (not
  inherited from a template's OS-level prefers-color-scheme switch, which
  was removed during M3's styling pass).
- Topic display-name mapping for the frontend (snake_case like
  "food_and_drink" → a human-readable "Food & Drink") — currently shown
  raw.
- Per-chip loading/error state in TagEditor.jsx — currently silent on
  failure, matching M2's already-accepted delete-error gap.
- Still open from M2: no nav link from Home to /sentences; no ondelete
  cascade on sentences.user_id FK.

Please start by doing the pytest/test-structure setup check and the SM-2
web-search check described above, THEN confirm M4's input and Definition
of Done per the guide, then break M4 down into sub-steps the same way we
did for M1, M2, and M3, and teach me the first concept before I write
anything.
