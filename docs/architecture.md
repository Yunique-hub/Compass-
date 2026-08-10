# Compass 2.5 Architecture

## Runtime boundary

```text
CompassEngine.run
  → SAFETY
  → restore archive + structured/semantic memory
  → extract Known facts and determine intent/stage
  → select one primary business path
  → execute handler
  → extract Evidence and state changes
  → persist canonical state and archive
  → normalize and render response
```

`scripts/core/turn_context.py` defines the shared `TurnContext`. It replaces scattered cross-module dictionaries at the engine boundary while leaving stable business payloads compatible.

## Major-agnostic growth model

`scripts/academic/major_engine.py` parses natural-language majors into an `AcademicProfile`. The resolution order is:

```text
curated major profile → discipline-family fallback → other/emerging fallback
```

The curated data in `reference/academic_profiles.json` accelerates common cases; it is not a support whitelist. Unknown majors still receive a plan and an explicit verification caveat. Double majors remain separate, major changes retain `previous_majors`, and cross-major targets do not overwrite the current academic background.

Major recognition first classifies the mention and extracts a declaration span. Topic, target role and target domain never become a durable Major by alias containment. Structured profile persistence applies a field allowlist and a separate explicit/confirmed source gate.

`scripts/academic/pathway_engine.py` resolves the user's destination independently from the major. `scripts/core/growth_context.py` then composes academic background, current stage, pathway/role, constraints, competencies and evidence types. Planning, Tutor and Assessment consume this same context:

```text
Academic Profile ─┐
Stage ────────────┤
Pathway / Role ───┼→ GrowthContext → Plan → Tutor → Assessment → Evidence
Constraints ──────┤
Known Evidence ───┘
```

Planning has an academic axis and an outcome axis. Tutor examples and exercises are selected by domain, while Assessment emits the exercise's expected evidence type rather than a universal `project` type.

`scripts/competency/domain_intelligence.py` defines shared competency semantics and focused overlays. `scripts/learning/domain_task_factory.py` turns those definitions into 1—3 hour domain-authentic tasks. Natural-language submissions are matched criterion by criterion before Evidence or mastery can change.

The deterministic `intent_router` chooses intent only. Business behavior remains in existing modules:

- Career and Planning: `scripts/career/`, `scripts/core/goal_planner.py`
- Recruitment and Gap: `scripts/recruitment/`, `scripts/competency/`
- Tutor and Assessment: `scripts/learning/`, `scripts/growth_orchestrator.py`
- Review and Research: `scripts/review/`, `scripts/research/`

The engine groups these behind small handler methods. Handlers do not own final archive persistence or final response formatting.

## Memory and evidence

SQLite remains canonical. Existing tables and 2.x data are retained; no destructive migration is required. Archive loading accepts prior 2.x versions and preserves unknown fields under `extensions`.

Only user-explicit, confidence-1.0 extracted facts enter automatic profile-fact memory. Inferences remain in turn context until confirmed. Structured writes are no-ops when merged data is unchanged. Semantic memories receive a stable UUID derived from user, type and canonical content, so equivalent writes replace instead of append.

Competency uses the following boundary:

```text
Claim → Evidence → Assessment → Confidence
```

Claimed skills remain separate from verified levels. Passing observable assessment criteria can create verified Evidence and update Competency; a user statement alone cannot.

## Response boundary

`scripts/core/response_builder.py` owns the canonical response model:

```text
current_judgment, current_goal, do_now, why, next_step, questions
```

Legacy handlers may provide additional `mentor_sections` and `details`; normalization guarantees the shared fields without forcing every simple answer into a long Markdown template.

## Release boundary

- skill: runtime instructions/code/resources/licenses only; no tests, dev reports or vendor source.
- dev: runtime plus tests, fixtures, scripts and development documentation; no vendor source.
- full: dev plus vendor snapshots and upstream audit resources.

`scripts/validate_package.py` validates structure, metadata/version alignment, JSON/schema, imports, six behavioral invariants—including finance, law and unknown-major leakage checks—and ZIP content rules. `scripts/pack_skill.py` builds a package only after directory validation and validates the resulting ZIP again.
