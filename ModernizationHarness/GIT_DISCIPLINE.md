# Git Discipline — Stage 4 supplement *(agent git mode only)*

Load this file **only when `context.repo.git` is `agent` or missing**, alongside
`4_PHASE_IMPLEMENTATION_INSTRUCTIONS.md` or `4_MINOR_EDIT_INSTRUCTIONS.md`, and follow it as
part of that run. It adds the branch, commit, PR and merge rules to whichever unit of work —
phase or minor edit — the stage file is running. Under `developer`, do not load it: follow
`AGENTS.md §Git mode` instead.

---

## Conventions

**Follow the repository conventions recorded in `PROJECT_CONTEXT §3`.** The defaults below apply
only where it is silent. **Branch naming and commit conventions bind you. PR target branch
(`context.repo.prTarget`) and required reviewers are informational — no rule reads them:** you
target the branch you branched from and you never merge unasked, so neither changes what you do.
Name both in the PR body where set, so the developer knows where the work is headed and whether
their own merge needs a review.

## For every unit of work

- **Branch** from **whatever branch is currently checked out** (§Starting From the Right Base),
  named for the work (e.g. `phase/P-3-frontend-foundation`, `edit/add-department-filter`) —
  except where the developer said to work on the current branch (§Work on this branch).
  **For a phase, create it when you set the phase `in progress`** (Step 1).
- **Commit small, examinable steps** — ideally one commit per task, each message stating what
  changed and why, so history can be read later. Don't squash a whole phase into one commit.
- **Update, in the same branch:** the **tests**, the **documentation** (READMEs, the plan's test
  guide, **`FEATURE_STATUS.md`**, and **`HOW_TO_RUN.md`** if running the app changed), and
  **`state.json`** (statuses, change log).
- **Push the branch and open a PR back at the branch you started from** — pushing is required,
  since the PR cannot exist otherwise. Its **descriptive body** captures the history:
  1. **Initial task** — what was asked (the phase goal or the edit request).
  2. **Reasoning** — key decisions, and any reconciliation handled.
  3. **Outcome** — what was built, how it was verified, the runnable state, follow-ups.
- **Record `branch` and `prUrls`** on the phase's (or edit's) `state.json` entry, so the next
  run and the developer can find them. `prUrls` is always an array: one element under a
  `single` layout, under `split` **one per repo you opened a PR in** — every one, not just the
  first — and `[]` where no PR was asked for.
- **Never merge unless the developer asks you to, in those words.** The PR is theirs, to merge
  whenever they choose or not at all. You never need a merge (§Starting From the Right Base), so
  never ask for one, and never perform one because it would be tidy or because the stack is
  getting tall. **When they do ask** — *"merge P-3"* — merge every PR in that item's `prUrls`
  and report what you merged; nothing records merges, so there is no field to update. Then note
  which branch they are now on, since the one they were standing on is now spent.
- **Repository layout** (`context.repo.layout`). **`single`** — one branch and one PR per unit of
  work. **`split`** — branch every repo the work touches under the *same* branch name, and open a
  PR per repo whose body cross-references the others. The unit of work is not finished until
  every repo's PR is open.
- **Legacy files in a shared repo** (`context.locations.sharedWithLegacy`): you may branch and
  commit in that repo, but no commit of yours may touch a legacy file.

## Starting From the Right Base

Phases are built in sequence, so a phase's branch must start from something that already
contains the previous phase's work. The rule needs **no configuration at all** — the
developer's git state is the instruction:

1. **Read the branch that is currently checked out**, and name it in your report — **per repo**
   under a `split` layout; each repo is read and branched on its own.
2. **Branch from it**, do the work, and **open the PR back at it**.
3. **Leave the developer on the branch you created**, and stop.
4. **Unless they said to work on the current branch** — then create no branch and open no PR;
   commit there directly (below).

If they merged the last phase and are standing on `dev`, you branch from `dev` and the PR
targets `dev`. If they didn't and are still on `phase/P-2`, you branch from that and the PR
targets `phase/P-2`. Neither case is exceptional, and nothing stalls: **the next phase always
has its predecessor's code, because it starts from where that code is.** That is why nothing
here needs a merge to have happened.

**Git is the truth; `state.json` is a cache.** Before writing anything:

1. **Confirm the predecessor's work is present by content, not by name** — check that
   files/symbols the previous phase delivered actually exist there. Branch names and PR state
   are unreliable: squash-merge and rebase workflows discard the predecessor's branch and commit
   ids entirely, so a branch holding every line of P-2 can still report "not merged".
2. **Check whether the current branch is already finished** — its work merged into another
   branch, or the branch itself gone from the remote. This is the **common** case, not an edge
   one: the developer merges the previous phase's PR in the web UI, the host deletes the branch,
   and their local checkout stays on it. Every other check here still passes, because the code is
   present — the branch is simply spent. Branching off it produces a PR that targets a branch
   which no longer exists on the remote, so the work stops flowing toward where it was headed.
   **Say so and name the branch you would use instead**, then do what they say:
   > "You're on `phase/P-2`, which is already merged into `dev` and gone from the remote. I'd
   > branch P-3 from `dev` instead — it has P-2's work. Confirm, or name another branch."
   Prefer the branch it was merged into. Never push a deleted branch back up to make a PR fit,
   and never target a branch you know is spent.
3. **Say what you found, in one line, before you start:**
   > "Branching P-3 from `phase/P-2`. It contains P-2's work. (Note: `dev` has 2 commits not in
   > this branch.)"
   This one line is what makes branching from wherever they stand safe rather than reckless.
4. If the predecessor's work is **missing**, stop and ask — don't guess and never silently
   rebuild it. Offer the ways forward: they merge it or switch branch, you branch from the
   branch that does have it, or you build here anyway because they know why it's absent. This
   is a blocker: stop and report.

**A fix for delivered work** never goes onto a merged branch. If the broken phase's or edit's
branch is still unmerged and the developer is standing on it, the fix lands on top of it like
any other work.

### Work on this branch

**The no-PR case.** When the developer says to make the change on the
branch they are standing on (*"do it on this branch"*, *"no PR, just commit here"*), do exactly
that: **no new branch, no PR.** Everything else is unchanged — small self-describing commits,
tests, docs, `FEATURE_STATUS.md`, `state.json`. Record the branch you committed to in `branch`
and leave `prUrls` as `[]`. The PR body's history (initial task / reasoning / outcome) goes in
the commit messages instead. Under **`split`** this applies **per repo**: commit on each repo's
currently checked-out branch, touching only the repos the work needs; if those branches are not
the same name, say so before you start, so a later reader knows where each half landed.

## At hand-off

- **Open the PR** (above) as the step before the report — skip it only in the no-PR case.
- **In the report:** the branch you built on and what it contained; **the PR link, and which
  branch it targets — it is theirs to merge, whenever they choose.** Where PRs from earlier
  phases are also still open, name them in one line: *"P-4, P-5 and P-6 have open PRs that
  haven't been merged."* That is the only signal of how much work has stacked up unlanded — a
  report, not a request. They land such a chain **oldest first**: as each PR merges, the host
  re-points the one above it at the base branch.
- **Stop on the branch you created.**

## Definition of Done (git items — add to the stage file's checklist)

- [ ] Before any code: the **current branch** was read, checked **by content** for the
      predecessor's work and for being **merged or deleted on the remote**, and **named in the
      report**; a spent branch was raised with a proposed alternative, not built on.
- [ ] **Branch created from the current branch; small commits pushed; tests, docs and
      `state.json` updated; PR opened against its source branch with a descriptive body
      (initial task / reasoning / outcome)** — or, where the developer asked to work on the
      current branch, committed there with no branch, no PR, and `prUrls` left `[]`.
- [ ] **Nothing merged unless the developer asked in those words** — otherwise the PR is left
      open for them; other phases' open PRs named in the report.
- [ ] `branch` and `prUrls` recorded on the phase (or `edits[]` entry) — every repo's PR under
      `split`, `[]` where no PR was asked for.
