# Instruction Set Evaluation — Design & Implementation

A two-tier evaluation system for the agent instruction sets in this repository.
Tier 1 analyses the **documents**; Tier 2 measures what the documents actually
**cause an agent to do**. Both are needed: Tier 1 is fast, deterministic, and
catches structural defects; Tier 2 is slow, expensive, and is the only tier that
produces evidence a change to an instruction set was an improvement.

**Status:** Tier 1 is implemented — 18 deterministic checks, all validated by
fault injection. 7 judge-backed checks are registered as stubs. Tier 2 is
designed but not built. See §11.

---

## 1. Scope & Non-Goals

**In scope.** The instruction set under `ModernizationHarness/` — a folder of
Markdown files that together define a multi-stage agent pipeline. The system is
set-agnostic: it discovers stages from filenames and content rather than
hardcoding the harness's structure, so a variant set can be scored on the same
axes for regression comparison.

**Not in scope.**

- Judging whether the *methodology* is right. The eval measures internal
  coherence and observed behaviour, not whether a six-stage modernization
  pipeline is the correct approach.
- Style, prose quality, or readability of the instructions.
- Grading the legacy application in `sample_legacy_app/`.

**A stated non-goal: minimizing tokens.** Instruction sets tolerate — and often
require — redundancy that prose does not. `AGENTS.md` restating invariants that
also appear in stage files is deliberate, because the stage files are not in
context during ad-hoc chat. Token counts are reported as a **budget signal**,
never as a score to optimise downward. Group A emits metrics, not findings, and
never gates CI unless the operator explicitly passes `--budget-warn`.

---

## 2. Architecture

```
                    ┌──────────────────────────────────────┐
   instruction set  │  TIER 1 — Static Analysis  [BUILT]   │
   ───────────────► │                                      │
                    │  parse ─► rule extraction ─► checks  │──► findings.json
                    │    │         (stub)          │       │    report.md
                    │  [det]                  [det]+[llm]  │
                    └──────────────────────────────────────┘
                                      │
                    ┌─────────────────▼────────────────────┐
   fixture app      │  TIER 2 — Behavioural  [DESIGNED]    │
   ───────────────► │                                      │
                    │  run stages ─► grade outputs         │──► scores.json
                    │       │             │                │    report.md
                    │   [agent runs]  [det]+[llm]          │
                    └──────────────────────────────────────┘
```

Tier 1 runs on every commit. Tier 2 runs on demand and on release candidates,
because it costs real money and wall-clock time.

The two tiers share one substrate: a **rule record** model (§4), an **LLM judge**
harness (§7.2), and a **findings** format (§8).

---

## 3. Severity Model

Every finding carries one of three severities. This is shared by both tiers.

| Severity | Meaning | Gate |
|---|---|---|
| **blocker** | The defect makes an instruction unenforceable or contradictory. An agent following the set will do the wrong thing or stall. | Exit code 1 |
| **major** | Real inconsistency that will cause drift or confusion, but an agent can still proceed. | Reported, exit 0 |
| **minor** | Hygiene, convention, or smell. May be intentional. | Reported, suppressible |

Findings carry **stable IDs** — `sha1(check + file + subject)[:10]` — so a baseline
file suppresses a known-acceptable *instance* without disabling the check. IDs
are deliberately independent of line numbers, so editing a file above a finding
does not orphan its suppression.

---

## 4. The Rule Record

The conflict-detection group and several coherence checks operate on atomic
**rule records** extracted from prose. **Not yet implemented** — it is the gate
for Phase 3, and every judge-backed stub depends on it.

```python
Modality = Literal["MUST", "MUST_NOT", "SHOULD", "SHOULD_NOT", "MAY"]

class Rule(BaseModel):
    id: str               # sha1(file + section + normalized_text)[:10] — stable
    file: str             # repo-relative
    section: str          # nearest enclosing heading
    line: int             # 1-indexed, for clickable citation
    actor: str            # from the ACTORS vocabulary below
    modality: Modality
    subject: str          # from the SUBJECTS vocabulary below
    predicate: str        # the action, normalized to a short verb phrase
    condition: str | None # the guard, if the rule is conditional
    verbatim: str         # source text, unmodified
```

Extraction is a structured-output call (§7.2). The two controlled vocabularies
are what make clustering and conflict detection tractable — the extractor is
constrained to these via schema `enum`, so it cannot invent a subject.

**ACTORS** — `stage-0` … `stage-5`, `any-agent` (rules from `AGENTS.md` that bind
every session), `developer` (rules describing what the human does).

**SUBJECTS** — the artifacts and state paths the pipeline acts on:

```
legacy-source           INTAKE.md               AGENTS.md
PROJECT_CONTEXT.md      requirements:business   requirements:functional
requirements:technical  design:hld              design:lld
plan                    target-code             review-report
state:stages            state:phases            state:edits
state:changeLog         state:reviews           state:progress
git:branch              git:commit              git:pr
secrets                 database-schema         constraints
```

Adding a subject is a one-line vocabulary change; the clustering and conflict
checks pick it up automatically.

**Caching.** Extraction is the expensive step and most files are unchanged
between runs. Rule records cache to `eval/.cache/rules/<sha256>.json`, keyed by
file content, and are re-extracted only when the hash changes.

---

## 5. Tier 1 — Static Analysis

25 checks in six groups. Status is one of **built** (deterministic, shipping),
**stub** (registered, reports as not-implemented, needs Phase 3/4), or
**experimental** (off unless `--include-experimental`).

Run `uv run run.py --list-checks` for the live registry.

### 5.A Size & Budget — all built

Emits metrics, never findings (except the opt-in `--budget-warn` ceiling).

| ID | Check | Status | Output |
|---|---|---|---|
| **A1** | Per-file token count | built | Token count for every `.md` in the set |
| **A2** | Per-section token count | built | Tokens per top-level heading, as share-of-file |
| **A3** | Composite per-stage budget | built | What a single stage run loads (below) |
| **A4** | Growth delta vs git HEAD | built | Per-file token diff against the previous commit |

**A3 is the number that matters.** A stage run does not load one file — it loads
a composite, modelled in `checks/size.py::STAGE_LOADOUTS`:

| Stage | Loads |
|---|---|
| 0 | `AGENTS.md` + `0_PROJECT_CONTEXT_INSTRUCTIONS.md` + `INTAKE.md` |
| 1 | `AGENTS.md` + `1_REQUIREMENTS_…` + `PROJECT_CONTEXT.md` + `state.json` |
| 2 | `AGENTS.md` + `2_DESIGN_…` + context + 3 requirements docs + `state.json` |
| 3 | `AGENTS.md` + `3_PLAN_…` + context + designs + requirements + `state.json` |
| 4 | `AGENTS.md` + `4_PHASE_…` + plan + designs + requirements + context + `state.json` |
| 5 | `AGENTS.md` + `5_REVIEW_…` + all docs + `state.json` |

Each composite splits in two:

- **Fixed** — the instruction files. Always measurable from the set alone.
- **Variable** — the generated artifacts. Only measurable against a real output
  directory (`--docs`).

Three reporting rules keep this honest:

1. **The composite is counted as one payload, never as a sum of A1 figures.**
   Token counts are not additive — message envelope overhead and boundary
   tokenization both differ. `TokenCounter.count_composite` joins the parts and
   counts once.
2. **A missing artifact is `unmeasured`, never estimated.** A guessed number here
   is worse than no number.
3. **A partial measurement renders as `N+` with the missing artifacts listed**,
   so a floor can never be misread as a total.

The **legacy source is excluded** from these totals. It dwarfs the instruction
overhead and varies per project; folding it in would make the instruction-side
number meaningless.

### 5.B Referential Integrity — all built

Highest ROI in the system: deterministic, no API cost, and every hit is an
unambiguous defect. A dangling reference is a rule that silently never fires.

| ID | Check | Status | Failure looks like |
|---|---|---|---|
| **B1** | Section anchors resolve | built | `PROJECT_CONTEXT.md §7` cited where the template defines no §7 |
| **B2** | File references resolve | built | A reference to an instruction file after a rename |
| **B3** | `state.json` field paths consistent | built | `progress.lastChangeLogId` vs `progress.lastProcessedChangeLogId` |
| **B4** | ID format consistency | built | `C-1` against the established `C1` convention |
| **B5** | Orphan artifact sections | built | A `PROJECT_CONTEXT` section nothing ever cites |

Two implementation notes that matter:

**Fenced blocks are parsed for headings.** The harness *declares* the shape of its
generated artifacts inside ```markdown fences — `PROJECT_CONTEXT.md`'s ten
sections, `PLAN_<App>.md`'s five. Those fences are the declaration site for
every section other files then reference as `§N`, so a checker that skipped
fenced content would report all of them as dangling.

**B1 is deliberately conservative.** An explicit reference (`PROJECT_CONTEXT.md
§7`) that does not resolve is a blocker. A bare `§N` with no file hint is
reported only when it resolves against *no* known artifact — otherwise the
ambiguity belongs to the checker, and a false positive here would train people
to ignore the whole group.

**B3 derives its schema from the set itself** rather than from a hand-maintained
file, by parsing the `state.json` template block plus the inline element
snippets in the field notes. The check therefore verifies the set against its
own declaration, with no second source of truth to keep in sync.

**B5 requires section addressing to be an established convention** for an
artifact — at least three distinct sections cited — before reporting orphans in
it. Requirements and design documents are read whole, not by section; without
that scope the check produced 15 findings on the harness, all noise. It remains the
weakest check in the group and a prune candidate.

### 5.C Pipeline Coherence

| ID | Check | Status | Failure looks like |
|---|---|---|---|
| **C1** | Stage handoff closure | built | Stage 2 lists an input no stage declares as an output |
| **C2** | Ownership matrix drift | stub | Stage 4 claims LLD write access the README table denies |
| **C3** | Artifact lifecycle | built | Two stages both declaring the same artifact as output |
| **C4** | DoD ↔ body coverage | stub | A DoD checkbox with no instruction behind it |
| **C5** | Rerun path present | built | A stage with no Additional Instructions block |

**C5's rerun half is conditional on the schema.** Stages 4 and 5 have no entry in
`state.json.stages` — they are loop stages, not one-shot document stages — so
requiring a `rerunCount` from them would be a false positive. The check reads
which stages the schema actually tracks and only holds those to it.

**C1 recognises unknown artifacts.** Canonical mapping falls back to a
SCREAMING_SNAKE-shaped key for artifacts it does not know about; without that,
the check could only see handoff breaks among artifact types already in its
table — precisely the case where a break is least likely.

### 5.D Consistency & Drift

| ID | Check | Status | Failure looks like |
|---|---|---|---|
| **D1** | Controlled vocabulary | built | `in-progress` vs `in progress`; `OPEN_QUESTION:` vs `OPEN QUESTION:` |
| **D2** | Near-duplicate rules, diverged | stub | One copy of a restated invariant grows a carve-out |
| **D3** | Modality density | built | Imperative density far above the set median |
| **D4** | Format conventions | built | Mermaid diagram in an untagged fence |

Vocabularies live in `evalkit/vocab/` as plain text, one canonical term per
line. A term is flagged when a literal differs but normalizes (case,
hyphen/underscore/space) to a canonical entry.

**D2 fires only on divergence, never on duplication.** Restatement across
`AGENTS.md` and the stage files is deliberate in these sets, so a naive
duplicate detector is pure noise. The check will shingle-match restated rules,
then report only pairs the judge finds semantically *different* — because at
that point one of the two copies is wrong and nobody knows which.

**D3 is a smell, not a defect** — MINOR, and a prune candidate.

### 5.E Conflict Detection

| ID | Check | Status | Failure looks like |
|---|---|---|---|
| **E1** | Direct contradiction | stub | One file forbids what another requires, same actor and subject |
| **E2** | Authority ambiguity | stub | Two stages claiming write access with no precedence rule |
| **E3** | Unfalsifiable instruction | stub, experimental | "Mechanical" criteria no machine could evaluate |
| **E4** | Obligation vocabulary closure | built | An obligation key naming a stage that does not exist |

**Clustering is what will make E1/E2 affordable.** Naive pairwise comparison over
a few hundred rules is tens of thousands of judge calls. Instead: bucket by
`subject`, compare only pairs whose `actor` sets intersect, and skip pairs with
identical modality *and* predicate (D2's job). For the harness that lands in the low
hundreds — cheap enough per commit, and cheap enough to batch (§7.3).

**E4 checks three directions**, which is what makes it useful without a judge: a
schema obligation key with no stage to execute it; a key used in prose but never
persisted to `state.json`; and a stage that *no* obligation key can bind — a
silent hole in a design where obligations are the single place constraint rules
live.

### 5.F Hygiene

| ID | Check | Status | Failure looks like |
|---|---|---|---|
| **F1** | Actor referent ambiguity | stub | "you" meaning developer in one file, agent in another |
| **F2** | Unresolved placeholders | built | `TODO` / `TBD` / `FIXME` left in prose |
| **F3** | Worked-example validity | built | A README example command naming a missing file |

F3 complements B2 by scanning *inside* fences and blockquotes, which B2 skips.
The worked examples are what users copy verbatim, so a stale path there fails on
first contact.

---

## 6. Tier 2 — Behavioural Eval *(designed, not built)*

Tier 1 cannot tell you whether an instruction set works. Tier 2 runs it and
grades the result.

### 6.1 Fixture

- **Legacy input:** [sample_legacy_app/](../sample_legacy_app/) — already in the
  repo, already the app these sets were designed against.
- **Intake:** a checked-in `eval/fixtures/INTAKE.md` with all six load-bearing
  questions answered so Stage 0 has no reason to hard-stop, plus a variant with
  deliberate blanks to test the hard-stop behaviour itself.
- **Reference outputs:** [instruction_output/](../instruction_output/) holds three
  requirements documents from a real run. These are a **reference, not a gold
  standard** — produced by an earlier set, never human-verified. Use them for
  diffing and drift detection, not as an answer key.

### 6.2 What Gets Run

| Stages | Cost | Automation |
|---|---|---|
| 0–3 (document-producing) | Moderate | Fully automated. No code execution, no git, deterministic file outputs. |
| 4–5 (code-producing) | High | Opt-in via `--with-build`. Needs a scratch git repo, a toolchain, and produces PRs. |

The 0–3 path is the default: it exercises most of the instruction surface at a
fraction of the cost, and it is where instruction-set changes usually land.

### 6.3 Grading

Half the grading is deterministic. Build that half first — it does not drift
with judge behaviour.

**Deterministic metrics**

| Metric | Definition |
|---|---|
| **Citation validity** | Of every `path:line` citation in the output, the fraction whose path exists in the fixture *and* whose line is in range. Directly measures fabrication. |
| **Citation density** | Requirements carrying at least one evidence citation ÷ total requirements. |
| **Obligation coverage** | For each Stage 0 constraint, whether its per-stage obligation was addressed in that stage's output. |
| **Structural conformance** | Output documents contain the sections the instructions specify. |
| **Marker discipline** | `ASSUMPTION:` / `OPEN QUESTION:` present and correctly formatted where required. |
| **State integrity** | `state.json` validates; `changeLog[]` and `reviews[]` are append-only across runs. |
| **Boundary respect** | The legacy source is byte-identical after the run. A violation is an automatic **blocker**. |

Citation validity is the strongest single signal in the system: cheap,
objective, and it catches the failure mode that most damages downstream stages.

**Judged metrics** — scored 1–5 against a per-stage rubric in `eval/rubrics/`,
with the judge required to quote supporting text for each score: completeness,
altitude discipline, non-invention, question quality, design traceability, phase
slicing.

### 6.4 Cross-Version Regression

Running two revisions of the harness against one fixture answers "did this change
improve it" with evidence rather than assertion. One caveat belongs in the report,
not buried: when a revision adds a stage or artifact the other lacks, metrics
depending on it report `n/a`, never `0` — scoring an absent feature as zero
fabricates a gap.

### 6.5 Variance

Agent runs are non-deterministic; a single run of each set proves nothing.

- Minimum **n = 3** per configuration; report median and range, never a bare number.
- Call a regression only when the ranges do not overlap.
- Fix everything fixable: same model, effort, fixture, prompt text.
- Log model id, effort, and set commit SHA into every result file, so a score is
  never orphaned from the conditions that produced it.

---

## 7. Shared Infrastructure

### 7.1 Token Counting

Two backends behind one `TokenCounter` interface (`evalkit/tokens.py`).

**Active: `tiktoken` (interim).** Fast, offline, no credentials. It is an
**approximation** — tiktoken is OpenAI's tokenizer, not Anthropic's, and it
systematically **undercounts** Claude tokens, typically 15–20% on prose and more
on the heavy Markdown tables these files are full of. Every metric it produces
carries `approximate: true`, and the report prints the caveat at the top, so an
approximate figure can never be mistaken for a real Claude count. Use it for
*relative* signal — growth over time, which stage load-out is heaviest — not for
absolute budget decisions.

**Placeholder: `AnthropicCounter`.** The real count, via
`client.messages.count_tokens`. The class is wired and documented; activating it
is filling in a three-line body, adding `anthropic` to the base dependencies,
and passing `--token-backend anthropic`. No other code changes, because every
caller goes through the interface.

Two things to settle when enabling it:

1. **Framing.** `count_tokens` counts a *request*, not a file. Everything here is
   framed as a single user message; that convention must stay constant or
   cross-commit deltas stop being comparable. If the real stage harness splits
   system/user, re-baseline once and note it.
2. **Volume.** A cold full run is ~15 calls (9 files + 6 composites) — cheap. The
   cache keeps repeat runs at zero.

**Caching** is keyed on `sha256(content) + backend + model`. Content rather than
mtime, so a git checkout does not invalidate everything; backend and model in
the key because a cache written by tiktoken must never be served to the
Anthropic backend.

### 7.2 The Judge Harness *(not built)*

One code path will serve rule extraction, D2, C2/C4, E1–E3, and Tier 2 rubric
scoring. Every judge call uses **structured outputs** so results are
schema-valid rather than prose that needs regex.

```python
class ConflictVerdict(BaseModel):
    conflict: bool
    kind: Literal["contradiction", "authority", "divergent_restatement", "none"]
    severity: Literal["blocker", "major", "minor", "none"]
    explanation: str
    quote_a: str          # verbatim from rule A
    quote_b: str          # verbatim from rule B

resp = client.messages.parse(
    model="claude-opus-5",
    max_tokens=2000,
    output_format=ConflictVerdict,
    system=[{"type": "text", "text": JUDGE_SYSTEM_PROMPT,
             "cache_control": {"type": "ephemeral"}}],
    messages=[{"role": "user", "content": render_pair(rule_a, rule_b)}],
)
```

Three properties the design depends on:

- **Verbatim quotes are required by the schema**, then verified deterministically
  against the source file. A judge that must quote the text it is judging
  fabricates less, and a quote that does not appear verbatim invalidates the
  finding outright.
- **Prompt caching on the system prompt.** Identical across hundreds of calls; a
  `cache_control` breakpoint makes reads ~0.1× input cost. The cacheable minimum
  on `claude-opus-5` is 512 tokens, which the judge prompt clears.
- **`effort` is a tuning knob.** Pairwise conflict judgement at `medium`; Tier 2
  rubric scoring at `high`, where judgement is harder and call volume far lower.

### 7.3 Batching

Tier 1's conflict pass is a few hundred independent calls with no ordering
dependency — the shape the Batches API is for, at 50% cost. Results key by
`custom_id` (they return in arbitrary order, never key by position). Interactive
runs use direct calls for latency.

### 7.4 Cost Control

- Token counts cached by content hash — unchanged files cost nothing.
- Rule extraction will cache the same way; conflict verdicts by `(rule_a.id, rule_b.id)`.
- **`--det-only` runs the entire deterministic surface with zero API calls.** This
  is the CI default and covers 18 of the 25 checks.

---

## 8. Outputs

Written to `eval/results/<timestamp>-<set>/`.

**`findings.json`** — machine-readable: `meta`, `summary`, `findings`,
`suppressed`, `metrics`, `skipped`. One finding record:

```json
{
  "id": "a3f9c21b04",
  "check": "B1",
  "severity": "blocker",
  "file": "ModernizationHarness/1_REQUIREMENTS_EXTRACTION_INSTRUCTIONS.md",
  "line": 62,
  "subject": "PROJECT_CONTEXT.md#8",
  "summary": "Reference to PROJECT_CONTEXT.md §8 does not resolve",
  "detail": "PROJECT_CONTEXT.md declares sections 1-7, 9-10.",
  "evidence": ["cite the constraint ID in §8 Constraint Traceability"]
}
```

**`report.md`** — human-readable: severity summary, the group A budget tables,
findings grouped by check with clickable `path:line` citations, skipped checks
with reasons, and suppressed findings.

**`baseline.json`** (checked in) — finding IDs to suppress, each with a required
reason. Suppression is per-finding, never per-check, so a suppressed instance
cannot hide a new one. Current entries cover three findings on the harness that are
deliberate design choices rather than defects.

---

## 9. Repository Layout

```
eval/
  EVAL_DESIGN.md          # this document
  pyproject.toml          # uv project; tiktoken only (anthropic under [llm] extra)
  baseline.json           # per-finding suppressions, each with a reason
  run.py                  # CLI entry point
  evalkit/
    model.py              # Finding, Metric, Severity, Document, Heading, InstructionSet
    parser.py             # Markdown parsing; fenced-block-aware; reference extraction
    registry.py           # @check decorator, Context, selection
    runner.py             # Tier 1 orchestration
    report.py             # findings.json + report.md + baseline
    tokens.py             # TokenCounter: tiktoken (active) | anthropic (placeholder)
    checks/
      size.py             # A1-A4      references.py   # B1-B5
      coherence.py        # C1-C5      consistency.py  # D1-D4
      conflicts.py        # E1-E4      hygiene.py      # F1-F3
    vocab/
      status_values.txt   # controlled status/enum terms (D1)
      markers.txt         # ASSUMPTION: / OPEN QUESTION: (D1)
  tests/
    fault_injection.py    # proves every deterministic check fires (§11.1)
  results/                # gitignored
  .cache/                 # gitignored (token cache)
```

Not yet present, and blocked on Tier 2: `rubrics/`, `fixtures/`, `behavioral/`.

---

## 10. CLI

Setup once: `cd eval && uv sync`.

```bash
# CI default — every deterministic check, zero API calls, ~2s
uv run run.py --set ../ModernizationHarness --det-only

# Token budgets, with the variable half measured against real outputs
uv run run.py --set ../ModernizationHarness --checks A --docs ../instruction_output

# A single check or group
uv run run.py --set ../ModernizationHarness --checks B1
uv run run.py --set ../ModernizationHarness --checks B C

# What is registered, and what is a stub
uv run run.py --list-checks

# Prove the checks still fire
uv run tests/fault_injection.py
```

Notable flags: `--token-backend {tiktoken,anthropic}`, `--budget-warn N` (off by
default — group A reports, it does not gate), `--baseline PATH`,
`--include-experimental`, `--with-llm` (stubs report as unimplemented),
`--no-cache`, `--out DIR`.

Exit codes: `0` clean or findings ≤ major, `1` blocker present, `2` harness
error or unimplemented tier.

---

## 11. Validation

### 11.1 Fault injection

`tests/fault_injection.py` copies a real instruction set, injects one specific
defect per check, and asserts that check reports it. A check that silently never
fires is worse than no check — it reads as a clean bill of health.

The harness distinguishes two failure modes so they are never confused:
**MUTATION FAILED** (the injected edit did not apply, so the case proves nothing
and must be repaired) and **CHECK SILENT** (the edit applied but the check found
nothing — a real defect in the check).

All 14 deterministic cases pass. It also runs a control pass over the unmodified
set, so a check that fires on everything is caught too.

**It has already earned its keep.** The first run found two checks that could
never have fired on real input:

- **D3 scored every file at 0.00** — its modality regex was uppercase-only while
  these sets write imperatives as lowercase prose (`**never** modify`, `you must`).
- **C1 could not see unknown artifacts** — canonical mapping returned `None` for
  any artifact type not already in its table, which is exactly the case where a
  handoff break is most likely.

Neither would have surfaced from a clean run on the harness; both looked like passing
checks.

### 11.2 Running against the harness

At commit `5e3a2c0`:

| Set | Checks runnable | Blocker | Major | Minor |
|---|---:|---:|---:|---:|
| ModernizationHarness | **18 / 18** | 0 | 0 | 3 |

**"Checks runnable" is itself a signal.** A set with no `state.json` schema, no
numbered stage files and no artifact template fences skips B1/B3/B5/C1/C3/C5/E4 —
there is nothing for those checks to verify. Each skip states its reason in the
report rather than silently scoring zero, so an absent feature is never mistaken
for a clean one.

The harness's three minors are all suppressed in `baseline.json` with reasons: a
`PROJECT_CONTEXT` section read as prose rather than cited, `AGENTS.md`'s
by-design imperative density, and the README's ASCII pipeline diagram in an
untagged fence.

### 11.3 False positives fixed, not baselined

Five checker bugs were found by triaging output rather than accepting it. All
were fixed in the checks; none were suppressed, because a false positive
baselined is a check quietly disabled:

| Bug | Symptom |
|---|---|
| Glob read as filename | `*_TEMPLATE.md` reported as a missing file; the fix needed a `(?<![*\w])` lookbehind, because rejecting only `*` let the regex re-anchor onto `TEMPLATE.md` |
| B5 over-scope | Every unreferenced section of documents that are read whole, not by section |
| `§0` unregistered | A set declaring `## §0 — Project-Wide Constraints` as a live heading, not inside a template fence, made every self-reference read as dangling |
| Prose hint too loose | "…stated in business terms (see §0)" resolved to `BUSINESS_REQUIREMENTS.md` and raised a blocker; hints are now bounded to 30 characters before the `§` |
| `TODO` in code span | "mark the AD wiring as \`TODO (AD)\`" is an instruction to *emit* a marker — reporting it inverts the check's meaning |

---

## 12. Implementation Phases

| Phase | Contents | Status |
|---|---|---|
| **1** | Parser, findings/report plumbing, group B, C1/C3/C5, E4, F2/F3 | **done** |
| **2** | Group A token counting (A1–A4), tiktoken backend | **done** |
| **2b** | D1/D3/D4, fault-injection harness, baseline mechanism | **done** |
| **3** | Rule extraction, judge harness, caching, batching | next |
| **4** | E1/E2, D2, C2/C4, F1 — conflict detection, the original motivation | blocked on 3 |
| **5** | Tier 2 deterministic metrics (§6.3) | blocked on fixture intake |
| **6** | Tier 2 rubric scoring, cross-version regression | blocked on 3, 5 |
| **7** | Anthropic token backend swap; prune E3/D3 if noisy | any time |

---

## 13. Open Decisions

1. **When to swap the token backend.** tiktoken was chosen for simplicity and is
   explicitly interim. Every number it produces is labelled approximate. The
   swap is one flag plus a three-line method body; it needs API credentials,
   which have not been confirmed in this environment.
2. **Fixture intake answers.** Someone must author `eval/fixtures/INTAKE.md`
   against `sample_legacy_app/`. This is a human judgement the eval cannot make,
   and Tier 2 is blocked on it.
3. **Reference outputs.** Should `instruction_output/` be promoted to a verified
   answer key? That needs a human pass. Until then, diff-only.
4. **Tier 2 budget ceiling.** Three runs × four stages, per revision compared, is a real
   spend. A per-run cap needs setting before Phase 6.
5. **Checks to prune.** B5 and D3 survive but earn little — B5 needed two rounds
   of scope-tightening to stop being noise, and D3 is a smell by construction.
   E3 remains experimental and unimplemented. Decide after Phase 4.
6. **~~Whether `state.schema.json` becomes authoritative.~~** *Resolved:* B3
   derives the schema from the set's own `state.json` template block, so the
   check verifies the set against its own declaration with no second source of
   truth. A hand-written schema is still worth having as a harness deliverable —
   the shape is currently described in prose across several files — but the eval
   does not need one.
