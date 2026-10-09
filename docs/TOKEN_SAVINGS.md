# Design Proposal — Token Savings in the Context File, state.json and AGENTS.md

*Status: **proposed, not applied.** Nothing in the harness has changed. Options 1–3 and 5 are
design changes and need a yes before any edit (see [AGENTS.md](../AGENTS.md) §Design changes).
Written 2026-10-09 after a three-round review against the files; line references are as of
that date and may have moved.*

---

## 1. The question

Can we redesign the agent template (`AGENTS_TEMPLATE.md`), the project context file
(`PROJECT_CONTEXT.md`) and `state.json` so that every stage run uses fewer tokens, without
lowering the quality of what the agents produce?

**Short answer:** yes, modestly. The main waste is information that is **stored twice and read
twice**, plus one large section of the context file that no later stage uses. The context file
itself should stay. §2 explains why.

---

## 2. Background: who reads the context file, and why it stays

**Who reads it.**

- **Stage 0** writes it. On a rerun, it loads the old file and compares last time's answers
  (§5) with the new `INTAKE.md`.
- **Stages 1–5** all list it as an input:

  | Stage | How it uses the file |
  |---|---|
  | 1 Requirements | Reads it first, as the top authority ([1_…:12](../ModernizationHarness/1_REQUIREMENTS_EXTRACTION_INSTRUCTIONS.md#L12)). |
  | 2 Design | Lists it first. The only stage told to read it **in full** ([2_…:152](../ModernizationHarness/2_DESIGN_INSTRUCTIONS.md#L152)). |
  | 3 Plan | Lists it second, after the designs. Focuses on §4. |
  | 4 Implement | Lists it as reference #6. Its §4 constraints still win any conflict. |
  | 5 Review | Lists it #4, and audits the built code against it. |

- **All of Stages 1–5** also read the `context` part of `state.json`, at least to find their
  files (`context.locations`). Stages 1, 2, 4 and 5 also read the constraints from there.
- **Other files that mention it:** `AGENTS_TEMPLATE.md` (stage routing, Invariant 2, the
  authority ladder), `0_INTAKE_TEMPLATE.md:540`, `examples/INTAKE_EXAMPLE.md:19`, and the
  guides (README, DEVELOPER_GUIDE, USE_CASES).

**Why it stays.**

1. **It keeps the stage files generic.** Each project's rules live in it as constraints, and
   each constraint carries its own per-stage obligations. A new project needs no edit to any
   stage file (DD-1, R1).
2. **It settles the intake once.** Stage 0 fills in defaults and works out the constraints.
   Without the file, each stage would re-interpret the raw intake and might reach a
   different answer.
3. **Its constraints outrank everything.** A constraint in §4 wins every conflict. Note that
   the *rest* of the file ranks **last**, below the plan, designs and requirements
   (`AGENTS_TEMPLATE.md:176-180`, R9.3).
4. **Nothing else can do its job.** The requirements describe the old app, not the
   developer's rules. `state.json` is machine bookkeeping and is meant to hold no prose (DD-2).

---

## 3. What wastes tokens today

1. **The constraints are stored twice.** Stage 0 writes each constraint and all its
   obligations into **both** §4 and `state.json` `context.constraints`
   ([0_…:276-278](../ModernizationHarness/0_PROJECT_CONTEXT_INSTRUCTIONS.md#L276-L278)).
   Stages 1, 2, 4 and 5 read both copies. Nothing checks that the two copies still match, so
   they can drift apart silently.
2. **§5 is large and no later stage uses it.** It lists all 80 intake answer parts, about
   2–3k tokens. The instructions call it "a record, not an input", yet every stage that opens
   the context file pays for it. Stage 4 opens it once per phase.
3. **The state tool's help text is printed on every stage run.** `AGENTS_TEMPLATE.md:40`
   says to run the tool with no command "before your first write". That prints about 2.5 KB,
   roughly 650 tokens.
4. **The Stage 4 file is large and reloaded every phase.** It is about 12k tokens. Its git
   section alone is 10.8 KB and repeats some rules.
5. **The generated documents are the biggest cost overall.** Stage 4 reads the full designs,
   the three requirements files and the plan on every phase. None of options 1–4 touch this;
   option 5 does.

---

## 4. The options

### Option 1 — Move the §5 intake list to its own file *(design change)*

- **What:** move the 80-row answer list into a new file that only Stage 0 reads, for example
  `INTAKE_RESOLVED.md`. Stage 0 compares old and new answers against it on a rerun.
- **Saves:** about 2–3k tokens on every later stage run.
- **Safeguards needed:**
  - **A new Stage 0 rule.** Every default or inferred answer that matters to a later stage
    must also be written in its normal section, as a constraint, or as an open question (§7).
    Today §5 is the only complete list, so without this rule a quiet default could vanish
    from view.
  - **A one-line §5 stub** pointing to the new file. The other stages cite §6–§10 by number,
    and Stage 0 says those numbers must not shift (0_…:519-521).
  - **R2.3** ("every answer the agent filled in must be reported back") now happens in the
    new file. Say so.
- **Places to update:**
  - Invariant 2 in `AGENTS_TEMPLATE.md:103`.
  - Stage 0 lines ~35, ~93, 377, 382, 717-722, and its Definition of Done at 765-766.
  - `0_INTAKE_TEMPLATE.md:540`.
  - `examples/INTAKE_EXAMPLE.md:19`.
  - `DEVELOPER_GUIDE.md:189-196` and `USE_CASES.md:475-480`.
  - `eval/evalkit/checks/consistency.py:342, 347` (messages only).
  - DESIGN.md (components list in §2) and REQUIREMENTS.md.
- **Risk:** low, once the new Stage 0 rule exists.

### Option 2 — Store the obligations in §4 only *(design change)*

- **What:** remove `context.constraints` from `state.json` completely. The full obligations
  stay in `PROJECT_CONTEXT.md §4`, which is where DD-1 already says they live. Keeping just
  ids or titles in `state.json` was considered and rejected: no stage would read them, and
  they would be one more copy that could drift.
- **Saves:** 1–3k tokens per run in Stages 1, 2, 4 and 5. It also removes the unchecked
  double copy.
- **Places to update:**
  - **Stage 0:** the line "into §4 **and** into `state.json`" (276-278), and the schema
    block (~585-588).
  - **The input lines in Stages 1, 2, 4 and 5:** 1_:52, 2_:30, 4_:46-47, 5_:30.
  - **The eval check that matches obligation names to stages (E4):** a rewrite, not a small
    edit. Today it reads the names from the `state.json` schema (`conflicts.py:38-51`). It must
    instead read the `*Requirements:*`-style bullets in the §4 template. Its test "a key used
    in prose but never written to state.json" (:120) must be removed or redefined. Then update
    `eval/EVAL_DESIGN.md:288-299` and check `eval/baseline.json`.
  - **DESIGN.md §5:** the diagram.
  - **No change needed:** `state.py` and its tests still pass. Optionally, point
    `test_state_tool.py:82` at another nested path such as `context.repo`, because
    `context.constraints` will no longer exist in the schema.
- **Risk:** low. §4 already holds the full text.

### Option 3 — Print the state tool's help only when needed *(borderline — ask first)*

- **What:** change `AGENTS_TEMPLATE.md:40` from "run it with no command for the syntax before
  your first write" to "run it with no command when a command is refused as malformed". The
  short command list in the template stays.
- **Saves:** about 650 tokens per stage run.
- **Risk:** low. A malformed command is refused and writes nothing, so the worst case is one
  retry. One rare quiet case: a literal `\uXXXX` typed in a `k=v` value.
- **Design change?** It changes no decision, requirement, schema or stage input. It only
  changes when an agent reads the help. That makes it borderline; ask before applying.

### Option 4 — Tidy the Stage 4 instructions *(not a design change)*

- **What:** remove rules that repeat inside "Git Discipline" (~10.8 KB). Shorten the wording
  of the Definition of Done items, but **keep it as a full checklist**. In a long run, that
  end-of-run list is what catches missed steps, so do not turn it into one-line pointers back
  into the body.
- **Saves:** moderate. The checklist itself is only ~1.1k tokens; most of the saving is in
  the git section.
- **Limit:** the eval check for checklist coverage (C4) is not built yet
  (`coherence.py:287-295`). So the eval can confirm references and wording still agree, but
  not that behavior is unchanged. Review by hand.

### Option 5 — Stage 4 reads only the sections the phase needs *(design change, later)*

- **What:** the plan entry for each phase names the design and requirements sections it
  needs. Stage 4 reads only those.
- **Saves:** the most of any option, because the generated documents are the biggest cost.
- **Risk:** high. A phase could miss a rule stated in a section it was not told to read. Do
  this only after a measured before/after run.

### Rejected options (and why)

| Idea | Why not |
|---|---|
| Tell each stage to read only certain sections | Saves almost nothing. The agent's file-reading tool loads the whole file anyway. |
| Give each stage only its own obligation | Lowers quality. Review falls back to the *Implement* obligation when a constraint has no *Review* one (5_:165). The plan builds the *Implement* obligations into its exit checks (4_:112). Obligations also refer to each other. |
| Keep constraints only in `state.json`, with a tool command to slice them | Breaks DD-1 (constraints live in §4) and DD-2 (no prose in `state.json`). Prose in JSON also costs more tokens, because the tool prints non-ASCII characters as escapes such as `\u2014`. |
| Move all structured context into `state.json` and print a per-stage summary | Breaks DD-1, DD-2, R1.2, R7.1, the authority ladder, the eval reference checks, and every stage's input list. |
| A heavy trim of `AGENTS_TEMPLATE.md` | Saves at most ~800 tokens, and it is loaded once and cached, not paid per turn. The mid-flight-change section, the "record what the developer tells you" table and the two kinds of tool refusal are needed in ordinary chat, where no stage file is loaded. |

---

## 5. Suggested order

1. **Option 4** — can be done now. Run the two required eval checks afterwards.
2. **Option 3** — after a one-line yes.
3. **Options 1 and 2 together** — after approval, with the safeguards above. Per the repo
   rules: DESIGN.md and REQUIREMENTS.md first, then the harness files, then the guides.
4. **Option 5** — only after a measured before/after run (§6).

---

## 6. How to check that quality holds

- **Token counts:** the size check (A3) in `eval/evalkit/checks/size.py` measures them. Run
  `uv run run.py --set ../ModernizationHarness --checks A` from `eval/`. Add `--docs <dir>` to
  include the generated documents. Do **not** compare against `eval/results/`. Those figures
  measure an older instruction set, and that folder is a historical record that must not be
  rewritten.
- **Quality:** A3 counts tokens, not quality. For options 1–3, run Stage 0 twice on the
  small `sample_legacy_app/` (before and after the change), then compare the Stage 1 and
  Stage 2 outputs. A full Stage 0–4 build is not needed. `D:\career\projects\MT_POC_JAVA` has
  no harness outputs yet, so it would need a full run.
- **Option 1, before applying:** after one Stage 0 run, list the §5 rows marked as defaults
  or assumptions. Check that each also appears in another section. Any that don't are
  exactly what the move would lose.
