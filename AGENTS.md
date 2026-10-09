# AGENTS.md

Project-wide instructions for any coding agent working in this repository (Claude Code, Codex,
Copilot, Cursor, Gemini, and others).

> **Not to be confused with the harness's own `AGENTS.md`.** This file governs work *on this
> repository*. The `AGENTS.md` that the harness docs talk about is a different file: it is copied
> from [ModernizationHarness/AGENTS_TEMPLATE.md](ModernizationHarness/AGENTS_TEMPLATE.md) into a
> *target* project by the installers. When a document here mentions `AGENTS.md`, it means that
> one, not this one.

## How to explain things to me

Explain in **simple English, as if I am a beginner.** This applies to every answer,
every time — I should not have to ask for it.

- Short sentences. Plain words. One idea per sentence.
- **Define jargon the first time you use it**, in the same sentence or the next one —
  including terms that feel basic to you (branch, merge, PR, gate, state, schema, enum).
- Prefer a concrete example or a short analogy over an abstract description.
- Lead with the plain-English answer. Put file paths, line references, and exact
  wording *after* it, as support — not as the explanation itself.
- When something has several moving parts, walk them one at a time in order, and say
  why each one matters. Don't compress it into a dense paragraph.
- It is fine to be long if that is what plain language costs. Don't trade clarity for
  brevity.
- Still be accurate and complete. "Simple" means simple *wording*, not fewer facts, and
  not a softer verdict. Say plainly when something is broken, risky, or won't work.

## Scope of that instruction

It governs **how you talk to me** — chat replies, explanations, reviews, hand-off reports.

It does **not** govern the harness documents in [ModernizationHarness/](ModernizationHarness/)
(the `*_INSTRUCTIONS.md` files, `AGENTS_TEMPLATE.md`, the templates). Those are written for
*other AI agents* to follow as precise specifications, and their dense, exact style is
deliberate. Keep writing those in the voice they already have. If you are unsure which of the
two a piece of writing is, ask.

## Keep code and documents in step

Every change keeps the code and the documents saying the same thing. A change is not finished
until both match.

### Which document describes what

| If you change… | …check and update these |
|---|---|
| A stage file, template, or `AGENTS_TEMPLATE.md` in `ModernizationHarness/` | [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md), [docs/DESIGN.md](docs/DESIGN.md), [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md), [USE_CASES.md](USE_CASES.md), [README.md](README.md) — wherever they describe that behavior |
| [ModernizationHarness/tools/state.py](ModernizationHarness/tools/state.py) | its tests in [eval/tests/test_state_tool.py](eval/tests/test_state_tool.py); the stage files and `AGENTS_TEMPLATE.md` wherever they tell an agent how to use it; `state.json` schema in `0_PROJECT_CONTEXT_INSTRUCTIONS.md §Output 2`; DD-18 in `docs/DESIGN.md` |
| The `state.json` schema | Stage 0's schema, every stage that reads or writes the changed field, `state.py`, `docs/DESIGN.md §5` |
| [install.sh](install.sh) / [install.ps1](install.ps1) | each other (they must do the same thing), and the install steps in `README.md` and `DEVELOPER_GUIDE.md` |
| [ModernizationHarness/0_INTAKE_TEMPLATE.md](ModernizationHarness/0_INTAKE_TEMPLATE.md) | Keep its shape (R2.1–R2.2): one `###` heading per question with one `**Answer:**` line; a `*Default…*` line or a ⚠️ LOAD-BEARING mark on every question; at most one tick-box list per question, with a `*Tick …:*` label (e.g. *Tick one:*, *Tick all that apply:*). Split a question that asks two things into lettered parts (`12a`, `12b`). Eval check D5 reports a **major** finding if the shape breaks — it does not fail the run (only blockers do), so read the report. Then update [examples/INTAKE_EXAMPLE.md](ModernizationHarness/examples/INTAKE_EXAMPLE.md) and every place that cites a question id you changed |
| The eval code in [eval/evalkit/](eval/evalkit/) | [eval/README.md](eval/README.md), [eval/EVAL_DESIGN.md](eval/EVAL_DESIGN.md) |

The table is a starting point, not the full list. To find every mention, search the repo for the
name of the thing you changed (a command, a field, a file name, a stage name, an id like
`DD-18` or `R7.4`).

### The rules

1. **Code changed → update the documents in the same change.** If a document describes the
   behavior you changed, fix the document too. Do not leave it for later.
2. **Document changed → make the code match, or say it does not.** If a document now promises
   something the code does not do, either change the code in the same change, or tell me
   plainly that the two now differ and ask what I want.
3. **Found a mismatch you did not cause?** Tell me. Do not quietly pick one side and "fix" the
   other — the document may be the one that is right.
4. **Leave historical records alone.** Do not rewrite [eval/results/](eval/results/) or
   [docs/UNGATED_LOOP.md](docs/UNGATED_LOOP.md); they record what was true at the time.
5. **Say what you updated.** End every hand-off with a short list of the documents you changed,
   or one line saying why no document needed changing.

### Design changes: ask me first

Before you make a **design change**, stop and ask me. Explain in plain words what you want to
change, why, and which documents it touches. Wait for my yes before editing anything.

A change is a design change if it does any of these:

- adds, removes, or changes a design decision (`DD-<n>` in `docs/DESIGN.md`) or a requirement
  (`R<n>` in `docs/REQUIREMENTS.md`);
- changes the stages — their order, what each one reads or writes, or which stage owns a
  document;
- changes an invariant, the authority ladder, or what the developer versus the agent decides;
- changes the `state.json` schema, or what the state tool allows or refuses;
- adds a new stage, tool, template, or top-level file.

If you are not sure whether something is a design change, treat it as one and ask.

Things that are **not** design changes — just do them, and still update the documents:
fixing a typo or unclear wording, fixing a bug so the code matches what the documents already
say, adding tests, and making two documents agree where one is clearly out of date.

After I approve a design change, update `docs/DESIGN.md` and `docs/REQUIREMENTS.md` first, then
the harness files, then the guides.

### Check your work

After changing anything in `ModernizationHarness/` or `eval/`, run these from `eval/` and
report the results:

- `python tests/test_state_tool.py` — the state tool's tests.
- `uv run run.py --set ../ModernizationHarness --baseline baseline.json` — the instruction-set
  checks.
