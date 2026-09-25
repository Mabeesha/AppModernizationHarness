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
                        └── next phase ◄─────────────────────────────┘
                                    ├─► you test whenever you like
                                    └─► [5] review (separate chat, optional)
```

Stages **0–3 run once each**, in order. Then **4 loops** — one phase at a time, until it's
done. **Nothing blocks:** you can run three phases before testing any of them, then test and
tick them off together. Testing is tracked per feature in `FEATURE_STATUS.md`, not per phase. Every document and the `state.json` that tracks progress live in
`./out/`; the code the agent writes goes to your target repo.

---

## 1. Set up

```bash
./install.sh            # macOS / Linux / Git Bash
```
```powershell
.\install.ps1           # Windows
```

That creates `./out/`, writes `AGENTS.md` and `out/INTAKE.md` from their templates,
installs the Angular agent skills into `.agents/skills/`, and adds `ModernizationHarness/`,
`AGENTS.md` and `.agents/` to the target's `.gitignore` (creating it if there isn't one —
entries already covered are left alone, and your existing content is never rewritten, only
appended to). It is safe to re-run: identical files are left alone, and anything it would
overwrite is moved to `.harness-backups/<timestamp>/` first — so a filled-in `INTAKE.md`
is never lost.

Note `./out/` is deliberately **not** ignored — the agent diffs those documents and
`state.json` between runs, so they belong in git.

Useful flags (same meaning in both, `--flag` in bash, `-Flag` in PowerShell):
`--target <dir>` to install somewhere other than the current directory, `--dry-run` to see
what it would do, and `--update` to re-vendor the Angular skills (below).

### The Angular skills

`.agents/skills/` is where the [GitLab Duo Agent Platform](https://docs.gitlab.com/user/duo_agent_platform/customize/agent_skills)
looks for agent skills, one directory per skill, each holding a `SKILL.md`.

What gets installed is the Angular team's own [angular/skills](https://github.com/angular/skills)
(MIT) — `angular-developer`, whose `SKILL.md` plus 40 reference files cover signals, forms,
DI, routing, testing, ARIA, styling and the CLI; and `angular-new-app` for scaffolding. They
are **vendored into `ModernizationHarness/skills/`** and committed, so installing works
offline and you can see exactly what your agents are being told.

`--update` re-downloads them and rewrites those directories, so upstream changes arrive as a
reviewable git diff. The upstream commit is recorded in `skills/.upstream-angular`, which is
also the list of directories `--update` is allowed to replace — **any skill you write
yourself is left untouched**, so this is where to put your own project conventions.

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

**Modernizing several apps?** See `ModernizationHarness/examples/INTAKE_EXAMPLE.md` — a worked
intake for a set of apps sharing one stack, auth model and deployment shape. It shows how to
pin the answers that are identical across the set, mark the per-app blanks, and append
load-bearing questions of your own (the template invites this at its close) for rules that have
no question — a no-shared-files boundary, an API-documentation standard. Copy it to
`out/INTAKE.md` per app and edit only what's marked.

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

The plan is a rolling forecast, not a fixed schedule: delivered phases drop off it, and the
remaining ones get re-checked before most build runs. What *doesn't* move is
**`FEATURE_STATUS.md`** — every requirement has a row there, and rows are never deleted.

## 4. Build it, one phase at a time

```
run stage 4
```

Branching and opening a PR is built in — you don't ask for it. It branches from **whatever
branch you're standing on**, points the PR back at that branch, leaves you on the new branch,
and **stops**. **It never merges** — every PR is yours. Then you:

1. **Merge it, or don't.** Nothing waits on it. If you leave the PR open, the next phase simply
   continues from this branch; merge it and check out your base branch, and the next phase starts
   from there instead. Either way the code is where the next phase needs it.
2. **Run the next phase whenever you want.** Nothing waits on you having tested anything either.
3. **Test when it suits you** — open `FEATURE_STATUS.md`, walk the rows that say `untested`,
   and use `HOW_TO_RUN.md` to get the app running. Every hand-off report tells you how many
   features are waiting, which ones this phase put back on the list, and which earlier PRs are
   still open.
4. **Say one of these when you have tested:**

   | | |
   |---|---|
   | It works | **`accept P-1`** — ticks every feature P-1 delivered. Several at once is fine: **`accept P-1, P-2, P-3`** |
   | Part of it works | **`search works`** — ticks that one row |
   | It's broken | **`P-1 failed — search returns 500`** — records it; the fix is planned as new work, never by reopening P-1 |
   | You want a change | describe it — the agent works out whether it's a minor edit or needs a design change first |

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
builds it. P-3 is never reopened — what is built is built, and the retrofit is new work. The
feature rows it changes go back to `untested` so you know to re-check them.

That's it. The second prompt is the one you always use, so a mid-build design change costs
exactly one extra prompt.

---

## Five things that'll trip you up

- **Never edit `state.json` or `FEATURE_STATUS.md` by hand.** Just say what happened —
  "accept P-2", "search works", "P-2 failed" — and the agent writes it.
- **Merging is entirely yours.** The agent never merges, so untested code only reaches `main`
  if you put it there. The flip side: if you never merge, phases stack as a chain of open PRs
  and you land them bottom-up later. Watch the open-PR line in each report.
- **Want the change on the branch you're on?** Say *"do it on this branch"* — no new branch, no
  PR, just commits where you are.
- **"accept" records testing; it unblocks nothing.** You can accept several at once when you
  name them. What gets challenged is the vague version — "accept everything so far" — which
  usually means nothing was tested; the agent turns it into the explicit list and asks you to
  confirm.
- **Watch the two counts** in every hand-off report: features awaiting your testing, and open
  review findings. With nothing blocking, those numbers are your only warning that the build
  has run a long way ahead of anyone checking it.
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
review blocker? → [USE_CASES.md](USE_CASES.md) walks each one with the
exact prompt.

**Stuck, or want the "why"?** → [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
