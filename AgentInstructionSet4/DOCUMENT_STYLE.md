# Document Style: How Every Pipeline Document Is Written

Every stage in this set writes Markdown a human has to read and act on. This file is the
single source for **how that writing is done**. Stage files point here; none of them restate
these rules.

Read this before you write your first line, and run the §Self-Check before you finish.

**Applies to** every document a stage produces: `PROJECT_CONTEXT.md`, the three requirements
documents, the HLD and LLD, `PLAN_<AppName>.md`, `HOW_TO_TEST_<phaseId>.md`, and review
reports.

**Does not apply to** `state.json`, which is machine state, or to code and commit messages.

---

## 1. What Brevity May Never Remove

Read this section first. The rest of this file tells you to cut. This section tells you what
you must never cut, no matter how much it looks like clutter.

These are load-bearing. Later stages and the Review stage read them mechanically:

1. **Evidence citations.** Every `path:line` stays. A requirement without its source is an
   assertion, and the Review stage cannot check it.
2. **IDs and cross-references.** `BR-3`, `FR-7.2`, `NFR-4`, `C1`, `DD-2`, `P-3.T-1`. These are
   how the whole pipeline joins up.
3. **Traceability sections and tables.** Never summarize a traceability matrix.
4. **Literal strings, reproduced exactly.** Error messages, labels, column names, config keys,
   file paths. Copy them character for character, including spacing, casing, and punctuation.
   Never paraphrase a literal, never "tidy" its wording, never correct its spelling.
5. **`ASSUMPTION:` and `OPEN QUESTION:` markers** and the text after them.
6. **Any detail a constraint's obligation in `PROJECT_CONTEXT.md §4` tells you to capture.**
7. **Ordering, where order is behavior.** If the legacy app validates before it queries, the
   sequence is the requirement. Keep the numbered steps.

> **The test:** would a later stage or the Review stage behave differently without this text?
> If yes, it stays — however long the document gets. Brevity is about *how you say things*,
> never about *what you leave out*. A short document that dropped a citation is a worse
> document, not a tighter one.

---

## 2. Plain English

Write for a competent colleague who does not know this codebase. Not for a specification
committee, and not for another model.

**Sentences and paragraphs**

- One idea per sentence. Aim under 25 words; hard stop at 40.
- Paragraphs of at most four sentences. Prefer two.
- Cut every clause that does not change the reader's understanding.
- Use active voice and name the actor: "The search screen rejects an empty filter", not
  "empty filters are rejected".
- Present tense for what is; `shall` only inside a requirement statement (§4).
- At most one em-dash aside per paragraph. Nested asides belong in separate sentences.

**Words**

- Say the plain word. `use` not `utilize`; `to` not `in order to`; `about` not `with respect
  to`; `so` not `thereby`; `helps` not `facilitates`.
- Delete filler outright: *it is important to note that*, *it should be noted*, *as
  mentioned above*, *in essence*, *basically*, *simply*, *of course*, *clearly*, *robust*,
  *seamless*, *comprehensive*, *leverage*, *best-in-class*.
- Delete intensifiers that add nothing: *very*, *quite*, *extremely*, *significantly*,
  *fundamentally*, *critically* — unless you can say by how much.
- **One term for one thing, everywhere.** If it is a "filter" in §2, it is not a "criterion"
  in §3 or a "search parameter" in §5. Rotating synonyms reads as three concepts, and a
  later stage will build three. Pick the term the legacy app or the target stack uses and
  keep it for the whole pipeline.
- Define each domain term and each abbreviation once, at first use, then use it bare.
- Never invent emphasis. Bold carries meaning here; if a third of a page is bold, none of it
  is.

**What you are not writing**

- No preamble that restates the heading you just wrote.
- No summary paragraph that repeats the table below it.
- No "this section describes…" openers. Start with the content.
- No closing paragraph that recaps the section.

---

## 3. Structure Before Prose

Prose expands to fill the space. Structure does not. Reach for structure first.

| When the content is | Write it as |
|---|---|
| Several items with the same fields | A table, one row per item |
| A sequence where order matters | A numbered list |
| A set of independent points | A bullet list |
| A rule with a trigger and a response | An EARS statement (§4) |
| A shape, a flow, or a relationship | A Mermaid diagram with a caption |
| Reasoning behind a decision | Prose — this is what prose is for |

Rules:

- **Say each fact once**, in the document and section where it belongs. Everywhere else,
  reference it by ID. Duplicated prose is how two copies of a rule drift apart.
- **A table beats a paragraph** whenever the content has repeating fields.
- **Do not narrate a table.** The table is the content; a caption of one line is enough.
- **Diagrams supplement, never replace.** Every fact in a diagram also exists in text, since
  a diagram is not searchable or citable.
- **Headings are navigation.** Keep the section structure the stage file specifies. Do not
  add depth beyond three levels.

---

## 4. Requirement Statements Use EARS

Every **normative statement** — a statement of what the system must do — is written in EARS
(Easy Approach to Requirements Syntax). Everything else is ordinary prose.

### 4.1 The five patterns

Use the simplest one that fits.

| Pattern | Shape | Use when |
|---|---|---|
| **Ubiquitous** | `The <system> shall <response>.` | Always true, no trigger or precondition |
| **Event-driven** | `When <trigger>, the <system> shall <response>.` | A specific event starts the behavior |
| **State-driven** | `While <state>, the <system> shall <response>.` | The behavior holds for as long as a state holds |
| **Unwanted behavior** | `If <condition>, then the <system> shall <response>.` | Errors, invalid input, failures, rejections |
| **Optional feature** | `Where <feature is present>, the <system> shall <response>.` | The behavior exists only in some configurations |

A **complex** statement combines a state and a trigger, in this order:
`While <state>, when <trigger>, the <system> shall <response>.`
Use it only when both genuinely apply. Two simple statements beat one complex one.

`<system>` is the named system or component — `EmployeeSearch`, `the login screen`, `the
export service`. Not "the application" everywhere, and not "it".

Where you name the system directly, drop the article: write `EmployeeSearch shall …`, not
`The EmployeeSearch shall …`. Both `The <system> shall` and `<System> shall` are valid
ubiquitous statements. Never put a comma before `shall` in one — a comma there means you have
opened a condition and not closed it.

### 4.2 Rules every EARS statement follows

1. **One statement, one sentence, one `shall`.** No `and also`, no semicolon splices. To
   state what must *not* happen alongside the behavior, use a participle rather than a second
   `shall`: "shall display `…` **without attempting** a credential lookup", not "shall display
   `…` and shall not attempt a credential lookup".
2. **One behavior per statement.** If the response has an "and" joining two independent
   behaviors, write two statements. A statement must be testable as a single pass or fail.
3. **`shall` only.** Never `should`, `may`, `might`, `will`, `can`, `must`, or `is expected
   to` in a normative statement. If it is genuinely optional, it is not a requirement — say
   so in prose, or record it as an `OPEN QUESTION:`.
4. **Every statement carries its own ID** — `FR-3.2`, `BR-11`, `NFR-4` — and at least one
   `path:line` citation.
5. **No implementation.** Say what the system does, not how it is coded. Literal strings,
   field names, and column names are *what*, so they stay.
6. **Measurable where it claims a measure.** "shall respond quickly" is not a requirement.
   Give the number, or mark it `OPEN QUESTION:`.

### 4.3 Voice: these documents specify the replacement

Stage 1 reads the legacy application, but the documents it writes are the **specification for
the system being built**. Stages 2, 3, and 4 build from them, and Stage 5 judges against them.
So write requirements in the `shall` voice, as obligations on the new system, and cite the
legacy source as the evidence for each one.

Under a **strict parity** stance (`PROJECT_CONTEXT.md §1`), the legacy behavior *is* the
requirement, so this is a direct translation and nothing is lost.

Where **improvements are permitted**, record the current behavior as the requirement first,
then note the proposed improvement separately, marked as a proposal. Never blend the two into
one statement.

Descriptive present tense stays correct in the sections that describe the legacy system as
built — Technical Requirements §1 (Current Architecture), §2 (Data Layer), §3 (Integrations),
§5, §6. Those sections record what exists, not what must be built.

### 4.4 Where EARS applies

| Document / section | EARS? |
|---|---|
| Business Requirements §5 Business Rules | **Yes** — mostly ubiquitous and unwanted-behavior |
| Business Requirements §6 Roles & Permissions | **Yes** — state-driven or ubiquitous |
| Business Requirements §1–§4, §7 | No — purpose, objectives, scope, user classes, questions |
| Functional Requirements §2 Detailed Features | **Yes** — this is the core of it |
| Functional Requirements §6 Validation Rules | **Yes** — usually unwanted-behavior |
| Functional Requirements §1, §3, §4, §5 | Context prose and tables; the **rules inside them** are EARS |
| Technical Requirements §7 Non-Functional | **Yes**, where measurable |
| Technical Requirements §1–§6, §8–§10 | No — these describe the system as built |
| LLD §4 Validation Rules | **Yes** |
| HLD, plan, review reports | No — decisions, sequencing, and findings are prose |

Forcing EARS onto a purpose statement or an architecture description produces worse writing,
not more rigor. Where the table says no, write plain prose under §2 and §3 of this file.

### 4.5 Feature layout: context, then statements

Keep the explanatory context. Add the EARS statements as the numbered, normative leaves under
it. The context tells a human what is going on; the statements are what gets built and tested.

```markdown
### FR-1 — Sign in

**Purpose.** Verify a submitted username and password and admit the user to the directory.
Implements BR-1, BR-2, BR-3.

**Trigger.** The user activates `Sign In`, or presses Enter in the username or password
field (`Views/LoginForm.cs:28`, `:30-37`). Both routes run the same procedure.

**Inputs.** Username (free text). Password (free text, masked on entry).

**Requirements.**

- **FR-1.1** When the user submits the sign-in form, EmployeeSearch shall trim leading and
  trailing whitespace from the username. (`Views/LoginForm.cs:41`)
- **FR-1.2** When the user submits the sign-in form, EmployeeSearch shall use the password
  exactly as entered, without trimming. (`Views/LoginForm.cs:42`)
- **FR-1.3** If the trimmed username is empty or the password is empty or whitespace-only,
  then EmployeeSearch shall display `Please enter both username and password.` without
  attempting a credential lookup. (`Views/LoginForm.cs:44-48`)
- **FR-1.4** If credential verification fails for any reason, then EmployeeSearch shall
  display `Invalid username or password. Please try again.` (`Views/LoginForm.cs:50-56`)
- **FR-1.5** If credential verification fails, then EmployeeSearch shall clear the password
  field. (`Views/LoginForm.cs:50-56`)
- **FR-1.6** If credential verification fails, then EmployeeSearch shall return focus to the
  password field, leaving the username field populated. (`Views/LoginForm.cs:50-56`)
- **FR-1.7** When credential verification succeeds, EmployeeSearch shall record the trimmed
  username as the signed-in principal. (`Views/LoginForm.cs:58-60`)
- **FR-1.8** When credential verification succeeds, EmployeeSearch shall open the search
  screen. (`Program.cs:22-28`)

**Sequence.** FR-1.1 → FR-1.2 → FR-1.3 → lookup → FR-1.4/FR-1.5/FR-1.6 or FR-1.7/FR-1.8. The
order is behavior: no lookup happens when FR-1.3 rejects the input.

FR-1.5 and FR-1.6 are separate statements on purpose. Clearing the field and moving focus are
two behaviors, and a legacy app that does one but not the other is a real and common defect —
one statement covering both would read as satisfied when only half of it works.
```

Note what this preserves: every citation, every literal string, the ordering, and the IDs.
It is not shorter because it says less. It is shorter because each statement says one thing.

### 4.6 Worked rewrites

**Vague → testable**

- Before: *The system should handle invalid searches appropriately and give the user helpful
  feedback.*
- After: **FR-3.4** If a search returns no rows, then EmployeeSearch shall display `No
  employees matched your search.` in the status line. (`Views/SearchForm.cs:112`)

**Two behaviors in one → split**

- Before: *When the user clicks Export, the system shall write a CSV file and shall display
  the row count in the status line.*
- After:
  - **FR-7.1** When the user activates `Export`, EmployeeSearch shall write the current
    result set to a CSV file. (`Views/SearchForm.cs:203`)
  - **FR-7.2** When the export completes, EmployeeSearch shall display the exported row
    count in the status line. (`Views/SearchForm.cs:219`)

**Narrative → EARS, with the literal kept**

- Before: *If the user leaves the username blank, an error is shown telling them to enter
  both fields, and no lookup takes place.*
- After: **FR-1.3** If the trimmed username is empty, then EmployeeSearch shall display
  `Please enter both username and password.` without attempting a credential lookup.
  (`Views/LoginForm.cs:44-48`)

**Implementation leaking in → behavior only**

- Before: *The system shall call `EmployeeRepository.SearchAsync()` with a LIKE clause on the
  surname column.*
- After: **FR-3.1** When the user submits a surname filter, EmployeeSearch shall return every
  employee whose surname contains the filter text, case-insensitively.
  (`Data/EmployeeRepository.cs:64`)

**Unmeasurable NFR → measured, or marked open**

- Before: *The system shall be fast.*
- After: **NFR-2** When a search filter is submitted, EmployeeSearch shall return results
  within the 30-second command timeout configured today. (`App.config:12`)
  `OPEN QUESTION:` is 30s the intended budget, or just an unreviewed default?

---

## 5. Self-Check Before You Finish

Run this over what you wrote. It is the same list the Review stage uses.

- [ ] Every normative statement in an EARS section matches one of the five patterns, in one
      sentence, with exactly one `shall`.
- [ ] No `should` / `may` / `might` / `will` / `can` inside a normative statement.
- [ ] Every normative statement has an ID and at least one `path:line` citation.
- [ ] Every literal string is reproduced exactly, unaltered.
- [ ] No section duplicates a fact that lives in another section or document; it references
      the ID instead.
- [ ] Repeating-field content is in tables, not paragraphs.
- [ ] No filler phrases, no section-opening preamble, no closing recap.
- [ ] One term per concept across the whole document.
- [ ] Every `ASSUMPTION:` and `OPEN QUESTION:` is still present and still marked.
- [ ] Read one page aloud. If a sentence needs a second pass to parse, rewrite it.
