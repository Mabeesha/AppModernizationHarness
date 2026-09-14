# Agent Instructions: Review an Instruction Set (Agentic Eval)

You are reviewing a **set of agent instruction files** as documents. You are not running
them, not fixing them, and not judging the methodology they describe. You are answering one
question with evidence:

> **If an agent tried to follow these instructions literally, where would it break, stall,
> or have to guess?**

You produce one artifact: a human-readable review report.

---

## 1. Relationship to the deterministic eval

This runs **parallel to**, and never replaces, the Tier 1 static eval
(`eval/run.py`, see [EVAL_DESIGN.md](EVAL_DESIGN.md)). They are complementary:

| | Tier 1 (`run.py`) | This review |
|---|---|---|
| Method | Regex / parser rules | Reading with comprehension |
| Catches | Anchors, paths, vocabulary, format | Meaning: contradiction, divergence, unstated dependency |
| Misses | Anything requiring semantics | Anything requiring exhaustive mechanical sweeps |
| Cost | ~2s, free | One agent session |
| Determinism | Total | Partial — see §8 |

Deliberate overlap on references (§4, group RF) is a feature: Tier 1 sweeps exhaustively, you
catch the references it cannot pattern-match — a section cited by name, a step label, a JSON
path buried in prose.

**Run Tier 1 first when it is available.** Read its `report.md` before you start, and when
your reading contradicts one of its findings, say so explicitly in §6.4 rather than quietly
dropping it. A disagreement between the two is itself a finding — usually about a check.

---

## 2. Inputs

1. **The instruction set** — a directory of Markdown files. Named on invocation; default
   `ModernizationHarness/`. **Read every file in it, completely, before writing anything.**
   Not skimmed, not sampled, not grepped-into. You cannot detect a contradiction between two
   files you have only seen fragments of.
2. **The Tier 1 report** (optional) — the most recent `eval/results/*/report.md`.
3. **The baseline** (optional) — `eval/review-baseline.md`. Findings previously accepted as
   deliberate. Still detect them; report them under **Suppressed**, not under Findings.
4. **Generated-artifact samples** (optional) — a directory of real pipeline output
   (`instruction_output/`, `modernized_app/out/`). Useful for resolving whether a referenced
   artifact section actually exists in practice. **Never** treat their content as a rule
   source: they are outputs, not instructions.

**Not inputs.** The legacy application, the modernized application, the eval's own Python, and
git history. Reviewing the set means reviewing the set.

---

## 3. Hard rules

1. **Never edit the instruction set.** Not a typo, not a broken link, not "while I was in
   there". You report; a human decides. This is the whole reason the review is trustworthy.
2. **Every finding quotes its evidence** — verbatim, with `file:line`. A conflict quotes
   **both** sides. A finding you cannot quote is a finding you cannot defend: drop it.
3. **Report defects, not preferences.** Prose quality, tone, ordering, length, and "I would
   have phrased this differently" are out of scope. So is token budget — Tier 1 group A owns
   it, and these sets deliberately tolerate redundancy (see the RD preamble in §4).
4. **A finding must name a victim.** Say which agent, at which stage, doing which task, gets
   the wrong answer. If you cannot write that sentence concretely, you have found a stylistic
   difference, not a defect.
5. **Never invent a rule to measure against.** You check the set against *itself* — its own
   declarations, its own cross-references, its own precedence order. You do not check it
   against how you think a modernization pipeline ought to work.
6. **Uncertainty is reported, never rounded off.** A file you could not fully read, an
   artifact you could not resolve, a check you ran out of budget for — all of it goes in §6.5.
   An unstated gap reads as a clean bill of health, which is worse than no review.

---

## 4. Method

Five passes, in order. Do not start writing the report during passes 1–3; candidate findings
go in a scratch list, and most of them will not survive pass 4.

### Pass 0 — Build the map

Before judging anything, extract the set's own declarations into a working inventory. Almost
every real finding is a mismatch between two entries in this map, so build it carefully.

- **Files** — every file in the set, and for each: its role (stage instruction, template,
  reference doc, README) and the stage number it belongs to, if any.
- **Headings** — every heading in every file, **including headings inside fenced blocks.**
  This is load-bearing: a set that generates artifacts declares their shape inside
  ` ```markdown ` fences, and those fences are the *definition site* for every `§N` other
  files cite. Treat a heading inside an output-template fence as a real, citable section.
- **Generated artifacts** — every artifact the set says some stage produces, with the
  producing stage and the sections its template declares.
- **Machine state** — if the set declares a state schema (e.g. a `state.json` template),
  record every field path it defines, including those introduced in inline snippets in field
  notes rather than in the main template block.
- **Identifier conventions** — the ID shapes the set uses (`C1`, `P-2`, `FR-3`, `DD-1`,
  `Step 0c`, obligation keys such as `requirements | design | plan | implement | review`) and
  where each is defined.
- **Stage I/O** — for each stage: declared inputs, declared outputs, and its Definition of
  Done, if it has one.
- **Precedence** — any stated authority or conflict-resolution order. Quote it exactly; it is
  the single most useful thing you will hold in pass 2.

Note gaps as you go. A set with no state schema simply has no RF3 findings — that is a skipped
check, not a passing one (§6.5).

### Pass 1 — Reference integrity (RF)

Sweep for the RF checks in §5. Mechanical, but do it with the map in hand rather than from
memory.

### Pass 2 — Conflicts (CF)

For each **subject** in your map (an artifact, a state path, a decision, a boundary), gather
every instruction that governs it, across all files, and read them together. Conflicts do not
announce themselves inside one file; they live between two files that were each written
correctly on their own day.

Compare only rules that share a subject **and** an actor. Two stages with different jobs saying
different things about different artifacts is not a conflict — it is a pipeline.

### Pass 3 — Redundancy & divergence (RD)

Cluster restatements of the same rule, then compare the copies word by word for a **material**
difference. Read the RD preamble in §5 before you report anything here — the bar is high on
purpose.

### Pass 4 — Falsify your own findings

**Do this for every candidate, without exception. Expect to drop a third of them.** For each:

1. **Re-read the full section around both quotes**, not the quoted lines. Most false positives
   die here, killed by a carve-out or a scoping sentence one paragraph away.
2. **Argue the other side.** Write the strongest reading under which the instruction set is
   correct as written. If that reading is plausible, the finding is dead — or at most a MINOR
   about the ambiguity itself, and you must say which reading you believe is intended.
3. **Write the failure scenario.** One concrete sentence: *"An agent at Stage 3, told to
   produce X, reads Y and Z and cannot proceed / produces the wrong artifact / silently skips
   the rule."* No scenario, no finding.
4. **Check the precedence rule.** If the set states an authority order that already resolves
   your conflict, it is resolved. Not a finding.
5. **Check the baseline.** If it is listed there, move it to Suppressed with the recorded
   reason.

### Pass 5 — Write the report

Per the template in §6. Findings ordered by severity, then by check id.

---

## 5. The checks

Three groups. Each check states what it catches and — as important — what does **not** count.
Every check has a **default severity**; deviate only with a stated reason in the finding.

### RF — References & dependencies

*A dangling reference is a rule that silently never fires. This group has the highest
signal-to-noise in the review: every genuine hit is an unambiguous defect.*

**RF1 — File references resolve.** Every file named in prose, a table, a link, or a fence
exists — in the set, or as a declared generated artifact, or in the supplied samples.
*Not a finding:* a placeholder-shaped name (`PLAN_<App>.md`, `HIGH_LEVEL_DESIGN_<AppName>.md`),
a path inside the target application that the set does not own, or an artifact a later stage
generates that is simply absent from a set-only review. Resolve names against your Pass 0
artifact list *before* calling one missing.
**Severity: blocker** — an instruction pointing at nothing cannot be followed.

**RF2 — Section references resolve.** Every `§N`, "see the X section", or "per the table in Y"
resolves to a heading that exists in the named file — including fenced template headings.
*Not a finding:* a bare `§N` with no file named that resolves against *some* plausible
artifact. When you cannot tell which document is meant, the ambiguity is yours, not the
set's — report it as MINOR if at all.
**Severity: blocker** when the file is named and the section does not exist; **major** when the
section exists but has been renumbered relative to the citation.

**RF3 — State field paths exist.** Every machine-state path mentioned anywhere
(`progress.lastProcessedChangeLogId`, `stages.design.rerunCount`, `phases[].status`) appears in
the schema the set declares. Check both directions: a path used but never declared, and a
declared path that nobody writes and nobody reads.
*Not a finding:* a path declared inside a field note rather than the main template block —
those are declarations too, and your Pass 0 map should already hold them.
**Severity: blocker** for a used-but-undeclared path; **minor** for a declared-but-unused one.

**RF4 — Identifier and label references resolve.** Every reference to a stage number, a step
label (`Step 0c`), an ID scheme (`C1`, `P-2`, `FR-3`), a status value, or an obligation key
matches something the set actually defines, in the shape it defines it.
*Watch for:* a stage referenced by a number it no longer has after a renumber; a step label
cited from another file after the owning file restructured its steps; an obligation key
(`implement`) written in prose under a different name (`build`) than the schema declares; a
status value used in prose (`in-progress`) that the schema spells differently (`in progress`).
**Severity: blocker** for a label that does not exist; **major** for a spelling variant of one
that does.

**RF5 — Handoff closure.** Every declared stage input is some earlier stage's declared output,
the developer's supplied input, or the legacy source. Every declared output is consumed by
something, or is a terminal deliverable the set names as such.
*Not a finding:* an output whose only consumer is a human. Say so and move on.
**Severity: major** — the pipeline still runs, but a stage will improvise its missing input.

**RF6 — Worked examples are valid.** Commands, file trees, and worked examples inside fences
and blockquotes name real files, real flags, and real directories. Users copy these verbatim,
so a stale path here fails on first contact.
*Check especially:* README command lines after a directory rename, and example invocations
naming a set that has since been renamed.
**Severity: major**; **blocker** when the example is the documented entry point for the set.

### CF — Contradictions & authority

*Report a conflict only when a single agent, at a single moment, facing a single decision,
would find two instructions that cannot both be satisfied.*

**CF1 — Direct contradiction.** Same actor, same subject, incompatible modality: one file
requires what another forbids.
*Not a finding:* a general rule plus an explicit carve-out ("this does not apply when you are
executing the stage that owns the edit"). A carve-out is the resolution, not the conflict. Read
the whole rule before calling it.
**Severity: blocker.**

**CF2 — Conditional contradiction.** Two conditional rules whose guards overlap and whose
outcomes differ, with no rule for the overlap. Harder to see than CF1 and more common: each
rule is correct in the case its author was thinking about.
*Method:* for each pair, construct the concrete case where both guards are true. If you cannot
construct one, the guards do not overlap and there is no finding.
*Not a finding:* an overlap the set explicitly routes to the human ("report it and stop"). That
**is** the rule for the overlap.
**Severity: blocker** when the overlap is reachable in a normal run; **major** when it needs an
unusual sequence.

**CF3 — Authority ambiguity.** Two actors may write the same artifact, or make the same
decision, with no precedence between them and no stated ownership.
*Not a finding:* clear single ownership, or shared write access governed by a stated ownership
table or precedence order. Where an ownership matrix exists, check it against what the stage
files actually claim — drift between the table and the stage is the real defect here.
**Severity: major**; **blocker** when both actors can write in the same run.

**CF4 — Precedence violated.** The set states an authority order, and a specific instruction
somewhere contradicts it, telling an agent to prefer the lower-authority source.
This deserves a dedicated sweep: a stated precedence rule is the set's own yardstick, so a
violation is objectively a defect and needs no judgment call from you.
**Severity: blocker.**

**CF5 — Unfollowable instruction.** Not a contradiction, but the same effect: an instruction an
agent cannot act on. Three shapes:

- **Unavailable input** — requires information the pipeline does not have at that point (a
  stage told to honor a decision a later stage makes).
- **Unevaluable criterion** — a gate whose pass condition no reader could evaluate the same way
  twice ("ensure the design is appropriate"). Report only when it is a **gate** — a Definition
  of Done item, an acceptance condition, a hard rule. Aspirational prose in a mission statement
  is not a gate.
- **Uncovered obligation** — a Definition of Done item, checklist entry, or required output
  section with no instruction anywhere in the file explaining how to produce it.

**Severity: major**; **blocker** for an unavailable input, which stalls the run outright.

### RD — Redundancy & divergence

> **Read this before reporting anything in this group.** In multi-stage instruction sets,
> restatement is usually *deliberate* — an always-loaded file (`AGENTS.md`) restates invariants
> that also live in stage files, because the stage files are not in context during ad-hoc chat.
> **Duplication alone is never a finding here.** Only *divergence* is, plus a narrow class of
> genuinely dead text. If you find yourself listing "this appears in two places" as a defect,
> stop — you are about to tell a maintainer to delete a safety net.

**RD1 — Diverged restatement.** The same rule appears twice and the copies now say materially
different things: one grew a carve-out, tightened a threshold, added a condition, or changed an
ID. One of the two copies is wrong and nobody knows which — that is why this matters.
*Material means:* an agent following copy A and an agent following copy B would produce
different output or take different actions. Different wording, ordering, or level of detail is
not material.
*Not a finding:* a short pointer plus a fuller normative statement elsewhere, where the short
version names its authority ("see §Recording What the Developer Tells You"). That is correct
restatement — worth noting as such if you were tempted by it.
**Severity: blocker** when the copies actively conflict (that is also CF1 — report it once, as
RD1, and say so); **major** when one copy is merely stale.

**RD2 — Duplication within one file.** The same instruction appears twice in the *same* file.
The always-loaded rationale does not apply within a single file, so this is usually an editing
artifact — and the two copies will drift.
*Not a finding:* a deliberate summary section (a DoD checklist, a "hard rules" recap) that
restates the body by design. Those are navigational, and the file usually says so.
**Severity: minor**; **major** when the two copies already differ.

**RD3 — Superseded or orphaned instruction.** A rule about an artifact, stage, flag, or
convention that no longer exists — the residue of a rename or a removal. Found reliably by
walking your Pass 0 map backwards: for each *thing the set no longer has*, search for text that
still governs it.
**Severity: major** — harmless-looking, and it will send an agent chasing a ghost.

**RD4 — Restatement with no normative home.** A rule stated in several places where no copy is
marked as the authority, so a future editor has no way to know which one to update.
Report at most **one** finding per rule cluster, and only when the copies are already drifting
or the rule is load-bearing. This check is a prune candidate: if it produces more than a
handful of findings on a healthy set, it is miscalibrated — say so in §6.5 rather than flooding
the report.
**Severity: minor.**

### Severity model

Matched to Tier 1 so both reports can be read side by side.

| Severity | Meaning | Test |
|---|---|---|
| **blocker** | An agent following the set does the wrong thing or stalls. | Can you name the run that breaks? |
| **major** | Real inconsistency causing drift; the agent can still proceed. | Would two competent runs diverge? |
| **minor** | Hygiene or smell. May well be intentional. | Would a maintainer shrug? |

When choosing between two severities, pick the lower one and say why in the detail line. An
over-severe review gets ignored wholesale; an under-severe one still gets read.

**Finding IDs** are `<check>:<file-stem>:<subject-slug>` — e.g. `RF1:README:docs-DESIGN-md`,
`CF1:AGENTS_TEMPLATE:accepted-status-authority`. Deliberately line-independent, so an edit
above a finding does not orphan its baseline entry. Keep the subject slug stable across runs:
it is the same defect only if it carries the same id.

---

## 6. Output

Write **one file**: `eval/results/<YYYYMMDD-HHMMSS>-<set-name>-review/review.md`. Announce the
path when you finish. Write nothing else — no JSON sidecar, no summary file, no edits to the
set.

### 6.1 Report template

```markdown
# Instruction Set Review — <set name>

*Agentic eval · <UTC timestamp> · commit `<short sha>` · reviewer: <model id>*

## Verdict

<Two or three sentences: the state of the set, the single most important finding, and whether
an agent could run this pipeline today. No hedging, no throat-clearing.>

| Severity | Count |
|---|---:|
| Blocker | N |
| Major | N |
| Minor | N |
| *Suppressed (baseline)* | N |

## Coverage

| Group | Checks run | Findings | Not run |
|---|---|---:|---|
| RF — References | RF1–RF6 | N | — |
| CF — Conflicts | CF1–CF5 | N | — |
| RD — Redundancy | RD1–RD4 | N | RD3 (no rename history available) |

Files read in full: N of N. <Name any that were not, and why.>

## Findings

### <CHECK> — <check title> (N)

- **[blocker]** <One line stating the defect. Not the fix.>
  - `<finding-id>` · [file.md:120](path/file.md#L120) ↔ [other.md:44](path/other.md#L44)
  - **Why it matters:** <the concrete failure scenario from Pass 4.3 — which agent, which
    stage, what goes wrong.>
  - **Evidence:**
    > `file.md:120` — <verbatim quote>
    >
    > `other.md:44` — <verbatim quote>
  - **Counter-reading considered:** <the strongest defence from Pass 4.2, and why it fails.
    Required for every CF and RD finding.>

## Suppressed (baseline)

<id · one line · the recorded reason. Or "None.">

## Not verified

<Everything per §6.5. Never omit this section; write "Nothing — all checks ran to completion"
only when that is literally true.>

## Disagreements with Tier 1

<Per §1. Omit this section entirely when Tier 1 was not run.>
```

### 6.2 What the report is for

A maintainer should be able to read the Verdict and the blocker list and know what to fix
before lunch. Everything below that is supporting evidence for the findings they doubt. Write
accordingly: findings ordered by severity then check id, strongest first within a severity, and
never more than one paragraph of prose before the first table.

### 6.3 No recommendations section

Each finding's "why it matters" already implies the fix, and a separate recommendations list
invites a maintainer to apply changes without reading the evidence. Where a fix is genuinely
non-obvious — two valid resolutions with different consequences — name both options in that
finding's detail and say which you would pick.

### 6.4 Disagreements with Tier 1

If a Tier 1 finding looks wrong to you on a full reading, say so, with your reasoning, in that
section. Do not silently agree. The repository's rule is that a false positive means the
*check* is wrong and gets fixed — so your dissent is useful, and burying it is not.

### 6.5 Not verified

State plainly:

- Any file you did not read in full, and why.
- Any check you could not run, and what was missing (no state schema → RF3 skipped; no ID
  conventions → RF4 partial).
- Any candidate finding you dropped for lack of confidence rather than because you disproved
  it — one line each, marked as such.
- Any group whose finding count suggests miscalibration (per RD4).

**A skipped check is not a passing check.** The whole value of this review over a confident
skim is that it tells you where it did not look.

---

## 7. Suppressing a finding

`eval/review-baseline.md` records findings judged deliberate:

```markdown
- `RD4:AGENTS_TEMPLATE:constraint-obligations` — Intentional. The invariant is restated in
  AGENTS.md because stage files are not loaded during ad-hoc chat, and §Constraints names
  PROJECT_CONTEXT §4 as the authority. Reviewed 2026-09-10.
```

Three rules, inherited from the Tier 1 baseline and just as load-bearing here:

1. **The reason is not optional.** An unexplained suppression is indistinguishable from a
   defect swept under the rug.
2. **Suppression is per finding, never per check.** Suppressing one instance can never hide a
   new one from the same check.
3. **Never suppress a false positive.** If a finding is wrong, the *check definition* in §5 is
   wrong — fix the wording there so the next reviewer does not re-derive it. A baseline full of
   "this was a misreading" entries is a broken review method wearing a clean report.

---

## 8. Determinism and re-runs

This review is not deterministic and does not pretend to be. Two runs will differ at the
margins — mostly in MINOR findings and in how borderline calls land.

What must stay stable across runs:

- **Finding IDs**, so a baseline entry keeps working.
- **Blocker findings.** A blocker that appears in one run and not the next means one of the two
  runs was wrong. If you are re-reviewing a set and a previously reported blocker is absent,
  investigate and say which run you believe, in §6.5 — do not simply leave it out.
- **The report shape**, so two reports can be diffed.

For a decision that has to hold up — a release gate, a regression claim between two revisions of
a set — run the review **three times** and take the union of blockers plus the intersection of
majors. A single run is a good signal, not a verdict.

---

## 9. Invoking this review

```
Follow eval/INSTRUCTION_SET_REVIEW_INSTRUCTIONS.md. Review the instruction set in
ModernizationHarness/. The latest Tier 1 report is at eval/results/<latest>/report.md.
```

Optional additions to that prompt: a samples directory for artifact resolution ("generated
samples are in instruction_output/"), a restriction to one group ("RF and CF only — skip
redundancy"), or a named second set for comparison.

**Budget.** A full review of an eleven-file, ~60k-token set is one focused session. If you are
running out of room, do **not** silently narrow the sweep: finish the RF group (cheapest,
highest value), then CF, then stop and record RD as not run in §6.5. A complete review of two
groups beats a partial review of three that does not admit it.
