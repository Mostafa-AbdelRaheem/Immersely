M6 Handoff — Correction / Grading Engine
Project: German Scene-Based SRS

This is a continuation handoff, following the same working style as the
M5 handoff: implement step by step, code-along, validate each step's
output together before moving to the next. Please keep that style for M6.

===========================================================================
0. How to work with me on this milestone
===========================================================================
- Follow the same best practices, clean code, and system design as the
  original project guide (service-layer separation, DI via FastAPI
  Depends, LangChain chains behind a service interface, etc).
- Break work into small steps. Explain each step you create.
- Give code step by step, one piece at a time, so I can implement it
  along with you.
- After each step, WAIT for me to run a validation command and paste
  the real output before moving to the next step. Do not assume a step
  worked without confirmation.
- If you don't know something about my codebase or have doubts, ASK —
  don't guess or assume file paths, model names, settings, etc.
- I will paste real file contents, real terminal output (including
  tracebacks), and real errors as they happen. Treat them as ground
  truth over anything assumed from the original project guide, since
  the guide is a plan, not a record of what was actually built.

===========================================================================
1. Tech stack (confirmed, as actually implemented)
===========================================================================
Frontend: React (Vite, .jsx, JavaScript not TypeScript), plain fetch-based
  API client, plain CSS (no Tailwind/CSS modules/styled-components),
  react-router-dom.
Backend: Python, FastAPI, async endpoints throughout.
ORM / DB: SQLAlchemy (async, asyncpg) + PostgreSQL with pgvector.
Migrations: Alembic (async env.py, autogenerate works against a live DB).
RAG orchestration: LangChain, using ChatGroq with structured output
  (`with_structured_output`) for every LLM call so far — no LangGraph
  used yet even though the original guide mentioned it as an option.
LLM inference: Groq API.
  IMPORTANT — confirmed working model: `openai/gpt-oss-20b`
    (production tier, reasoning-capable via reasoning_effort="low",
    reasoning_format="hidden"). This replaced `qwen/qwen3.6-27b`, which
    turned out to be an invalid/hallucinated model string that had been
    silently failing (see Loose thread #1 below).
  Do NOT assume a model name from the original guide or from memory —
  Groq's available models can change. If a new model is needed,
  websearch Groq's current docs (console.groq.com/docs/models) before
  hardcoding a model string, the same way we caught the invalid model
  in M5.
Embeddings: sentence-transformers, model
  "sentence-transformers/paraphrase-multilingual-mpnet-base-v2", 768-dim
  (NOT 384 as the original guide's schema draft said — pgvector column
  is `Vector(768)`). Run via asyncio.to_thread to avoid blocking the
  event loop.
Auth: JWT access + refresh, httponly refresh cookie + separate
  readable CSRF cookie, bcrypt hashing, login lockout after repeated
  failures. Access token kept in module-level JS state
  (src/api/client.js), not localStorage.
Containerization: not yet confirmed whether Docker Compose is actually
  in use day-to-day — the user has been running the backend directly
  via a conda env (`immersely`) and Postgres separately. Don't assume
  `docker compose exec` is how commands get run; ask first if it matters
  for a given step (this bit us once in M5 — see conventions below).

===========================================================================
2. Backend code structure (confirmed real layout)
===========================================================================
backend/
  alembic/
    env.py          # async, autogenerate confirmed working against live DB
    versions/
  app/
    api/
      __init__.py    # EMPTY
      auth.py        # router = APIRouter(prefix="/auth", tags=["auth"])
      deps.py         # get_current_user (HTTPBearer + JWT decode)
      sentences.py    # router = APIRouter(prefix="/sentences", ...)
      srs.py          # router = APIRouter(prefix="/srs", ...)
      topics.py       # router = APIRouter(prefix="/topics", ...)
      scenes.py       # router = APIRouter(prefix="/scenes", ...)  <- M5
    core/
      config.py       # Settings(BaseSettings), see §3 below
      db.py            # engine, AsyncSessionLocal, get_db()
      limiter.py       # slowapi limiter, app.state.limiter
      security.py      # hashing, JWT create/decode, csrf token gen
      topics.py        # TOPICS constant list
    langchain_/
      topic_tagging.py     # tag_sentence(de_text) -> TopicTaggingResult
      scene_generation.py  # generate_scene(), verify_semantic_preservation() <- M5
    models/
      __init__.py     # explicitly imports+exports User, RefreshToken,
                       #   Sentence, Scene — Alembic autogenerate depends
                       #   on this file listing every model, or new
                       #   tables silently won't be picked up. When M6
                       #   needs a review_events table, it MUST be added
                       #   here too.
      base.py          # Base (declarative base) lives here, NOT in db.py
      user.py
      refresh_token.py
      sentence.py       # Sentence, incl. srs_* fields, embedding Vector(768)
      scene.py          # Scene <- M5
    schemas/
      user.py
      sentence.py
      tagging.py         # Topic enum built dynamically from TOPICS
      srs.py             # SRSState, Grade enums; GradeIn, SentenceWithSRS
      scene.py           # SceneRequest, SceneRead <- M5
      scene_generation.py # SceneLineOutput, SceneGenerationOutput,
                          #   SemanticVerificationResult,
                          #   SceneSemanticVerificationOutput <- M5
    services/
      auth.py           # register_user, login_user, refresh_tokens
      sentences.py       # CRUD, SentenceNotFoundError
      embeddings.py       # embed_text()
      tagging.py          # tag_sentence(), TaggingError
      srs.py              # update_srs() pure function, grade_sentence(),
                          #   list_due_sentences(), count_due_sentences()
      scenes.py            # get_scene_source_sentences(),
                          #   get_padding_sentences(), find_reusable_scene(),
                          #   create_scene(), get_or_create_scene(),
                          #   NoDueSentencesError  <- M5
      scene_verification.py # generate_verified_scene(),
                          #   SceneVerificationFailedError <- M5
    main.py               # FastAPI app, lifespan does a DB ping,
                          #   CORSMiddleware, slowapi limiter registered,
                          #   all routers included here
  tests/
    services/             # exists but largely unpopulated so far — M6's
                          #   grading logic is a good candidate for real
                          #   unit tests per the guide's Testing section
                          #   (deterministic, no DB/LLM needed for the
                          #   tier-mapping logic itself)

Exception-naming convention used throughout: plain Exception subclasses,
one per failure case, named descriptively (SentenceNotFoundError,
TaggingError, NoDueSentencesError, SceneVerificationFailedError, etc.),
caught in the API route layer and translated to HTTPException there.
There is NO global exception handler — every route does its own
try/except -> HTTPException. Follow this same pattern for M6's grading
errors.

===========================================================================
3. Settings / .env conventions (IMPORTANT — read before adding constants)
===========================================================================
The user has an explicit stated preference: "one source of truth" —
ANY tunable numeric/config value should live in Settings (app/core/config.py)
and be overridable via .env, NOT hardcoded inline, UNLESS it's a pure
internal safety valve (e.g. a retry-attempt cap), which can stay as a
module-level constant. When in doubt, ASK which one they want — this
came up twice in M5 and the user's answers differed each time
(scene_max_targets -> Settings; MAX_GENERATION_ATTEMPTS -> stayed a
module constant). Don't assume either way by default.

Current confirmed contents of app/core/config.py:

    from pydantic_settings import BaseSettings, SettingsConfigDict

    class Settings(BaseSettings):
        database_url: str

        jwt_secret_key: str
        jwt_algorithm: str = "HS256"
        access_token_expire_minutes: int = 30
        refresh_token_expire_days: int = 7
        groq_api_key: str

        scene_max_targets: int = 8
        scene_max_padding: int = 4
        scene_max_reviews_before_regen: int = 5

        model_config = SettingsConfigDict(env_file=".env")

    settings = Settings()

Pydantic v2 pattern used throughout: `ConfigDict(from_attributes=True)`
on Read schemas (not the old `orm_mode`/`class Config` style, except in
one older file, app/schemas/user.py, which still uses `class Config:
from_attributes = True` — a minor inconsistency, not yet cleaned up).

===========================================================================
4. Frontend code structure (confirmed real layout)
===========================================================================
frontend/
  src/
    api/
      client.js     # apiFetch(), refreshAccessToken(), setAccessToken(),
                    #   setUnauthorizedHandler(). UPDATED in M5 to attach
                    #   `.status` to every thrown Error (see §6 below) —
                    #   this is now the pattern for reading HTTP status
                    #   codes on the frontend; use err.status, not
                    #   string-matching err.message.
      sentences.js
      srs.js         # getDueCount, getDueSentences, gradeSentence(id, grade)
                    #   <- gradeSentence ALREADY EXISTS, posts to
                    #   /srs/{sentence_id}/grade. M6's new grading/
                    #   correction-check endpoint is DIFFERENT from this
                    #   — this one just applies a manually-chosen SRS
                    #   grade; M6 needs a new endpoint that CHECKS a
                    #   user's typed German answer and SUGGESTS a tier
                    #   + grade. Don't confuse the two.
      topics.js
      scenes.js       # requestScene(topic, maxTargets) -> POST /scenes <- M5
    context/
      AuthContext.jsx   # user, isLoading, login, register, logout
      TopicsContext.jsx  # { topics, isLoading } — must wrap any page
                        #   that calls useTopics(), e.g. via
                        #   <TopicsProvider><Page /></TopicsProvider>
                        #   in App.jsx's route element
    features/
      auth/            # LoginPage, RegisterPage, ProtectedRoute,
                       #   RedirectIfAuthenticated
      sentences/        # SentencesPage, SentenceForm, SentenceListItem,
                       #   TagEditor
      session/           # DueTodayBadge, ScenePage, SceneView  <- M5
    components/
      Layout.jsx         # not yet reviewed in detail this project —
                        #   ask to see it if M6 needs new nav entries
    pages/
      Home.jsx
    App.jsx              # BrowserRouter, routes nested under
                        #   ProtectedRoute > Layout; /review route added
                        #   in M5, wraps ScenePage in its own
                        #   TopicsProvider (separate mount from
                        #   /sentences' TopicsProvider — see Loose
                        #   thread #2)
    index.css             # single global stylesheet, CSS custom
                        #   properties in :root (--color-primary,
                        #   --color-surface, --color-border, --radius,
                        #   --shadow-sm, etc). No Tailwind, no CSS
                        #   modules. Class-name convention:
                        #   kebab-case, BEM-ish modifiers with `--`
                        #   (e.g. .scene-line--target, .status-pill--ok).
                        #   Match this exactly for any new M6 UI.

No test framework installed on the frontend (no Vitest/RTL) as of this
handoff. Component validation was done by TEMPORARILY rendering new
components inside Home.jsx with hardcoded fake data, eyeballing the
result in the browser, then reverting Home.jsx back to its original
form. Expect to use the same approach for M6's grading-feedback UI
unless the user sets up a test framework first — ask if they want to
before assuming this workaround again.

===========================================================================
5. What M5 (Scene generation) delivered — DONE, confirmed working
===========================================================================
Backend:
- Scene model (app/models/scene.py) + Alembic migration, applied.
- get_scene_source_sentences(): reuses app/services/srs.py's
  list_due_sentences() for targets; new get_padding_sentences() for
  non-due same-topic flavor sentences (random selection, capped by
  settings.scene_max_padding).
- LangChain scene-generation chain (app/langchain_/scene_generation.py):
  generate_scene() produces SceneGenerationOutput (list of lines, each
  with speaker/text_de/text_en/target_sentence_id). temperature=0.7
  (creative, on purpose — contrast with tagging's temperature=0).
- Two-layer verification (app/services/scene_verification.py):
  6a check_structural_completeness() — deterministic, checks every
    target id appears exactly once (catches missing AND duplicated).
  6b verify_semantic_preservation() — separate LLM call (temperature=0)
    checking each claimed line's meaning actually matches its target.
- generate_verified_scene() orchestrates: generate -> 6a -> 6b -> retry
  up to MAX_GENERATION_ATTEMPTS = 3 (module constant, by user's choice).
  IMPORTANT: the retry loop wraps BOTH the generation call AND the
  verification call in try/except, because we hit a real Groq tool-call
  formatting failure (BadRequestError) on a 7-target scene during
  testing — the model occasionally mis-emits the structured-output tool
  name under load. Any new LLM-calling retry loop in M6 should follow
  this same defensive pattern (catch broad Exception around each LLM
  call inside the retry loop, not just around "business logic" checks).
- Regeneration-policy caching (app/services/scenes.py):
  find_reusable_scene() — reuse if same due-sentence-id-set AND
  review_count_since_generated < settings.scene_max_reviews_before_regen.
  get_or_create_scene() — the single entry point routes/other services
  should call; encapsulates reuse-or-generate-and-persist.
  NOTE: review_count_since_generated is NOT incremented anywhere yet —
  that's explicitly deferred to the review/grading flow (M6/M7's job),
  since incrementing it is a consequence of REVIEWING a scene, not of
  fetching one. M6 or M7 needs to add something like
  increment_scene_review_count(db, scene_id) and call it after a grade
  is recorded.
- POST /scenes route (app/api/scenes.py): NoDueSentencesError -> 404,
  SceneVerificationFailedError -> 502. Rate-limited 10/minute (same as
  sentence creation), since it's an LLM-calling endpoint.

Frontend:
- SceneView (static, presentational, no interactivity) — renders
  text_de/text_en split by newline, marks target-line positions (via
  line_sentence_map's values) with a "review" badge + tinted
  background. Deliberately NOT interactive — that's M7.
- ScenePage — topic picker (from TopicsContext) + "Get scene" button +
  three states: loading, friendly "nothing due" empty state (via
  err.status === 404), and success (renders SceneView).
- Route: /review, wrapped in its own TopicsProvider, added to App.jsx.

Full M5 Definition of Done from the original guide (repeated here since
it's still the authoritative spec): "given a topic with due sentences,
the API returns a cached-or-freshly-generated scene that verifiably
contains every target sentence; a second call with the same due set
reuses the cache." — Confirmed at the service layer directly (cache-miss
generated+persisted in ~1s for a single-target scene, cache-hit
returned the same scene id in 0.07s) AND via the real /review page in
the browser. Not yet load-tested via raw HTTP (curl/httpie with a real
bearer token) — that's optional polish, not a gap, since the route is a
thin wrapper around the already-proven service layer.

===========================================================================
6. Loose threads NOT yet resolved (carry into M6 or handle first)
===========================================================================
1. TOPIC-TAGGING BACKFILL NEEDED. During M5 we discovered
   app/langchain_/topic_tagging.py was using an invalid Groq model
   string (`qwen/qwen3.6-27b`, which does not exist — confirmed via
   Groq's own docs), and topic tagging has a catch-and-print
   (TaggingError -> print(), not raised) fallback in
   services/sentences.py's create_sentence(), so tagging failures were
   being silently swallowed. We fixed the model string (now
   openai/gpt-oss-20b) and confirmed tagging works again, but a real
   chunk of the user's existing sentences in the DB still have
   topics=[] from before the fix (confirmed directly via a DB query:
   several rows including "Ich bin sehr hungrig.", "Der Himmel ist
   blau.", "Testsatz 1/2", "Der Hund läuft" all show topics=[]).
   This needs a backfill script/endpoint: find all sentences with
   topics = '{}' for a user (or all users), re-run tag_sentence() on
   each, and update. Not part of M6's spec, but affects real usage of
   scene generation (a sentence with no topic can never be picked up
   by get_scene_source_sentences' topic filter, so it'll never appear
   in a generated scene) and directly affects grading test data too, so
   it's worth fixing before or during M6, or at least flagging to the
   user again if they want it scheduled explicitly.

2. TopicsProvider double-mounts. /sentences and /review each wrap
   themselves in their own <TopicsProvider>, meaning /topics gets
   fetched twice as the user navigates between them (each mount is a
   fresh, independent context instance). Harmless (just a mildly
   wasteful extra GET /topics call) but not ideal. The clean fix would
   be lifting <TopicsProvider> up to wrap the whole <Layout> route in
   App.jsx once, rather than per-page. Low priority; mention it if M6's
   UI also needs topics data (it likely will, e.g. for a topic-scoped
   review-session picker) so we don't add a THIRD independent mount on
   top of the existing two without at least considering the fix first.

===========================================================================
7. M6 scope — Correction / Grading Engine (from the original project guide)
===========================================================================
Reproduced verbatim from the original guide, since it's still the
authoritative source for M6's design:

--- §2.3 Correction / grading — lenient, three tiers ---
Graded on correctness of German + meaning, not on similarity to the
stored sentence's exact wording.

Tier            Definition                                  What the user sees
correct         Valid German, right meaning, any phrasing    checkmark confirmation only
almost_correct  Recognizable attempt with a fixable          Their sentence, minimally
                grammar error                                corrected, brief diff note
incorrect       Broken grammar or wrong meaning               The stored target sentence
                (folded into one tier)                        shown as the model answer

A separate, independent check — rule_practiced (bool) — only evaluated
when tier is correct or almost_correct: does the answer actually use the
grammar rule this sentence was saved to drill? If not, this is shown as a
soft, non-blocking note alongside the model sentence — it never changes
the tier and never blocks progress.

Grading is tied to tier only. rule_practiced is informational and
never affects suggested_grade or the SRS update.

suggested_grade mapping:
  correct -> good (or easy if the match is very close/fluent)
  almost_correct -> hard
  incorrect -> again

The user can always override the suggested SRS grade before continuing.

--- M6 milestone block from the guide ---
M6 — Correction / grading engine
  Input: M4 (SRS engine), M5 (scene context optional — isolated mode
    doesn't need it).
  Backend output: LangChain call implementing the three-tier lenient
    grading prompt + independent rule_practiced check, structured JSON
    output validated against a Pydantic model,
    POST /review/{sentence_id}/check endpoint.
  Frontend output: the tiered feedback UI: correct confirmation,
    almost-correct diff, incorrect model-answer display, soft rule note.
  Security/Auth output: validate/guard malformed LLM JSON output before
    trusting suggested_grade; input sanitization on user answers.
  Definition of done: submitting answers across a set of test cases
    (clearly correct, correct-but-different, near-miss, wrong meaning,
    correct-but-rule-avoided) returns the expected tier and note each
    time.

--- review_event schema, from §4 of the guide (not yet created in the
    real DB — this is planned, not confirmed existing) ---
review_events (
  id UUID PK,
  user_id UUID FK -> users.id,
  sentence_id UUID FK -> sentences.id,
  scene_id UUID FK -> scenes.id NULL,
  mode TEXT NOT NULL,               -- isolated | cloze_in_scene | free_production
  user_input TEXT,
  tier TEXT NOT NULL,               -- correct | almost_correct | incorrect
  corrected_input TEXT,
  rule_practiced BOOLEAN,
  grade TEXT NOT NULL,              -- again | hard | good | easy
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
Note: the guide lists review_events as part of M7's orchestration
output ("plus review_events logging on every grade"), but the /review/
{sentence_id}/check endpoint in M6 is naturally where tier and
suggested_grade get computed — worth deciding together, as the first
real design question of this milestone, whether M6 should already
create the review_events table and log each check, or whether M6
should stay pure (compute-only, no persistence) and defer all logging
to M7 as the guide's milestone split implies. Don't assume either way —
this is exactly the kind of design decision that shaped M5 (e.g. the
target-tracking-in-padding question) and is worth surfacing explicitly
at the start of the M6 conversation.

===========================================================================
8. Known environment gotchas worth remembering
===========================================================================
- FastAPI/Starlette versions in use are NEWER than what most training
  data assumes (FastAPI 0.141.1, Starlette 1.6.0, confirmed via `pip
  show`). Since FastAPI ~0.137, `include_router()` no longer flattens
  child routes into `app.routes` — each becomes a lazy `_IncludedRouter`
  wrapper with no `.path` attribute. If you ever need to introspect
  registered routes for debugging, don't naively iterate `app.routes`
  checking `hasattr(route, 'path')` — you have to walk into
  `route.original_router.routes` recursively. This cost real time in
  M5; don't repeat the mistake.
- Postgres availability has flickered mid-session before (a
  ConnectionRefusedError on app startup was just Postgres being down at
  that moment, unrelated to any code change) — if a DB-touching command
  fails with a connection error, check whether Postgres is simply not
  running before assuming a code bug.
- The user's browser blocks pasting into devtools console by default
  (Chrome's self-XSS guard) — don't rely on "paste this into the
  console" as a validation method; prefer file-based validation
  (temporary component rendering, terminal python -c snippets) instead.
