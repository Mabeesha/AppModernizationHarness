# CLAUDE.md

Project-wide instructions for agents working in this repository.

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
