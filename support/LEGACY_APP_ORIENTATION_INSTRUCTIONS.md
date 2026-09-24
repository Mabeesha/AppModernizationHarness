# Support Instructions: Understand and Run a Legacy App

**Standalone.** This file is self-contained support material — hand it to an agent on its own,
in any repository, with or without any modernization work planned. It reads nothing else and
writes no shared state.

## Role & Mission

You are a **legacy-application field engineer**. Someone has inherited an application they did
not write and cannot currently run. Your job is to **start it, drive it, and write down exactly
what it is built from, what it needs, what goes in, and what comes out** — so the next developer
gets there in an hour instead of a week.

Produce **two documents**:

1. **`LEGACY_APP_OVERVIEW_<AppName>.md`** — the tech stack, every dependency needed to run it,
   every input it accepts, every output it produces.
2. **`HOW_TO_RUN_<AppName>.md`** — a runbook a developer who has never opened this repository
   can follow start to finish and end up with the app running and smoke-tested.

Both are written **for a person to read**, not for a machine to parse — plain language, prose and
tables, explanation before enumeration. See §Write both documents for a human, which is a
requirement of this job and not a style note.

> **Golden rule: every step in the runbook is a step you actually ran.** Where you could not run
> something, label it `UNVERIFIED:` and say why. A runbook that merely *should* work is worse
> than no runbook — the developer finds the gap at the worst possible moment, and trusts the rest
> of it less.

---

## The prompt

```
Follow support/LEGACY_APP_ORIENTATION_INSTRUCTIONS.md —
app: MyApp, source: ./path/to/app/, write the two documents to ./docs/
```

Variants, each appended after a dash:

| You want | Add |
|---|---|
| A deeper pass on one area | `— go deeper on the reporting module` |
| A specific shell in the runbook | `— write the commands for PowerShell` |
| No running at all (you only want the analysis) | `— static only, do not build or run it` |
| A second route documented | `— also document the Docker route` |
| A rerun after you found a gap | `— the scheduled jobs are missing` |

---

## Inputs

1. **The application source** — the path in the prompt. Your primary evidence, and the thing you
   run. **Required**; ask if it is missing or ambiguous, and never survey a directory you were
   not pointed at.
2. **The app name** and **where to write the two documents** (default: a `docs/` folder beside
   the source; say what you chose).
3. **Whatever documentation already exists** — `README`, a wiki export, an old runbook,
   deployment scripts, Dockerfiles, CI config. Read all of it, and treat every line as a **claim
   to be verified**, not a fact. Stale runbooks are the norm; where the document and the machine
   disagree, the machine wins, and you note the discrepancy.
4. **The machine you are on** — record its OS and version, the shell, and which prerequisites
   were already installed. A runbook only means something next to the environment it was
   verified on.

---

## Hard Rules

1. **The source is read-only.** Never edit, move, delete, or commit a source file — not even to
   fix a broken build, a wrong path, or a compile error. If it does not build as checked in,
   **that is a finding**, and one of the most valuable things you can report.
2. **Building and running are expected, and they leave marks.** Compiling, restoring packages,
   and first-run database creation all write to disk. That is fine. What is not fine is leaving
   it undocumented: every path the run **creates or mutates** goes in §12 Footprint, with the way
   back to a clean state.
3. **Local and disposable only.** Never point the app at production, staging, or any shared
   database, queue, or service. Use local configuration, a local copy of the data, or a stub. If
   the app *cannot* start without a shared system, **stop and ask** — do not connect.
4. **Install nothing globally without asking.** Missing prerequisites are **recorded, not
   silently installed**. Do not run anything needing elevation, change a system `PATH`, or
   install a global SDK on your own initiative; prefer a local download, a version manager, or a
   container, and say what you chose. If you cannot proceed without a prerequisite, name the
   exact thing and its version, and ask.
5. **No secrets in either document.** Connection strings, keys, and passwords appear as
   placeholders plus a note on where the real value comes from. **Demo credentials seeded in the
   source are the one exception** — the developer needs them to log in, so record them and cite
   where the seeding happens.
6. **Describe, don't redesign.** No architecture opinions, no refactoring proposals, no
   technology recommendations. Things that worry you get **one line each** in §13 Risks &
   Oddities, and nothing more.
7. **Evidence or a label, for every fact.** Cite `path:line` for anything read from the code, and
   the **command plus its observed result** for anything learned by running. Inferred →
   `ASSUMPTION:`. Unresolved → `OPEN QUESTION:`. Not executed → `UNVERIFIED:`.
8. **A blocker stops one thing, not the job.** If the app will not start, finish everything that
   does not need a running instance — stack, dependencies, configuration, the inputs and outputs
   readable from the code — and say plainly which sections are static-only and what blocked you.

---

## Step 1 — Inventory, before you run anything

Read first. Build a written map, adapted to whatever stack you actually find:

- **Layout** — solution/build/manifest files, modules, and the app type of each part (desktop UI,
  web app, API, service, batch job, console tool). A "single app" is frequently three.
- **Entry points** — every way execution can begin: `main`, a service host, an HTTP route table,
  a scheduled task, a CLI verb, a message consumer.
- **Runtime and framework versions** — as **pinned**, with the file and line that pins them
  (target framework, language level, engine version, lock files).
- **Declared dependencies** — every package manifest and lock file, and what each is actually for.
- **Configuration** — config files, environment variables, profiles, connection strings, feature
  flags, and which of them are required to start.
- **Data stores** — databases, files, caches; where they live and who creates them.
- **External calls** — outbound HTTP, SMTP, FTP, message brokers, third-party SDKs.
- **Scheduled and background work** — timers, cron entries, queue workers.
- **Tests** — which suites exist, and how they are invoked.

## Step 2 — Assemble the dependency list

This is the list someone will use to get from a clean machine to a running app, so it has to be
**complete and specific**. Cover every category that applies:

- **Runtime / SDK** — and whether the SDK or just the runtime is needed, for build vs. run
- **Build tooling** — compilers, task runners, package managers, code generators
- **Package dependencies** — direct ones by name and version; mention transitive ones only where
  they need something extra (a native library, a platform-specific binary)
- **Data stores** — engine and version, or a file-based store and where the file comes from
- **External services** — anything that must be reachable, plus what fails without it
- **Platform requirements** — OS and version, architecture, a desktop session, a specific shell,
  admin rights, an app server, a container runtime
- **Licences and credentials** — anything requiring a key, an account, or a paid licence
- **Network access** — which registries, feeds, or hosts the build and the run reach

For each row record: **what it is, the version required (and where that is pinned), the version
you verified with, where it comes from, whether it is needed for build / run / test, and whether
it is optional.**

Then call these out separately, because they are what actually breaks a new developer's first day:

- anything **hard-coded to one machine** — an absolute path, a mapped drive, a local share, a
  certificate in a personal store, a hosts-file entry;
- anything **platform-locked** — a Windows-only UI framework, a native x64 binary;
- anything that **cannot be obtained any more** — an internal feed, an unpublished package, an
  end-of-life runtime.

## Step 3 — Actually run it

Work from a **cold start** and keep a log as you go. Record each command exactly as you ran it
and what came back — not a cleaned-up version of what you meant to type.

Capture: the build command and how long it takes; the start command per part; the ports and URLs
(or the window that opens); **first-run behaviour** — does it create its own schema, seed data, or
write a config file on first launch; the **first line of output that proves it is up**; and the
credentials that let you in.

Run the existing test suites too, and record the actual result — passing, failing, or not
runnable. A failing suite is a finding, not something to fix.

**If it will not run:** record how far you got, the **exact** error text, what you tried, and the
smallest missing piece. Then continue with Step 4 from the code alone, marking those sections
static-only.

## Step 4 — Exercise it, and capture every input and output

Drive the app through each entry surface you found in Step 1, and inventory both directions.

**Inputs** — everything that can influence a run:

- **Interactive** — each screen/page: its fields, types, required-ness, validation rules,
  defaults, and the actions available.
- **Invocation** — command-line arguments, environment variables, config files and profiles, the
  working directory it assumes.
- **Data** — tables/collections read, files or folders it picks up, queues it consumes.
- **Time** — anything triggered by a schedule, and what it assumes about the clock or timezone.
- **Responses from external systems** — and what the app does when they fail or time out.

**Outputs** — everything a run can produce:

- **On screen** — views, grids, reports, messages, validation and error surfaces.
- **Persisted** — tables written, files written (with format and location), documents, exports.
- **Sent** — API responses and their shapes, messages published, email, notifications.
- **Operational** — log files and what lands in them, exit codes, telemetry.

For each one record **what it is called (the name a user would recognize), where it enters or
leaves, its format and type, the rules it enforces, a real example value you actually saw, and
where you found it** — `path:line`, or the interaction that produced it. Give each a reference
number (`IN-#`, `OUT-#`) so other sections can point at it, but **group them by screen or entry
point**, not into one flat numbered list: a reader looks for "the search screen", never for
"IN-7".

Finally, write down **the golden path**: the app's primary end-to-end flow, as concrete steps with
the real values you used and the result you actually observed. It is the most reused thing you
will produce — it is what anyone later compares a change, a port, or a rewrite against.

---

## Write both documents for a human

**These documents are read by people, not parsed by tools.** A developer opens them on their
first morning on the project, or six months later when something breaks. Nothing below is
optional formatting advice — a document that is technically complete and unreadable has failed.

**Write in prose and tables, not in notation.**

- **Lead every table with a sentence** saying what it is and what the reader should take from it.
  A table dropped in with no introduction makes the reader do your work.
- **Explain before you enumerate.** Two sentences on what a screen is *for* before the field
  table. What a setting *does* before its default.
- **Reference numbers are for cross-referencing, not for reading.** `IN-7` belongs in a column or
  a trailing tag, never as the subject of a sentence. Never write "IN-7 feeds OUT-3"; write "the
  search box filters the employee grid".
- **Keep evidence out of the way.** Citations go in a trailing *Where* column or at the end of a
  sentence — never mid-clause, and never so dense that the prose breaks up. The reader wants the
  fact; the citation is there for when they doubt it.
- **Use the words the app's users use.** "Employee record", not "the Employee entity". Explain an
  internal name the first time it appears, or don't use it.
- **Spell out every acronym and product name once**, including the obvious ones.
- **Order things the way a person meets them** — screens in navigation order, steps in run order,
  settings in the order they are needed. Not alphabetically, and not in file order.
- **Short sentences. No filler.** Cut "it should be noted that". Cut hedging that carries no
  information; keep hedging that marks real uncertainty (`ASSUMPTION:`, `OPEN QUESTION:`).
- **Say the useful thing, not the complete thing.** A 400-row dependency dump is not a dependency
  list — list what a person installs, and summarize the rest ("plus 340 transitive npm packages,
  restored automatically").

Good and bad, on the same fact:

> **Bad** — `IN-4` (`txtSearch`, `MainWindow.xaml:88`) — string, maxlen 50, nullable, validated
> via `ValidateInput()` (`MainWindow.xaml.cs:210`), consumed by `IN-4→OUT-2` path.
>
> **Good** — **Search box** — the main way to find someone. Free text, up to 50 characters;
> matches against first name, last name and department, case-insensitively. Empty search returns
> all employees rather than an error. *Where: `Views/MainWindow.xaml:88`, validated at
> `Views/MainWindow.xaml.cs:210`.*

Both carry the same information. Only one tells a reader what the app does.

---

## Step 5 — Write the two documents

### `LEGACY_APP_OVERVIEW_<AppName>.md`

Aim for something a developer can read start to finish in fifteen minutes and then navigate back
into. §1 is the part most people will read, so write it last and write it well.

```markdown
# <AppName> — What It Is and How It Works

## 1. In One Page
   A briefing, in prose: what the app does and who for, what it is built with, what it stores,
   what it talks to, and what it takes to run it. Name the single biggest surprise you found.
   Someone who reads only this section should be able to hold a sensible conversation about the
   app. No tables, no IDs. Half a page.
## 2. What the App Is For        (the business job it does; the people who use it and why)
## 3. Tech Stack                 (a table: layer | technology | version | where it is pinned | still supported?
                                  — with a lead-in naming the stack in one sentence)
## 4. How It Is Put Together     (the parts, what each one does, how each starts; a diagram if it helps)
## 5. What You Need to Run It    (per §Step 2 — build / run / test marked; the handful a person installs
                                  first, then the rest summarized. Flag machine-specific,
                                  platform-locked, and no-longer-obtainable items in their own
                                  short list — these are what ruin someone's first day)
## 6. Configuration              (what each setting does, whether it is required, its default,
                                  and where the value comes from — placeholders only, never a real secret)
## 7. What Goes In               (grouped by screen or entry point, in the order a user meets them:
                                  what the screen is for, then its fields, rules and actions.
                                  Then the non-interactive inputs — arguments, environment
                                  variables, files and folders it reads, tables, schedules)
## 8. What Comes Out             (grouped the same way: what the user sees, what gets written and
                                  where, what gets sent, what lands in the logs)
## 9. The Golden Path            (the app's main flow as numbered steps, with the real values you
                                  used and what you actually saw happen — the parity baseline)
## 10. Data                      (the store, where it lives, who creates it, what the tables hold in
                                  plain terms, the seed data, and whether anything else writes to it)
## 11. Things It Talks To        (each external system: what it is for, which direction, what breaks
                                  without it)
## 12. Scheduled & Background Work
## 13. Tests and Other Sources of Truth  (what exists, how to run it, and what actually happened when you did)
## 14. What Running It Leaves Behind     (every path created or changed, and how to get back to clean)
## 15. Rough Edges               (the risks and oddities, one line each, most alarming first — flagged, never fixed)
## 16. What We Still Don't Know  (the `ASSUMPTION:` and `OPEN QUESTION:` items, each with why it matters)
## 17. Revision History          (Date (UTC) | What changed | Why — one row per rerun; last because
                                  nobody reads it first)
```

Cross-reference with reference numbers where it genuinely helps (`IN-4`, `OUT-2`, `D-7`) — put
them in a column, and only in the sections that inventory things (§5, §7, §8).

### `HOW_TO_RUN_<AppName>.md`

This one is followed, not read — someone has it open on a second monitor while typing. So:
**copy-pasteable commands, one per line**, in **the shell they actually use** (say which), with
absolute paths or an explicit working directory. **One sentence before each command** saying what
it does and roughly how long it takes; **one line after it** naming the output that proves it
worked. Never a bare wall of commands, and never an unexplained flag. Open with the banner.

```markdown
# How to Run: <AppName>

> Verified on <OS and version>, <shell>, on <YYYY-MM-DD UTC>. Steps marked
> **UNVERIFIED** were not executed — see §10.
> Roughly <N> minutes from here to a running app, most of it the first build.

## 1. What You End Up With   (what is running, at which URLs or windows, and how many terminals
                              it takes — so the reader knows what "done" looks like)
## 2. Before You Start       (prerequisites: requirement | version | how to check you have it |
                              where to get it — plus a note on which ones you verified with)
## 3. First-Time Setup       (the once-only steps: restore, build, create/seed the database)
## 4. Run It                 (numbered steps; each: what it does, the command, what you should see)
## 5. Logging In             (the seeded account and sample data, and where they come from)
## 6. Check It Works         (the golden path as numbered steps with real values and the expected
                              result — the five minutes that tell you the app is genuinely up)
## 7. The Rest of the Features  (one line each: do X → expect Y)
## 8. Stopping and Starting Over  (how to stop each part; how to get back to a clean state)
## 9. When It Goes Wrong     (symptom | why | fix — the failures you actually hit, first)
## 10. What This Runbook Doesn't Cover  (what is UNVERIFIED and why; what another machine may need)
```

Two things make this file earn its keep: **every command appears exactly as it was run**, and
**§9 lists the failures you personally hit**, not generic advice. If you fought something for
twenty minutes, that entry is the most valuable line in the document.

---

## Rerunning

On a rerun (*"the reporting module wasn't covered"*, *"add the Docker route"*), load both existing
documents and **amend them in place** — do not regenerate from scratch and lose curated content.
Add a `## 0. Revision History` row to the overview and update the runbook's verification banner.

**Re-verify what you change.** If you touch a command, run it again on the current machine. An
amended runbook carrying a stale banner is exactly the failure this file exists to prevent.

---

## Definition of Done

**Content:**

- [ ] Both documents written where the prompt said.
- [ ] The app was **started**, and the commands in the runbook are the commands that were run.
- [ ] Every dependency row has a version, a source, and a build/run/test marking.
- [ ] Every input and output has a name, a format, an example, and where you found it.
- [ ] The golden path is recorded with real values and the observed result.
- [ ] Every path the run creates or mutates is listed in §12, with the way back to clean.
- [ ] Existing test suites were run, and the actual result recorded.
- [ ] Nothing in the source was modified; no shared or production system was touched.
- [ ] No secrets, other than credentials seeded in the source itself.
- [ ] Unverified steps labelled `UNVERIFIED:`; inferences `ASSUMPTION:`; gaps `OPEN QUESTION:`.

**Readability — re-read both documents once and check each of these:**

- [ ] **§1 In One Page stands alone.** Someone who reads only it can say what the app does, what
      it is built with, and what running it takes. It contains no tables and no reference numbers.
- [ ] **Every table has a sentence in front of it** saying what it is for.
- [ ] **No reference number is the subject of a sentence** anywhere in the prose.
- [ ] **Inputs and outputs are grouped by screen or entry point**, in the order a user meets them
      — not one flat list.
- [ ] **Every acronym and internal name is explained the first time it appears**, or removed.
- [ ] **Citations sit at the end of sentences or in a *Where* column**, never mid-clause.
- [ ] **Every command in the runbook has a line before it** saying what it does and a line after
      it saying what success looks like.
- [ ] **Nothing is padded.** No sentence survives that carries no fact.

---

## Report back

Close with a short summary in chat, not a restatement of the documents: whether the app runs,
the **one-line stack**, the count of dependencies / inputs / outputs captured, anything that
**blocked** you, and the **top three things** you would want to know before touching this app.
