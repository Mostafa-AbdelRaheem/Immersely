# German Scene-Based SRS — M5 Handoff (Scene Generation)

I'm continuing a project from previous conversations. I'm building the
German Scene-Based SRS app described in the attached project guide,
milestone by milestone, teaching myself with you as a teacher/pair-programmer.

## PROCESS — follow this for every milestone, exactly as below

1. **TEACH FIRST.** Before any code, explain the concept for the piece
   we're about to build — what it is, why it's needed, how it fits the
   rest of the stack, and what problem it solves in this specific app.
2. **CODE IN CHAT, NOT FILES.** Give me code as text to type/paste myself
   — never create files or downloads on my behalf.
3. **ONE FILE AT A TIME.** After giving me a file to add or a specific
   edit to make, stop and wait for me to confirm it's in place and
   working before proposing the next file. Do not bundle multiple files
   into one response, and do not create or edit adjacent files "while
   you're at it" unless I explicitly asked for that file.
4. **NEVER ASSUME A FILE EXISTS OR IS ALREADY IN MY REPO.** If I pasted
   you a file's contents earlier in this conversation, that does not mean
   it's actually saved in my project yet. I will tell you when I've
   created or edited a file. If you're unsure what my current file looks
   like, ask me to paste it — don't build on a remembered/assumed version.
5. **WHOLE FILES, NOT FRAGMENTS.** When giving me a file to edit, either
   give me the complete file to paste over the old one, or an explicit
   before/after diff — never a bare "changed part" I have to merge myself.
6. **EXPLAIN TRADEOFFS** whenever there's more than one reasonable
   approach — don't silently pick one. When you make a judgment call on my
   behalf, name it explicitly as a call you made and why, and ask before
   restructuring anything (routing, folder layout, CSS architecture, etc.)
   even if you think it's "best practice."
7. **CHECK UNDERSTANDING** at natural checkpoints with real questions, not
   just "does it run."
8. **USE YOUR TOOLS TO VERIFY, NOT TO PRODUCE DELIVERABLES.** Sandbox
   testing/verification is welcome, but state plainly what was and wasn't
   actually verified, and against what (a real DB/server vs. a sandbox
   stand-in). Don't imply something is fully proven when only a stand-in
   was tested.
9. **CONFIRM DoD BEFORE STARTING, AND BEFORE MOVING ON.** Confirm the
   milestone's input and Definition of Done up front. Break the milestone
   into numbered sub-steps and track progress against them. Confirm the
   DoD is actually met — via me testing/pasting real evidence — before
   moving to the next milestone.
10. **REAL EVIDENCE, NOT ASSUMED SUCCESS.** Every claimed "it works" gets
    backed by pasted terminal output, DB query results, or Network-tab/HTTP
    status codes — not just "yes it works."
11. **VERIFY CURRENT BEST PRACTICE VIA WEB SEARCH** before committing to a
    library/model/API choice where training data is likely stale (this has
    burned us before — see M1/M3 notes below). Don't rely on memory for
    anything version- or maintenance-status-sensitive.
12. **Backend follows the MVP structure in the guide's §5 exactly**:
    routes → services → models. Services raise plain Python exceptions
    defined in the relevant service file — never `HTTPException`. Routes
    catch those exceptions and translate them to HTTP status codes. Apply
    this to every new service (scene generation included).
13. **Keep each milestone scoped to exactly what it needs** — don't build
    ahead. Where a real scoping decision exists, present it explicitly as
    a choice rather than deciding for me.
14. **If I say something feels wrong or is frustrating me, stop, say so
    plainly, and ask what I want instead** — don't keep building in the
    same direction hoping it resolves itself.

## CURRENT STATE

### M0 — scaffolding
Confirmed from what I've seen in this conversation: FastAPI app
(`app/main.py`) with a `/health` endpoint, CORS configured for
`http://localhost:5173`, async SQLAlchemy engine, Alembic wired for
migrations against a shared declarative `Base` (`app/models/base.py`).
**Not directly verified in this conversation — ask me to paste
`docker-compose.yml` and `app/core/config.py` if you need exact DB
connection details, container names, or ports.**

### M1 — auth & user accounts (complete)
Verified from real pasted code in this conversation:

- `users` table: UUID PK, unique `email`, `hashed_password`, `created_at`.
- `app/models/refresh_token.py`: `RefreshToken` stores a **hash** of the
  refresh token (never the raw token) — `token_hash`, `user_id` FK,
  `expires_at`, `revoked_at` (nullable timestamp, not a bool — gives an
  audit trail), `created_at`.
- `app/services/auth.py`: `register_user`, `login_user`, `refresh_tokens`
  — all raise plain exceptions (`EmailAlreadyRegisteredError`,
  `InvalidCredentialsError`, `InvalidRefreshTokenError`,
  `AccountLockedError`), never `HTTPException`. Per-email login lockout
  via an in-memory `_failed_login_attempts` dict — 5 failures within a
  60-second window locks that email out (`LOCKOUT_THRESHOLD`,
  `LOCKOUT_WINDOW`), independent of any IP-based limiting.
- Refresh token **rotation with reuse detection**: every refresh call
  marks the presented token's row `revoked_at` and issues + stores a new
  one; reusing an already-rotated token is rejected.
- Cookie-based refresh delivery: access token returned in the JSON body
  only; refresh token in an `httpOnly`, `SameSite=Lax` cookie scoped to
  `Path=/auth`. CSRF via double-submit cookie — a JS-readable
  `csrf_token` cookie (`Path=/`), and `/auth/refresh` requires a matching
  `X-CSRF-Token` header.
- Cookies currently set `secure=False`, commented "True once served over
  HTTPS" — must change before real deployment.
- `app/api/deps.py`: `get_current_user` via `fastapi.security.HTTPBearer`
  — decodes the access token, checks the `type` claim is `"access"` (not
  `"refresh"`), loads the `User`. Routes become protected via
  `current_user: User = Depends(get_current_user)`.
- Rate limiting on auth endpoints via `slowapi` (`app/core/limiter.py`, a
  shared `Limiter` instance imported wherever needed).
- **Not directly verified in this conversation** — password hashing
  library/version pin, exact JWT expiry durations, and JWT signing
  algorithm live in `app/core/security.py`, which I haven't seen in this
  thread. If those details matter for M5 (they shouldn't), ask me to
  paste that file.

### M2 — sentence CRUD (complete)
Verified from real pasted code:

- `app/models/sentence.py` (base, before M3/M4 additions): `id`,
  `user_id` FK, `de`, `en`, `created_at`, `updated_at`.
- `app/services/sentences.py`: single `SentenceNotFoundError` covers both
  "doesn't exist" and "exists but belongs to another user" (deliberate
  404-for-both convention, avoids leaking existence of other users' data).
  `get_sentence` is the one place ownership is checked — filters by
  `user_id` in the query itself. `update_sentence`/`delete_sentence` both
  call `get_sentence()` first rather than duplicating that check.
- `app/api/sentences.py`: full CRUD behind `Depends(get_current_user)`,
  each route translating service exceptions to `HTTPException`.
- Frontend: `src/api/sentences.js` (thin `apiFetch` wrappers),
  `SentenceForm.jsx`, `SentenceListItem.jsx`, `SentencesPage.jsx` — all
  confirmed present and working (we styled these during M4's UI pass).

### M3 — embeddings & topic tagging (complete)
Verified from real pasted code:

- `app/services/embeddings.py`: embedding model is
  **`sentence-transformers/paraphrase-multilingual-mpnet-base-v2`**,
  producing **768-dim** vectors — confirmed by `Sentence.embedding` being
  `Vector(768)` in the model (not the 384 the original guide's draft
  schema mentioned — this was a deliberate adjustment made in M3).
  Lazily loaded as a module-level singleton; the blocking `.encode()` call
  is offloaded via `asyncio.to_thread` so it doesn't block the event loop.
- `app/services/tagging.py` wraps `app/langchain_/topic_tagging.py` (not
  seen directly in this conversation), raising `TaggingError` — tagging
  failures are caught in `create_sentence` and **never block sentence
  creation** (best-effort, with a `print()` left in for diagnosing silent
  failures — flagged in the code as temporary, worth removing at some
  point).
- `app/schemas/tagging.py`: `Topic` enum built dynamically from a
  `TOPICS` list (`app/core/topics.py`, not seen directly) so the enum
  can't drift from the source list. `TopicTaggingResult` schema includes
  `topics`, `grammar_tag` (free-text snake_case label), and
  `suggested_new_topic` (for topics that don't fit the fixed list).
- `Sentence.topics` is `ARRAY(Text)`, `Sentence.grammar_tag` is plain
  `Text`.
- Frontend: `TagEditor.jsx`, topic filter in `SentencesPage.jsx`,
  `TopicsContext.jsx` — all confirmed present and styled.

### M4 — SRS engine (complete, fully verified against real Postgres)

- Migration `8099e684fe80` (down_revision `b5feca403bbe`) — six `srs_*`
  columns on `sentences` (`srs_due`, `srs_interval_days`, `srs_ease`,
  `srs_reps`, `srs_lapses`, `srs_state`), a `CheckConstraint` on
  `srs_state`, and an `(user_id, srs_due)` index. **`alembic upgrade head`
  run and confirmed working** (this fixed a real `UndefinedColumnError`
  we hit live).
- `app/services/srs.py`:
  - `SRSFields` (frozen dataclass) + `update_srs(fields, grade, now)` —
    pure, no I/O, never mutates its input. Three phases:
    `_handle_again` (AGAIN, any phase — resets to the first learning
    step; only counts as a lapse if the card had already graduated to
    `review`), `_handle_learning_step` (NEW/LEARNING/RELEARNING — two
    steps, `[10 min, 1 day]`, before graduating), `_handle_review`
    (interval grows by `× ease` on GOOD, more cautiously on HARD, with a
    bonus on EASY).
  - `reps` deliberately does double duty: while learning, it's the
    step-index counter; on graduating it resets to `1` and becomes the
    review-phase rep count. No separate "learning step" column exists —
    this was a conscious tradeoff to stay within the schema §4 already
    defined, not an oversight.
  - `grade_sentence`, `list_due_sentences`, `count_due_sentences` bridge
    `SRSFields` to the real `Sentence` ORM rows and the DB session.
  - `Grade` and `SRSState` enums live in `app/schemas/srs.py` (not
    `services/srs.py`) — matching the existing convention from
    `app/schemas/tagging.py` (`Topic` enum lives in schemas, not
    services).
  - **`tests/services/test_srs.py` — 15/15 passing**, confirmed run for
    real in the project's own conda env (`immersely`) with
    `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest
    tests/services/test_srs.py -v` (that env var is needed because ROS2
    packages on this machine leak incompatible pytest plugins otherwise —
    unrelated to this project, just a local machine quirk worth
    remembering).
- `app/api/srs.py`: `GET /srs/due` (topic filter via
  `Sentence.topics.any(topic)` — Postgres-specific array `ANY()`),
  `GET /srs/due/count`, `POST /srs/{sentence_id}/grade` — all three
  **smoke-tested live** against the real backend/DB, including a
  `new → learning` grade transition observed directly.
- Frontend: `src/api/srs.js` (`getDueCount`, `getDueSentences`,
  `gradeSentence` — thin `apiFetch` wrappers, matching `sentences.js`'s
  pattern exactly), `src/features/session/DueTodayBadge.jsx` (polls
  `getDueCount` on mount, shows `…` while loading, nothing on error),
  `src/components/Navbar.jsx` + `src/components/Layout.jsx` (nav links,
  the due-count badge, logout — wraps every protected route),
  `src/index.css` (covers every className already used across
  sentences/tags/forms/auth/navbar). `App.jsx` nests `Layout` inside
  `ProtectedRoute`, above `Home`/`/sentences` — login/register stay
  outside `Layout` (no navbar while logged out, deliberate).

**Known gaps carried forward, not yet addressed:** no `ondelete=` cascade
on `sentences.user_id` FK (flagged in M2, still not a real issue — no
user-deletion feature exists yet).

## M5 — Scene generation (from the original project guide)

**Input:** M3 (embeddings/topics), M4 (SRS engine — due sentences).

**Concept (§2.1–2.2 of the original guide):**
- Sentences are saved once; review happens either as isolated sentences or
  inside a generated scene/dialogue for a topic. Scene composition varies
  each time even when the topic repeats.
- SRS state lives on the sentence, never on the scene. Scenes are
  disposable, regeneratable views over due sentences.
- **Retrieval:** due sentences for a topic (via M4's `list_due_sentences`)
  + optional non-due sentences from the same topic for natural flow
  ("padding").
- **Generation:** LLM weaves target sentences into a short dialogue,
  preserving each target close to verbatim (minor conjugation allowed).
- **Verification:** a check step confirms each target sentence's content
  actually appears in the generated scene before caching; regenerate on
  failure.
- **Padding rule:** padding sentences appear in the dialogue for flavor
  only — never presented as review items, never graded.
- **Regeneration policy:** a cached scene is reused until either (a) the
  due-sentence set for that topic changes, or (b) the scene's age exceeds
  N reviews — whichever comes first.

**Backend output (per the guide's M5 milestone):**
- `scenes` table + migration (`id`, `user_id`, `topic`, `sentence_ids`
  (targets covered), `padding_sentence_ids`, `text_de`, `text_en`,
  `line_sentence_map` JSONB, `generated_at`,
  `review_count_since_generated`, `model`).
- LangChain (or LangGraph) chain: retrieve due (+ padding) sentences →
  generate scene → verify target inclusion → retry on failure → cache;
  regeneration policy implemented.

**Frontend output:** scene rendering (static view first — full
interactivity comes in M7).

**Security/Auth:** server-side-only Groq key, input sanitization of
sentence text before prompting, timeout/retry handling on LLM calls.

**Definition of done:** given a topic with due sentences, the API returns
a cached-or-freshly-generated scene that verifiably contains every target
sentence; a second call with the same due set reuses the cache.

**Special note for this milestone:** M5 touches an area where training
data is very likely stale — LangChain's current integration pattern for
Groq (package name, import path, whether the API has changed recently).
Per PROCESS rule 11, web-search and confirm current best practice for this
before proposing the sub-step breakdown, the same way M3's embedding-model
choice was verified rather than assumed.

## Do not assume file contents — ask for them

Everything above is an accurate recap of what was *shown* to me in the
conversation where this was written — it is not a substitute for the
actual files. Before writing any code:

- **Ask me by name for the specific file(s) you need to see**, one at a
  time, instead of guessing what's in them.
- Likely candidates, depending on what you're working on at each step:
  `app/models/sentence.py` (current, with SRS fields), `app/services/srs.py`
  (for `list_due_sentences`), `app/schemas/tagging.py`, anything already
  in `app/langchain_/`, `app/core/config.py` (Groq key/model config),
  `app/core/security.py` and `docker-compose.yml` (the two files flagged
  above as unverified in this thread) — but treat this as a hint list,
  not a green light to assume their contents.
- If I reference a file you haven't seen yet, stop and ask for it rather
  than continuing as if you already know what's in it.

Please start by confirming M5's input and Definition of Done against the
guide, doing the LangChain/Groq web-search check, then break M5 down into
numbered sub-steps the same way M1–M4 were done, and teach me the first
concept before I write anything.
