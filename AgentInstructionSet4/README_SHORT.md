# Quick Start

Modernize a legacy app with an agent, one testable phase at a time — you stay in control of
every increment.

**Five minutes to read. Then you're running.** For the reasoning behind any of it, see
[README.md](README.md).

---

## 1. Copy two files

```bash
cp AgentInstructionSet4/AGENTS_TEMPLATE.md   ./AGENTS.md      # project root
cp AgentInstructionSet4/0_INTAKE_TEMPLATE.md ./out/INTAKE.md
```

`AGENTS.md` keeps the agent honest in *every* chat, not just formal runs. Don't skip it.

## 2. Answer six questions

Open `INTAKE.md`. It has 22 questions — **six block the pipeline**, the rest have sensible
defaults. Answer these and you're done:

| Q | |
|---|---|
| 4 | What's the current stack? |
| 5 | What's the target stack? |
| 7 | Reuse the existing database, or new schema? |
| 9 | Will the old app keep writing to that database? |
| 11 | How does it authenticate today — keep it, or stub it? |
| 12 | Cutover: big-bang, strangler fig, or parallel run? |

Fill in more if you know it. Leave the rest blank — the agent applies defaults and **tells you
exactly which ones it answered for you**.

**Got a sample UI?** Answer Q23 with a path to some HTML/CSS, a mockup, or your design system.
The design stage turns it into a design language every phase builds from — which is what keeps
later screens looking like earlier ones.

## 3. Run four stages, once each

One prompt each, in order. Read the output before moving on.

```
Follow `0_PROJECT_CONTEXT_INSTRUCTIONS.md`. Intake: ./out/INTAKE.md.
Legacy app: ./legacy/. App: MyApp. Write output to ./out/.
```
→ `PROJECT_CONTEXT.md` + `state.json`. **Check the constraints it derived** — they drive everything downstream.

```
Follow `1_REQUIREMENTS_EXTRACTION_INSTRUCTIONS.md`. Context + state in ./out/.
Legacy app: ./legacy/. Write output to ./out/.
```
→ Three requirements docs. **Answer every `OPEN QUESTION:`.**

```
Follow `2_DESIGN_INSTRUCTIONS.md`. Everything in ./out/.
```
→ HLD + LLD. **Sanity-check the big decisions now** — changing them later costs rework.

```
Follow `3_PLAN_INSTRUCTIONS.md`. Everything in ./out/.
```
→ A phased plan. **Is phase 1 genuinely small?** If not, rerun this stage.

Unhappy with any output? Rerun that stage and say what you want different.

## 4. Build it, one phase at a time

```
Follow `4_PHASE_IMPLEMENTATION_INSTRUCTIONS.md`. Everything in ./out/.
This is a phase. Implement the next pending phase. Branch and open a PR.
```

The agent builds it, opens a PR, and **stops**. Then you:

1. **Test it** — follow that phase's test guide in the plan
2. **Say one of these:**

   | | |
   |---|---|
   | It works | **`accept P-1`** — merges the PR, records it, done |
   | It's broken | **`P-1 failed — search returns 500`** — reopens it, keeps the PR |
   | You want a change | describe it — the agent checks whether it contradicts the design first |

3. **Repeat** for the next phase.

Optionally, in a **separate chat**, audit a phase:

```
Follow `5_REVIEW_INSTRUCTIONS.md`. Target: P-1. Everything in ./out/. Codebase is this repo.
```
→ PASS, or findings that the next build run fixes. Run it in a fresh session — an agent can't
review its own work.

---

## Four things that'll trip you up

- **Never edit `state.json` by hand.** Just say what happened — "accept P-2", "P-2 failed" —
  and the agent writes it.
- **Say "accept" as its own message.** Asking for the next phase won't accept the current one;
  the agent will stop and point you back. That's deliberate.
- **Read the "Answered without you" list** after stage 0. Those are decisions you didn't make,
  and they propagate everywhere.
- **Keep `./out/` and `state.json` in git.** The agent diffs them to work out what changed
  between runs.

---

## When you just want to chat

Ask anything, anytime — questions and debugging are free. The moment the agent is about to
**change code**, it asks whether to run it through the phase process or do it directly. If you
say directly, it still logs the change so the next run knows the ground moved.

---

**Stuck, or want the "why"?** → [README.md](README.md)
