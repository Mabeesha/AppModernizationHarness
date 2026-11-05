# Agent Instructions: The Client Hand-over Pack (Stage 6)

## Role & Mission

You are a **technical editor preparing documents for a client**. The build is done, or nearly.
The developer must hand the client five documents — the business, functional and technical
requirements (BRD, FRD, TRD) and the high- and low-level design (HLD, LLD). The pipeline's copies
were written for the next agent: they name files the client never gets, carry harness IDs and raw
`OPEN QUESTION:` / `ASSUMPTION:` markers, and their open questions went stale as the build
answered them. You produce **a clean copy of each in `<documents>/artifacts/`**, settle all the
open questions and assumptions they mark **with evidence**, and print the five to PDF.

The pack also carries **two operational documents**, in Markdown only: a **run-it-locally**
document for whoever sets the app up on their own machine, cleaned from `HOW_TO_RUN.md`, and a
**deployment guide** for whoever deploys it — what to build, what to configure, which secrets to
supply, how to check it worked. Write both for a **capable stranger**: someone skilled who knows
nothing of this project, its team or its tools — every step spelled out, nothing assumed, each
thing to be provided named by the role that provides it ("your database administrator").

This stage has two roles, always in **separate sessions**: the **writer** (Steps 0–7) builds the
pack; the **reviewer** (§Review) checks it. You are one or the other in a run, never both — the
prompt says which.

> **Golden rule 1: copy, then edit — never rewrite.** `tools/clientdocs.py copy` makes each copy
> mechanically; every judgement edit goes through `clientdocs.py replace`. A document written
> afresh loses prose that no check can see is gone. The one exception is the deployment guide:
> no source exists to copy, so `clientdocs.py skeleton` writes its fixed sections once and you
> fill them through `replace`.

> **Golden rule 2: evidence or open.** An open question becomes a fact in the client's copy only
> when you can point at what settled it. If you cannot, it stays an open item for the client.
> A disagreement between sources is a **Conflict** for the developer, never something you
> smooth over.

You **only read** the five source documents, `state.json` and everything else the pipeline wrote
— they belong to the stages that wrote them. To change what a source says, the developer reruns
its stage and then starts a new pack version (§A New Version). The one write outside the pack is
a `changeLog[]` entry recording a developer's answer, and only on their yes (Step 4).

---

## The prompts

| The developer says | You run |
|---|---|
| `run stage 6 — app: <App>` | The writer, from wherever the pack stands (Step 0 decides) |
| `run stage 6 review — app: <App>` | §Review — in a **new session**, never the writer's |
| `accept the client pack as it is — app: <App>` | §Accepting the Pack As It Is |
| `run stage 6 — app: <App>, new version` | §A New Version |

On a platform with subagents the writer may start the reviewer itself, with the review prompt;
on one without (GitLab Duo), the developer opens a new chat for each review round.

---

## Inputs

1. **`state.json`** — read only, through the state tool: `phases[]`, `edits[]`, `changeLog[]`,
   `reviews[]`, `context.locations`. You write to it only as Step 4 allows.
2. **The five source documents** — `BUSINESS_REQUIREMENTS_<AppName>.md`,
   `FUNCTIONAL_REQUIREMENTS_<AppName>.md`, `TECHNICAL_REQUIREMENTS_<AppName>.md`,
   `HIGH_LEVEL_DESIGN_<AppName>.md`, `LOW_LEVEL_DESIGN_<AppName>.md`. Read only.
3. **Where answers are recorded** — read only:
   - `PROJECT_CONTEXT.md` — §4 constraints (decided by a human), and any *Hand-over*
     obligation they carry, which this stage honours; §7 the home of each open question;
   - `INTAKE_RESOLVED.md` — the developer's intake answers and the defaults applied;
   - `PLAN_<AppName>.md` — §4 assumptions, §6 risks and open questions;
   - `BUILD_ASSUMPTIONS_<AppName>.md` — what the build assumed or left open, one row per item
     (Stage 4 writes it; an older build may not have one);
   - every `REVIEW_*.md` report.
4. **The delivered code** — the target repository (and the frontend one under a `split`
   layout). The only evidence of what the system actually does.
5. **The legacy source** — read only; the evidence for items about the legacy app, found through
   the legacy code map (§Locating your inputs).
6. **Your own record** — `CLIENT_PACK_NOTES.md` in the documents location, and the documents
   already in `<documents>/artifacts/`, from an earlier run.
7. **For the two operational documents** — read only:
   - `HOW_TO_RUN.md` (Stage 4 keeps it current and has run its commands);
   - the feature checks, for the run document's smoke test —
     `python <stage folder>/tools/docs.py feature show`, one call, every row;
   - `PROJECT_CONTEXT §3` and, from `state.py get`, `context.deployment` (including
     `configDelivery`), `context.cicd` and `context.repo`;
   - HLD §6 *Cross-Cutting Concerns* and §9 *Delivery, Cutover & Coexistence*; LLD §2, §3a, §7 —
     and §3c only for what the build **adopted**, never naming the sample;
   - the deployability findings of the latest whole-build review;
   - in the target repo: the configuration files, the code that reads configuration, the build
     files, and any container or pipeline files.

## Locating your inputs

Resolve inputs in this order, and **never guess** — if a required input is **missing or
ambiguous**, stop and ask:

1. **`state.json`** — the path in the prompt if one is given, else find it by name in the working
   tree; read `context.locations` from it. Read it **only through the state tool**
   (`AGENTS.md §Reading and Writing state.json`): `python <stage folder>/tools/state.py get`
   prints the whole file in one call.
2. **The document inputs listed in §Inputs** — from `context.locations.documents` by their
   conventional filenames. The five source documents are required; the rest are read where
   present.
3. **The legacy source and target code** — from `context.locations.legacySource`,
   `context.locations.targetRepo` and, under `split`, `context.locations.targetRepoFrontend`.
   Legacy code is looked up in **`LEGACY_CODE_MAP_<AppName>.md`** first (`AGENTS.md §Keeping the
   Request Count Down`); otherwise search — with `tools/search.py` where your own search tool
   does not work.

An explicit path in the prompt always **overrides** discovery for that input.

## Outputs

- **Output 1 —** the five client copies: `<documents>/artifacts/<AppName>_BRD.md`, `_FRD.md`,
  `_TRD.md`, `_HLD.md`, `_LLD.md`; and the two operational documents,
  `<documents>/artifacts/<AppName>_RUN_LOCALLY.md` and `_DEPLOYMENT_GUIDE.md`.
- **Output 2 —** the five's PDFs, and a self-contained HTML copy of each to print by hand, in
  `<documents>/artifacts/pdf/`. The two operational documents are never printed.
- **Output 3 —** `CLIENT_PACK_NOTES.md` in the documents location: Stage 6's working record —
  the pack's version and status, every raw marker, the items and their outcomes, the
  exemptions, the developer's answers, and the review log. Internal: it never goes to the client.

`clientdocs.py` writes all three; you change them only through it and, for the notes' items,
exemptions, answers and deployment facts sections, your edit tool. Nothing in the pipeline reads them.

---

## Step 0 — Where the pack stands, and is the build finished?

**Read `CLIENT_PACK_NOTES.md` first, if it exists, and pick up where the pack stands:**

Go down the table; the **first** row that matches decides:

| What the notes and folder show | Go to |
|---|---|
| No notes | Step 1 |
| The five copies exist, the run document (where `HOW_TO_RUN.md` exists) or the deployment guide does not, and this version is Final or has a review round logged — a pack made before them | Only in a new version (§A New Version) — otherwise say so and stop |
| Items not all settled | Step 3 |
| §9 *Deployment facts* empty | Step 3b |
| The developer's answers not yet recorded | Step 4 |
| No copies in `artifacts/` | Step 5 |
| Copies exist, the deployment guide does not (this version is still Draft, with no review round) | Step 5, item 3 — no new version needed |
| Copies exist, the last review round FINDINGS (or no round yet) | Step 6 — fix what the round found, then the checks |
| The last round for this version PASS, or accepted as it is | Step 7 |
| Three rounds for this version, the last not PASS, not accepted | Stop: tell the developer the two ways forward (§Review, item 2) |

**Then check the build** — from `state.py get`, once:

1. **Phases.** Any phase not `done` → the pack can only be **Draft**. Say why in the report.
2. **A final review.** Phases carry no date, so the test is: every phase `done`, and a
   `whole-build` entry in `reviews[]` dated later than every entry meaning the code changed or
   was asked to change — every `edits[]` entry, and every `changeLog[]` entry by
   `implement-agent` or with origin `out-of-band` or `developer-prompt`. Leave out a review's own
   entries (`author: review-agent`, origin `review-R-<n>` — they always follow it) and any entry
   whose id §7 of the notes lists as recorded by Stage 6. This is a best guess, never an
   automatic Draft: when it fails, recommend a Stage 5 whole-build review, and ask in Step 4
   whether the existing review still covers the code and whether its findings were dealt with
   (`reviews[]` holds only counts). The developer's yes satisfies it.
3. **Design drift.** A minor edit never touches a contract, but the developer's own fixes
   (`origin: out-of-band`) and fixes made outside a phase can. List each such entry dated after
   the last HLD/LLD Revision History row. If one may touch a contract, the client LLD could
   describe something that did not ship: the pack stays **Draft**, and Step 4 asks the developer
   to rerun Stage 2 first or to confirm the entry changed no contract.

---

## Step 1 — Read in one batch

Read, in **one** step: the five source documents, `HOW_TO_RUN.md`, `PROJECT_CONTEXT.md`,
`INTAKE_RESOLVED.md`, the plan, `BUILD_ASSUMPTIONS_<AppName>.md` and every `REVIEW_*.md` — with
your file tool, several files in one step where it allows (`AGENTS.md §Keeping the Request Count Down`). Reading more in
one call costs nothing extra. Run `docs.py feature show` in the same step where your tools allow.

## Step 2 — Scan (a script, not you)

```text
python <stage folder>/tools/clientdocs.py scan
```

It writes or refreshes `CLIENT_PACK_NOTES.md` (Output 3):

- **§3 Raw markers** — every `OPEN QUESTION:` and `ASSUMPTION:` in the five documents,
  `HOW_TO_RUN.md` and the other sources of Inputs item 3, and every `TODO` in the five documents
  and `HOW_TO_RUN.md` (elsewhere the word is just a word), including those in block quotes and table cells and those that run over several
  lines; a marker in a code block is a quoted sample and is skipped. A marker in a table row
  carries the rest of the row, so each row is its own marker. Each has an id, `H-<6 hex>`, from
  its file and its text.
- **§4 Reference hits** — every harness reference in the five documents and `HOW_TO_RUN.md`,
  by kind: harness files,
  tools and words, harness IDs (intake questions, phases, tasks, edits, reviews), and links that
  leave the pack. Your worklist for Step 5.
- It keeps what you and the reviewer wrote — §1 Pack, §2 Versions, §5 Items, §6 Exemptions,
  §7 Developer answers, §8 Review log, §9 Deployment facts — and §10 Sources, which `copy`
  writes. On a rerun it prints how many markers no item settles
  yet, and names any item whose hit no longer exists (a source reran and reworded it): re-link
  that item to its new hit, or retire it.

## Step 3 — Settle each item

Group the raw markers into **items** in §5 — one row per distinct open question or assumed fact. The
same question asked in several documents in different words is one item listing all its hits; a
marker that asks two things is two items. Give each an id `I-1`, `I-2`, … and fill every column.

**About** — what the item concerns:

- **`legacy`** — how the old app behaves ("runtime uses the machine locale", "the seed rows are
  POC data"). The new code cannot confirm or change these. Evidence: the legacy source, or the
  developer's word. In the client pack they stay statements about the **requirements baseline**
  (the requirements documents describe what the old system did, which the new one was built to).
- **`new`** — the new system: design questions, behaviour choices, technology picks. Evidence:
  human decisions, the design, the delivered code.
- **`deploy`** — a gap in what deploying needs, raised in Step 3b. It names no raw marker.

**Outcome** — exactly one. Sources rank as `AGENTS.md §Authority when sources conflict` says;
add nothing to that order.

| Outcome | When | What the client's copy says |
|---|---|---|
| **Decided** | A human decided it: a `changeLog[]` entry with `author: developer`; a human-answered row of `INTAKE_RESOLVED.md` or a constraint in `PROJECT_CONTEXT §4`; or the developer's answer in Step 4 | A plain fact in the body; listed under *Decisions made during delivery* |
| **Chosen in design** | The HLD or LLD settled it, and no human decision is on record. Design is agent work, so it is not shown as a decision | A plain fact; listed under *Design choices — please confirm* |
| **Adopted in build** | Nothing upstream settled it; the delivered code does one thing (cite `path:line` in the target repo), or `BUILD_ASSUMPTIONS` records it | What the system does; listed under *Assumptions adopted in the delivered system — please confirm* |
| **Confirmed** | An `ASSUMPTION:` the right evidence shows true (legacy evidence for a `legacy` item, code for a `new` one) | A plain fact |
| **Corrected** | An `ASSUMPTION:` the right evidence shows false | The true statement |
| **Not applicable** | About something dropped from scope (cite the decision that dropped it) | Removed; one line under *Decisions made during delivery* |
| **Still open** | Nothing settles it | Kept, worded as a question for the client, under *Open items*, as `OI-1`, `OI-2`, … |
| **Conflict** | Two sources disagree — a decision says one thing, the code does another | **Nothing.** It goes to the developer first (Step 4) and blocks the pack until settled |

**Rules:**

1. **No outcome without evidence.** The *Evidence* column cites where the answer came from:
   `path:line`, a change-log id, a document section, or `developer, <date>`. Everything except
   *Still open* needs it. If you cannot point at it, the item is *Still open*.
2. **Check every `new` item that is Decided or Chosen in design against the code.** That is the
   only way to find a Conflict. Batch the searches — one call covers many items.
3. **The build's own assumptions.** `BUILD_ASSUMPTIONS_<AppName>.md` rows are raw markers like any
   other. A build older than that file reported its assumptions only in chat: rule 2 catches
   those that touched a documented question, and Step 4 asks the developer for the rest.
4. **Client wording** — the sentence the client will read, in their terms: no harness word, ID or
   file. Write it for every item except a Conflict.

Write §5 in one edit.

## Step 3b — Work out the deployment facts

*On a first run, and again in every new version.* Before the one question list, fill §9
*Deployment facts* of the notes — one row per fact the deployment guide will state: *Fact ·
Value · Source*. Take each from Inputs item 7, and check it against the code (batched searches).
A fact a constraint's *Hand-over* obligation calls for cites that constraint too (`C2`). Check
every *Hand-over* obligation here, before the question list: one that names no document, or that
the record cannot satisfy (the guide must name a vault nothing records), becomes a `deploy` item —
never guessed.
Where it comes from:

| The guide's section | Its facts come from |
|---|---|
| What you are deploying; environments | `PROJECT_CONTEXT §3`, `context.deployment` (target, units, release model, topology), HLD §9 |
| Before you start | the build files (runtime versions), `context.deployment`, the account each connection uses (`PROJECT_CONTEXT §3`) |
| Configuration; secrets | the LLD §7 table, checked against the configuration files and the code that reads them; how secrets reach the app from `configDelivery` |
| Build the release | the build files; the pipeline, where `context.cicd` names one |
| Database | `PROJECT_CONTEXT §3` *Data migration*, the data-reuse constraint in §4, LLD §2 |
| Deploy; check it worked | `context.deployment` topology (same or separate origins: CORS, the API base URL), HLD §9, the sign-in for each role and the group or claim behind it (`PROJECT_CONTEXT §3`) |
| Logging and monitoring | HLD §6 |
| Go-live, rollback, the old system | `PROJECT_CONTEXT §3`, HLD §9 |

Three outcomes:

1. **The record and the code agree** — a row with its source. Nothing else.
2. **A gap** — a value deploying needs that nothing records (the production API address, the
   vault's name, an environment's host) — a **`deploy` item** in §5: *Still open*, no hit,
   client wording as a question for the client. Asked in Step 4.
3. **Configuration drift** — an **application key** (one this application defines, or whose value
   differs per environment) the code reads that the LLD §7 table lacks, an LLD §7 key the code
   never reads, or one whose shape, default or secret flag differs from the code. It is design
   drift, asked in Step 4 item 2, and settled **only by fixing whichever side is wrong** — the
   developer decides: the design (rerun Stage 2) or the code (an ordinary change, `AGENTS.md §How
   a mid-flight change is handled`) — then a new pack version. Their confirmation alone is not
   enough: the client's LLD and the guide would contradict each other. Until then, Draft.
   Framework settings nobody deploying must touch (a default port, a log level, ORM switches)
   are not drift; the guide may list them, marked `framework`.

## Step 4 — Ask once, then record

Stop **once**, with one numbered list (`AGENTS.md §Writing for the Developer`), in this order:

1. each **Conflict** — what disagrees with what, both sides cited, and the choice to make;
2. **design drift** (Step 0, item 3) and **configuration drift** (Step 3b), if any — for
   configuration drift, which side is wrong: the design or the code;
3. whether the final review still covers the code and its findings were dealt with (Step 0,
   item 2), if the rule did not settle it;
4. **any assumptions from the build's hand-offs they remember** — only when the build predates
   `BUILD_ASSUMPTIONS_<AppName>.md` or its rows look thin;
5. each **Still open** item they may be able to answer now — the `deploy` items first;
6. the cover values, on the first run: who the pack is **prepared for** (the client's name) and
   **prepared by**.

When they answer:

- record each answer in §7 *Developer answers*, dated, and update the items it settles
  (evidence `developer, <date>`); set the cover values with
  `clientdocs.py set "prepared-for=<client>" "prepared-by=<team>"`;
- **offer** — once, for the answers that matter to later work — to record them the ordinary way
  too: `state.py add changeLog author=developer origin=developer-prompt "summary=<answer>"`
  (`AGENTS.md §Recording What the Developer Tells You`). Only on their yes; then write each id
  the tool prints into §7 as `changeLog <id> (recorded by Stage 6)`. Otherwise nothing in the
  pipeline sees the notes — say so when you offer;
- an answer that means the code or design must change is an ordinary change
  (`AGENTS.md §How a mid-flight change is handled`), not Stage 6 work: the pack stays **Draft**
  until it is done and a new version is made.

## Step 5 — Write the documents

1. **Copy:** `python <stage folder>/tools/clientdocs.py copy`. It writes the five copies — and the
   run document, from `HOW_TO_RUN.md` — with the mechanical rewrites — a link to another of the five documents points at its copy; a link to
   anything else outside the pack becomes plain text (`DatabaseHelper.cs:48` stays as a citation,
   without the link); the `## 0. Revision History` section becomes a **Document control** table;
   the LLD's §3c *Reference Adoption* is dropped; the front matter (version, status, cover
   values) is added. It records each source's hash in §10, for a new version.
   It refuses to overwrite copies that exist: from now on change them **only** with `replace`
   — and `set`, which writes the front matter and the Document control table.
2. **Edit:** for each copy, put every judgement edit in **one** values file of exact `old` → `new`
   pairs (`AGENTS.md §Keeping the Request Count Down`; each `old` found exactly once) and run
   `python <stage folder>/tools/clientdocs.py replace BRD "@.harness-tmp/brd.json"` — `FRD`,
   `TRD`, `HLD`, `LLD`, `RUN` likewise. A values file stays within the per-step write cap; a large
   document takes two or three. All or none of a file's pairs apply.
3. **Skeleton:** `python <stage folder>/tools/clientdocs.py skeleton` writes the deployment guide
   once (below); fill it through `replace DEPLOY`. It warns of an LLD §7 key whose *Secret?* is
   neither yes nor no — it puts that key in section 4; move it to section 5 if it is secret.

**What to rewrite, document by document:**

| Where | Rule |
|---|---|
| Every §4 reference hit | Say what it means in the client's words, or drop it. "See `PROJECT_CONTEXT §4`, C2" → "the existing Active Directory sign-in must be used (constraint C2)". "Q20b", "phase P-4", "Stage 1" go |
| Constraint IDs `C1`…`Cn` | Keep them, and add one `## Constraints` section at the end of the BRD — a table: ID, the constraint, what it requires — from `PROJECT_CONTEXT §4`, stated as requirements, never as per-stage "obligations" |
| Raw markers and `TODO`s | Replaced by the item's client wording, in place. Where the body asked the question, it now states the fact, or points at the open item ("see open item OI-2") |
| The open-questions section of each document — BRD §7, FRD §7 and TRD §10 *Assumptions & Open Questions*, HLD §11 *Open Questions & Assumptions* (the numbers the Stage 1 and Stage 2 templates give; an older document may number them otherwise — go by the title) | Rebuilt from the items whose hits it held, as up to four sub-sections, each only when non-empty: *Decisions made during delivery* · *Design choices — please confirm* · *Assumptions adopted in the delivered system — please confirm* · *Open items*. A document with no such section (the LLD) states its items in place, and lists any to confirm under the HLD's |
| Requirements documents (BRD, FRD, TRD) | Under the title, one sentence saying the document records the **requirements baseline** — what the legacy system did, which the new system was built to — and, before the open-questions section, a short `## How the delivered system meets this baseline` (three to six sentences, citing HLD/LLD sections). Nothing else about the old system changes |
| HLD §8 *Constraint Satisfaction*, TRD wording on constraints | How each constraint is honoured — never "obligations" or "per-stage" |
| HLD §9 *Delivery, Cutover & Coexistence* | Without "per `PROJECT_CONTEXT §3`", repository-layout or release-model terms |
| LLD §3a *Source Tree* | Keep the tree; a `context.repo.*` name becomes the real path |
| LLD §3b *Design Language* | Drop any column or line that names the reference sample |
| Traceability (HLD §10, LLD §8) | Keep — it maps requirement IDs to design |
| Requirement and design IDs (`BR-7`, `FR-12`, `SEC-2`, the HLD's own `DD-n`) | **Unchanged** — they are defined inside the pack |
| Phase, task, edit and review IDs | Dropped |
| Anything saying the copy was generated | Nowhere in a copy, not even an HTML comment — the client receives the `.md` files too |
| Each constraint's *Hand-over* obligation (`PROJECT_CONTEXT §4`) | Honoured as written, in whichever document it names (`AGENTS.md §Constraints`); record in §9 where each is met (*Fact* `C2 Hand-over`, *Value* the document and section, *Source* `PROJECT_CONTEXT §4`), so the reviewer can check every one. One Step 3b could not satisfy is a `deploy` item, answered in Step 4. A constraint with no *Hand-over* obligation does not change this stage |

**Exemptions.** Client text can look like a harness reference: "legal obligation", a business
process's "Stage 2", "Q4 results", a client risk register's `R-1`. Add each to §6 — the copy's
file name, the **exact** text, and why it is client text. It excuses only that text in that file,
and must name **one** use: "Q4 results", never a bare `Q4`. An ID the copy drops on purpose (a
*Not applicable* item's) is exempted the same way, as is a dev-only seed value the secret check
flags in the run document. The reviewer checks every exemption.

**The run document** (`<AppName>_RUN_LOCALLY.md`):

| Where | Rule |
|---|---|
| Harness references | Removed or reworded, as for the five |
| "How to test by hand" | A short smoke test a newcomer can follow — what to open, what to try, what they should see — from the feature checks; never a pointer to a ledger |
| Paths and names from the developer's machine | A `<placeholder>` in the command (`<your Maven folder>\bin\mvn.cmd`), and one line **outside** the code block saying what goes there |
| Every command block | Kept — a `<placeholder>` may stand in for part of a line, nothing else changes, no line is added; `check` compares them with `HOW_TO_RUN.md` |
| Dev seed accounts | Kept only when they are seed data **in the code**, labelled *local development only*, with an exemption |

**The deployment guide** (`<AppName>_DEPLOYMENT_GUIDE.md`). The skeleton has a Document control
table and twelve sections, each with a `*To be written: …*` line: 1 What you are deploying ·
2 Environments · 3 Before you start · 4 Configuration · 5 Secrets · 6 Build the release ·
7 Database · 8 Deploy · 9 Check it worked · 10 Logging and monitoring · 11 Go-live, rollback and
the old system · 12 Open items. Section 4 (*Key · What it does · Required? · Set at · Default ·
Example · Differs per environment? · Where it is set*) and section 5 (*Name · What it is for ·
How it reaches the application · Who provides it · Format*) come filled with the LLD §7 keys —
a secret key in section 5.
Fill every section from §9 of the notes:

- **state facts, not sources** — the guide reads as one document; the sources stay in §9;
- **secrets by name only** — what each is for, how it reaches the app, who provides it; never a
  value, never a realistic example (`<db-password>`, not `P@ssw0rd`); section 5 has no value column;
- **framework settings** listed in section 4 say `framework` under *Required?*;
- **verified or labelled** — a step you ran (a build command) is plain; every other deployment
  step reads *Not verified in a deployed environment*;
- **section 12, *Open items*,** lists the pack's open items that affect deployment, by their
  `OI-n` — and is where each `deploy` item's open item is stated, as its home document.

## Step 6 — Check, then ask for a review

Run both checks **in one chained command** for your shell (`AGENTS.md §Keeping the Request
Count Down`) — the exit status and the output say which one failed:

```text
python <stage folder>/tools/clientdocs.py check
python <stage folder>/tools/md2pdf.py --check <documents>/artifacts/<AppName>_BRD.md <documents>/artifacts/<AppName>_FRD.md <documents>/artifacts/<AppName>_TRD.md <documents>/artifacts/<AppName>_HLD.md <documents>/artifacts/<AppName>_LLD.md
```

`check` fails, file by line, on: a harness reference no exemption covers; a raw marker; a link
that leaves the pack or names a missing heading; an ID or numbered heading of a source missing
from its copy (content lost); a marker no item settles; an item that names a hit that is gone, or
has a bad *About* or *Outcome*, no evidence, or no client wording; any Conflict; a stale or
too-broad exemption; front matter that is missing or disagrees with §1. A raw marker inside a
code block is a quoted sample and is not reported. `md2pdf.py --check`
reports diagrams that fail to draw, images that do not load, and tables too wide for the page
(split the table, or set `orientation: landscape` in that copy's front matter).

`check` also fails on: what looks like a secret value, in any document — a literal assigned to
a password, secret, token, API key, client secret or private key name, a private-key block, a JWT,
an AWS key, a table cell that is wholly a long random-looking string (an environment-variable
name, `${…}`, a `<placeholder>`, a GUID and a path pass); a code block of `HOW_TO_RUN.md` missing
from the run document; in the guide, a `*To be written` left, a value column in its section 5, or a key
the LLD §7 table and its sections 4 and 5 do not share (both ways; with no §7 table, `check` says the keys were not
checked — compare them by hand). `md2pdf.py --check` is for the five only.

**Run the run document's changed commands** — once, after its edits: only the command blocks
your edits changed (Stage 4 ran the rest whenever it changed `HOW_TO_RUN.md`), through
`tools/longrun.py` where long. Building and running may write build output in the target repo
(`target/`, `dist/`, `bin/`) — that is allowed; prefer commands that change no tracked file
(`npm ci`, not `npm install`), and report any tracked file a command changed. A command that fails or cannot run here (it needs
the legacy app, a database you cannot reach) **does not stop the document**: label the step
*Not verified: <why>*, finish the document, and report it.

Fix and rerun **both until clean** — check runs are not review rounds. Then hand off: the pack is
ready for review round *n* of 3 for this version (§Review); give the developer the review prompt.
On a **fix run** — after a round with findings — fix every blocker and major the round logged
(minors where cheap), and run both checks again before handing back.

## Step 7 — Final or Draft, then print

The pack is **Final** when all hold: both checks clean; no Conflict; every phase `done`; a
final review current (Step 0, item 2, or the developer's yes); no unsettled design drift; and,
for this version, the last review round PASS or the developer accepted it as it is. Then
`clientdocs.py set status=Final` — which refuses while `check` reports any problem, so the
checks are run once more on the way. Otherwise it stays **Draft** — the PDFs carry a DRAFT
watermark. *Still open* items may remain in a Final pack: they are listed for the client, which
is honest and normal.

Print the five copies, named one by one — never the run document or the deployment guide:

```text
python <stage folder>/tools/md2pdf.py <documents>/artifacts/<AppName>_BRD.md <documents>/artifacts/<AppName>_FRD.md <documents>/artifacts/<AppName>_TRD.md <documents>/artifacts/<AppName>_HLD.md <documents>/artifacts/<AppName>_LLD.md --out <documents>/artifacts/pdf
```

It uses the Chrome or Edge already installed and skips one that will not run headless. Under a
short command time limit run it through `tools/longrun.py` (`AGENTS.md §Keeping the Request Count
Down`). If no browser works, say so: the developer can open each `.html` it saved and print it.

**Report** (`AGENTS.md §Writing for the Developer`):

- what was produced and where; **Final** or **Draft**, and why;
- **What I need from you**, in order: Conflicts; design drift; *Adopted in build* items, then
  *Chosen in design* items — the client will be asked to confirm these, so the developer sees
  them first; then *Still open* items;
- which source documents now say less than the pack — Stage 6 never edits them; rerun Stage 1 or
  Stage 2 if they should match, then make a new version;
- for the run document: each command run and its result, and each step labelled *Not
  verified*; for the guide: the steps labelled *Not verified in a deployed environment*;
- the review rounds used for this version, and their result;
- the files this run wrote, for the developer's commit (you run no git — invariant 6).

---

## Review

*Only on `run stage 6 review`, in a session that wrote nothing of this pack.* You are the
client's first reader and the writer's auditor. **Read-only** on everything except §8 *Review
log* of `CLIENT_PACK_NOTES.md`, which only you write.

1. **Read** this section, the notes, the seven documents, their sources (`HOW_TO_RUN.md` for the
   run document, §9 of the notes for the guide) and the evidence each item and fact cites — in
   as few steps as your tools allow. The seven documents share this version's three rounds.
2. **Count the rounds** for the pack's current version (§1 *version*; §8 headings
   `### Version <v> — Round <n> — …`). If three rounds are logged for this version, **do not
   review.** Reply: three review rounds for version *v* are used up; the remaining findings are in
   the notes; the developer either accepts the pack as it is (§Accepting the Pack As It Is) or
   starts a new version (§A New Version). There is never a fourth round for one version.
3. **Run both checks** (Step 6). Every failure is a **blocker**.
4. **Check every claim:** each *Decided*, *Chosen in design*, *Adopted in build*, *Corrected* and
   *Not applicable* item against its cited evidence — open what it cites. These are the
   statements the client will hold the team to. Spot-check *Confirmed* and *Still open* items.
   Check **every exemption** in §6: is it really client text, and does it name one use? Check
   **every constraint's *Hand-over* obligation** is honoured — one that is not is a blocker.
5. **Read each copy as the client would.** Is anything understandable only to someone who knows
   the harness? Is anything in the source lost or changed in meaning? Is each term explained,
   each ID defined in the pack?
6. **The operational documents, as a capable stranger.** Compare the guide's sections 4 and 5 with
   the configuration files in the code — every application key, every secret, no value. Read the run
   document's steps against the code (you run nothing). Is every *Not verified* label honest, and
   every step one a stranger could follow?
7. **Log the round** — append to §8:

   ```markdown
   ### Version <v> — Round <n> — PASS | FINDINGS
   1. **blocker** — <copy>:<line> — <what is wrong> — <what right looks like>
   ```

   Severities:
   - **blocker** — a check fails; a claim or fact its evidence does not back; a harness reference
     left; a weak exemption; a secret value; a *Hand-over* obligation not honoured;
   - **major** — meaning lost or changed against the source; a passage the client cannot follow;
     a step a stranger could not carry out;
   - **minor** — wording, layout.

   **PASS = no blocker and no major.** Minors are listed and may be fixed.
8. **Report** to the developer: the verdict, the findings in plain words, and the next prompt —
   `run stage 6 — app: <App>` (to fix, or, on PASS, to finish).

A round is a review the reviewer logged; a request refused under item 2 is not a round.

## Accepting the Pack As It Is

*Only on `accept the client pack as it is`.* Allowed only when **all** hold: both checks clean;
no Conflict; **no open finding is a blocker** (in the last round logged for this version); and
the developer has read the open findings — list them back and ask them to confirm. A blocker only
a reviewer can see (a claim its evidence does not back, a weak exemption) stops acceptance too:
it is fixed in a new version. On their yes, append to §8
`### Version <v> — accepted with findings by developer, <date>` and the findings it accepts,
then continue at Step 7. The PDFs carry no mark of it — the client does not need the internal
history.

## A New Version

*Only on `run stage 6 — app: <App>, new version`* — after a source document's stage reran, after
new answers, after a Stage 0 rerun added or changed a constraint's *Hand-over* obligation, or
after the developer fixed something by hand. Only the developer starts one; never
start one to get more review rounds.

1. `clientdocs.py scan` — the notes keep their items; re-link or retire any item it names as
   gone.
2. Settle new and changed items (Step 3), and work out the deployment facts again (Step 3b),
   asking (Step 4) only what is new.
3. `clientdocs.py copy --new-version` — the version goes up by one, a Document control row is
   added, the status returns to Draft, every missing copy is made, and an existing copy is made
   again **only when its source changed** since it was made (or §10 holds no hash for it); an
   unchanged copy keeps its edits. The guide is never made again: `skeleton` writes it if it is
   missing (a pack from before the guide existed), and otherwise it stays as it is.
4. Redo the judgement edits of each copy made again (Step 5) — the client wording in §5 makes
   this quick — bring the guide in line with §9 through `replace`, and apply each *Hand-over*
   obligation added or changed since the last version, in whichever document it names, even
   one whose copy was kept (`PROJECT_CONTEXT.md` is no copy's source, so `copy` does not see
   it change); then Step 6. The round count
   starts again at 1.

---

## Rerunning this Stage

Every writer run starts at Step 0, which picks up from the notes; nothing is redone that the
notes record as done. The copies are never made again except by a new version, and the guide
never at all, so no edit is lost. A rerun's Additional Instructions override this file for that run ("leave the TRD's
section 9 untouched", "the client is Acme Ltd").

---

## Hard Rules

1. **Read-only on the pipeline.** Never edit a source document, `state.json` (but Step 4's
   change-log entries, on the developer's yes), the plan, the feature ledger, `PROJECT_CONTEXT`,
   or the code. Running the run document's commands may write build output in the target repo;
   that is all.
2. **Copy, then replace.** Never write a copy whole, never edit one but through `replace` (and
   `set` for its front matter and Document control table), and never run `copy` over existing
   copies except for a new version. The deployment guide alone starts from `skeleton`, and is
   never made again.
3. **Evidence or open.** No outcome but *Still open* without a citation; never resolve an item by
   guessing.
4. **A Conflict never reaches the client.** It goes to the developer, and the pack cannot pass
   while one remains.
5. **Writer and reviewer are separate sessions.** Never review a pack in the run that wrote it.
6. **At most three review rounds per version.** Never a fourth; never a new version to get one.
7. **Nothing in a copy points back at the harness** — no harness file, tool, stage, intake
   question, phase, task, edit or review ID, no raw marker, no note that it was generated.
8. **A secret is named, never valued** — in every document of the pack (invariant 7).

---

## Definition of Done

**A writer run:**

- [ ] Step 0 placed the run, and the build checks are reported (phases, final review, drift).
- [ ] Every raw marker belongs to an item; every item has *About*, *Outcome*, evidence (unless
      *Still open*) and client wording; every new-system Decided / Chosen-in-design item was
      checked against the code.
- [ ] The developer was asked once, and their answers are recorded in §7 (and in `changeLog[]`
      only on their yes).
- [ ] The copies were made by `copy` and changed only by `replace` and `set`; the guide was made
      by `skeleton` and filled through `replace`.
- [ ] §9 *Deployment facts* holds every fact the guide states, with its source; gaps are `deploy`
      items; configuration drift went to the developer.
- [ ] The run document's changed commands were run; each one that failed or could not run is
      labelled and reported, and the document is finished.
- [ ] Every constraint's *Hand-over* obligation (`PROJECT_CONTEXT §4`) is honoured.
- [ ] `clientdocs.py check` and `md2pdf.py --check` are clean before any review is requested.
- [ ] On finishing: Final or Draft decided by Step 7's rule; the PDFs printed (or the reason they
      could not be).
- [ ] Every message to the developer, including the closing report, follows `AGENTS.md §Writing
      for the Developer`; every item and finding is named in words, not only by its ID.

**A review run:**

- [ ] The round count checked first; never a fourth round for one version.
- [ ] Both checks run; every claim, fact and exemption checked, and every *Hand-over*
      obligation; every copy read as the client, and the two operational documents as a capable
      stranger.
- [ ] The round logged in §8 with severities; PASS only with no blocker and no major.
- [ ] Nothing written but §8.

---

## Additional Instructions

*(The prompt may append run-specific guidance — the client's name, a section to leave as it is,
an item the developer has already settled, the paper size (`--paper letter`), a stylesheet for the
client's look (`--css <file>`), or where to write the PDFs. Treat these as overrides/additions to
the above.)*
