# Workflow

How each stage is carried out. What each stage learns, builds and counts as done is set in the
stage plan in `scope_and_rationale.md`.

The owner makes the decisions and runs every git operation. The AI coding assistant (Claude Code)
explains, proposes and implements plans under the owner's direction, following
[CLAUDE.md](CLAUDE.md). Coding and testing standards are in [DEVELOPMENT.md](DEVELOPMENT.md).

## Start a stage

1. **Open the stage branch** from `main`, named as in `scope_and_rationale.md` Section 6 (e.g.
   `stage-2-rules`).
2. **Learn the concepts first,** in plain language from the public sources in CLAUDE.md
   ("Personas"), and check understanding before any code is proposed.
3. **Review the parked notes** for the stage in `docs/backlog.md`.
4. **Plan, review, then confirm.** The plan states what will be built and which files change. The
   financial crime practitioner reviews it for realism and typology coverage, and work starts once
   the owner confirms.
5. **Add only the dependencies the stage needs.**

Findings from every review, here and at the close of the stage, are fixed once the owner approves,
drafted as a `docs/decisions.md` entry, or parked in `docs/backlog.md`.

## Build

1. **Build only what the stage plan in `scope_and_rationale.md` commits to.**
2. **Test alongside the code:** label logic, data validation and every feature function, to the
   standards in DEVELOPMENT.md ("Tests"), which also set the leakage test for time-based features.
3. **Flag assumptions and departures from the stage plan,** each with a `docs/decisions.md` entry.
4. **Park scope creep** in `docs/backlog.md`.
5. **Report only numbers produced by running the code;** mark anything unverified as such.
6. **Run the documentation checks** (`.claude/skills/docs-check/SKILL.md`) whenever documentation
   changes.

## Close a stage

1. **Confirm the "Done when" item** in the stage plan in `scope_and_rationale.md` is met.
2. **Write the stage report,** `reports/stageN_<name>.md`: an executive summary for a
   non-technical reader, then what was built, what it found, what it doesn't show and what it
   means for the next stage.
3. **Update the documents that own each fact** (e.g. `data/README.md`, `docs/decisions.md`) and
   the README's stage table.
4. **Run the documentation checks** across every document.
5. **Run the practitioner review, then the validator review last,** each covering its remit in
   CLAUDE.md ("Personas"). Either can run in a fresh context for stronger independence.
6. **Complete the pre-merge checklist** in DEVELOPMENT.md ("Before a pull request").
7. **Merge and tag.** The owner merges the stage branch into `main` and tags the release named in
   the stage plan (e.g. `v0.2`).
