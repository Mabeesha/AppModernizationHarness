# Quick Start

Modernize a legacy app with an agent, one testable phase at a time — you stay in control of
every increment.

**Five minutes to read. Then you're running.** For the reasoning behind any of it, see
[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md).

---

## The whole thing, in one picture

```
 setup ─► [0] context ─► [1] requirements ─► [2] design ─► [3] plan ─┐
          fill INTAKE     what it does        HLD + LLD    phases    │
                                                                    ▼
                        ┌──────────────────────────────────► [4] build one phase
                        │                                           │
                        └── you test ◄── accept / report failure ◄──┘
                                    └─► [5] review (separate chat, optional)
```

Stages **0–3 run once each**, in order. Then **4 loops** — one phase, you test, you accept,
repeat — until it's done. Every document and the `state.json` that tracks progress live in
`./out/`; the code the agent writes goes to your target repo.

---

## 1. Set up

```bash
mkdir -p out
cp ModernizationHarness/AGENTS_TEMPLATE.md   ./AGENTS.md      # project root
cp ModernizationHarness/0_INTAKE_TEMPLATE.md ./out/INTAKE.md
```

The six numbered stage files stay in `ModernizationHarness/` — you never copy those.

`AGENTS.md` does two jobs. It keeps the agent honest in *every* chat, not just formal runs —
don't skip it. And its first section records where those stage files live, which is why you
can name them bare in a prompt. Moved the folder? Change that one line and everything below
still works.

## 2. Answer six questions

Open `out/INTAKE.md`. It has 24 questions — **six block the pipeline**, the rest have sensible
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

**Worth doing too:** Q16 says where the legacy code, the docs, and the **target repo** live. Get
it right and you never type a path again (see below).

**Got a sample UI?** Answer Q23 with a path to some HTML/CSS, a mockup, or your design system.
The design stage turns it into a design language every phase builds from — which is what keeps
later screens looking like earlier ones.

**Got example code you want followed?** Answer Q24 with a path per area — deployment files,
auth, file upload/download, logging. Say for each whether it's a *reference* (follow its shape,
use your own names) or *literal*, and what it governs. Every stage then builds to it, and Review
checks both that it was followed and that nothing outside its scope was copied along with it.

## 3. Run four stages, once each

You ask for a stage by name — **`run stage 2`** or **`run the design stage`**, whichever you'd
say out loud. `AGENTS.md` maps both to the right file.

**Stage 0 is the only one that needs paths.** It writes `state.json`, and every stage after it
reads its own inputs from there — so the rest really are just four words.

```
run stage 0 — intake: ./out/INTAKE.md, legacy app: ./legacy/, app: MyApp,
write to ./out/
```
→ `PROJECT_CONTEXT.md` + `state.json`. **Check the constraints it derived** — they drive everything downstream.

```
run stage 1
```
→ Three requirements docs. **Answer every `OPEN QUESTION:`.**

```
run stage 2
```
→ HLD + LLD. **Sanity-check the big decisions now** — changing them later costs rework.

```
run stage 3
```
→ A phased plan for **remaining work**. **Is phase 1 genuinely small?** If not, say so now.

Read each output before moving on. Unhappy with one? **`rerun stage 2 — the API should be REST,
not GraphQL`** — everything after the dash is what you want changed. Reruns are normal, not a
sign something went wrong.

The plan is a rolling forecast, not a fixed schedule: accepted phases drop off it, and the
remaining ones get re-checked before most build runs. What *doesn't* move is the **Coverage
Matrix** — every requirement has a row there, and rows are never deleted.

## 4. Build it, one phase at a time

```
run stage 4
```

Branching and opening a PR is built in — you don't ask for it. The agent builds the phase,
opens the PR, and **stops**. Then you:

1. **Test it** — follow `HOW_TO_TEST.md` (one file, always current: *New in P-N* first, then
   the accumulated regression checks). The agent tells you which regression lines this phase
   put at risk.
2. **Say one of these:**

   | | |
   |---|---|
   | It works | **`accept P-1`** — records it and merges the PR (if your repo requires reviewers or green CI, it records the acceptance and leaves the merge to you) |
   | It's broken | **`P-1 failed — search returns 500`** — reopens it, keeps the PR |
   | You want a change | describe it — the agent works out whether it's a minor edit or needs a design change first |

3. **Repeat** for the next phase.

Optionally, in a **separate chat**, audit a phase:

```
run stage 5 on P-1
```
→ PASS, or findings that the next build run fixes. Run it in a fresh session — an agent can't
review its own work.

---

## Changing the design halfway through

You're at P-6 and need to change auth — which was built in P-3. **Two prompts:**

```
rerun stage 2 — change auth from the local stub to OIDC against Keycloak,
bearer tokens
```
→ Design amended in place, with a note recording that **P-3 and P-5** are now out of date.
**Be specific about what you want** — the agent will otherwise ask, or assume.

```
run stage 4
```
→ It proposes adding **P-8 "migrate auth to OIDC"**, to run *before* P-6. You approve; it
builds it. P-3 stays accepted and is never reopened — the retrofit is new work.

That's it. The second prompt is the one you always use, so a mid-build design change costs
exactly one extra prompt.

---

## Five things that'll trip you up

- **Never edit `state.json` by hand.** Just say what happened — "accept P-2", "P-2 failed" —
  and the agent writes it.
- **Say "accept" as its own message, one item at a time.** Asking for the next phase won't
  accept the current one, and "accept everything so far" gets challenged — both mean nothing
  was actually tested. The agent stops and points you back. That's deliberate.
- **Read the "Answered without you" list** after stage 0. Those are decisions you didn't make,
  and they propagate everywhere.
- **Keep `./out/` and `state.json` in git.** The agent diffs them to work out what changed
  between runs — and git is the only history of superseded design and plan versions, since
  documents are amended in place rather than copied to new filenames.
- **Phase numbers stop being sequential.** A retrofit added at P-8 may run before P-6. That's
  deliberate: IDs are permanent so PRs and reviews keep meaning what they said. Read the plan
  for the running order.

---

## When you just want to chat

Ask anything, anytime — questions and debugging are free. The moment the agent is about to
**change code**, it asks whether to run it through the phase process or do it directly. If you
say directly, it still logs the change so the next run knows the ground moved.

---

**Hit a situation this page doesn't cover** — a failed phase, a mid-build design change, a
review blocker? → [USE_CASES.md](ModernizationHarness/USE_CASES.md) walks each one with the
exact prompt.

**Stuck, or want the "why"?** → [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
