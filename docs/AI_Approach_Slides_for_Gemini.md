# Slide Spec — AI-Assisted Modernization Approach

> **Instructions for Gemini:** Build a set of presentation slides (Google Slides / PPTX) from
> the spec below. These slides will be **inserted into a larger existing modernization POC deck**,
> so keep the styling clean and neutral (I will restyle to match the master template). One
> `## Slide N` block = one slide. Use the **Title** as the slide title, render **Content** as the
> body (respect the bullet indentation), draw the **Diagram** as simple boxes-and-arrows shapes,
> and put **Speaker notes** in the notes pane. Do not invent extra slides.

---

## Slide 1 — Context: how the coding agent is guided

**Title:** AI-Assisted Modernization: Guiding the Coding Agent
**Subtitle:** Rebuilding the legacy .NET application on Angular + Spring Boot

**Content:**
- The modernization is executed by an **AI coding agent**, steered by a structured **"instruction set"** rather than free-form prompting.
- An instruction set = **staged, document-driven prompts** that carry the agent from legacy code → requirements → design → plan → working software.
- Each stage produces a **reviewable artifact**, so a human validates the work before the next stage begins.
- **Two generations evolved during the POC:**
  - **Set 2** — the linear pipeline used on the client-delivered POC.
  - **Set 3** — the refined, iterative model built from lessons learned.

**Side panel (box titled "Fixed constraints across every stage"):**
- Reuse the existing database as-is — no schema change, no data migration.
- Mirror the legacy app's authentication (real AD, or an auth seam + stub).
- Backend Java follows the Google Java Style Guide, enforced in the build.

**Speaker notes:** Set the frame before comparing the two generations. The key idea is that we don't just "ask an AI to rewrite the app" — we drive it through disciplined, reviewable stages, under three fixed program-wide constraints. Everything that follows is about how the *implementation* stage evolved.

---

## Slide 2 — Generation 1 (Set 2): the waterfall pipeline

**Title:** Generation 1 — Set 2: Linear (Waterfall) Pipeline
**Subtitle:** The approach used on the client-delivered POC

**Diagram (single left-to-right flow, arrows between each, no return path):**
`Requirements Extraction` → `Design (HLD / LLD)` → `Planning` → `Implementation (one large step)`
- Style the first three boxes in the primary/neutral color; style **Implementation** in a warning/red tone to signal it's the problem area.
- Caption under the flow: *"Single forward pass — no return path, no intermediate build to test."*

**Content (callout box titled "Why it proved impractical", red/warning styling):**
- Implementation is **one big step** — the whole application is generated before anything can be run.
- **No checkpoints:** AI drift, misread requirements, and integration errors surface only at the very end.
- A late-discovered problem means **large, expensive rework** — there is no cheap point to course-correct.
- Human review happens **once, on a finished blob**, instead of continuously — the classic waterfall risk, amplified by generative AI.

**Speaker notes:** This is what we actually ran on the client POC. It works as a concept, but generating the whole implementation in one pass means we only find out what the AI got wrong at the very end — exactly the failure mode waterfall has for human teams, made worse because AI output can drift silently. That lesson drove Set 3.

---

## Slide 3 — Generation 2 (Set 3): iterative implementation

**Title:** Generation 2 — Set 3: Iterative Implementation
**Subtitle:** Same planning stages — but implementation becomes a controlled loop

**Diagram:**
- Top row (left-to-right, arrows between): `Requirements` → `Design (HLD / LLD)` → `Planning (phases P-1 … P-N)` → `Phase Implementation`
- Style **Phase Implementation** in a distinct (teal/green) color.
- Below "Phase Implementation," draw a **loop / circular arrow** labeled **"Iterate, one phase per run"** containing the cycle:
  `Build phase` → `Agent self-tests` → `Human accepts ✓` → `next phase` → (loops back to Build).

**Content (callout box titled "Why it works", positive/green styling):**
- Each phase ends in **something runnable and testable** — the plan is sliced into small, verifiable increments.
- A **human acceptance gate** sits between phases: the agent **cannot advance** until a person accepts — errors are caught early, not at the end.
- A **change log is the loop's memory** — every run reconciles feedback before it builds, keeping the human in control throughout.

**Speaker notes:** The upfront stages are unchanged — requirements, design, and planning still happen once. The change is that implementation is no longer one step; it's a loop of small phases. After each phase the agent stops, self-tests, and hands off to a human who must explicitly accept before the next phase starts. This gives us continuous validation and a clean rollback point at every phase boundary.

---

## Slide 4 — Why the shift, and what's next

**Title:** Why Iteration Won — and the Next Step

**Left column (heading "From waterfall to iteration"):**
- Generative AI output **cannot be trusted end-to-end** — it needs validation checkpoints, which a single-pass pipeline never provides.
- Slicing implementation into **accepted phases** catches behavioral drift early and keeps a human in the decision loop.
- It mirrors modern **agile / spec-driven practice** instead of waterfall — the same reason waterfall was abandoned for human teams.
- Net effect: **lower rework risk, continuous confidence**, and a clean rollback point at every phase boundary.

**Right column (heading "Future work: close the design loop"):**

*Mini diagram:* `Design` → `Plan` → `Implementation`, with:
- a solid loop between **Plan ↔ Implementation** labeled *"Today: iterate here"*, and
- a **dashed feedback arrow from Implementation back to Design** (highlight/accent color) labeled *"New: feedback path Implementation → Design → re-Plan."*

*Bullets under the diagram:*
- Today the loop spans **Plan → Implementation**; the design is fixed once approved.
- Next: when a mid-build change **alters the design**, route it back to the **Design stage**, re-plan the affected phases, then resume — **without restarting the pipeline**.
- Enables **larger course-corrections** to be absorbed safely and traceably.

**Speaker notes:** Two takeaways. First, why we changed: AI codegen needs checkpoints, and iteration gives us that while keeping humans in control — it's just good agile practice applied to an AI agent. Second, where we're going: right now only implementation iterates against a fixed design. The next evolution is a feedback path that reaches back into the design stage, so a genuine design change mid-build can be absorbed cleanly instead of forcing a restart.

---

### Optional condensed version
If space in the master deck is tight, Slides 2 and 3 can be merged into a single **"Set 2 vs Set 3"** before/after slide (waterfall flow on the left, iterative loop on the right), reducing the insert to 3 slides total.
