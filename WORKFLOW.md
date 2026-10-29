# Workflow

The steps each stage of this project follows, from opening its branch to its release tag. What
each stage learns, builds and counts as done is set in `scope_and_rationale.md` Section 3; this
file covers how the work is carried out.

The project is built with an AI coding assistant (Claude Code). The owner makes the decisions and
runs every git operation; the assistant explains, proposes, and implements a plan once the owner
confirms it. The assistant's working rules are in [CLAUDE.md](CLAUDE.md), and the coding and
testing standards are in [DEVELOPMENT.md](DEVELOPMENT.md).

## Start a stage

1. **Open the stage branch** from `main`, named as in `scope_and_rationale.md` Section 6 (e.g.
   `stage-2-rules`).
2. **Learn the concepts first.** The stage's key concepts are explained in plain language, from
   the public sources listed in CLAUDE.md ("Personas"), and understanding is checked before any
   code is proposed.
3. **Review the parked notes** for the stage in `docs/backlog.md`.
4. **Plan, then confirm.** The plan states what will be built and which files change. Work starts
   only after the owner confirms it.
5. **Add the stage's dependencies.** Each stage installs only what it needs, when it starts.

## Build

1. **Build only what the stage plan commits to,** as set in `scope_and_rationale.md` (Section 3).
2. **Test alongside the code:** label logic, data validation and every feature function, to the
   standards in DEVELOPMENT.md ("Tests"), which also set the leakage test for time-based features.
3. **Flag assumptions** rather than choosing one silently. Each gets a `docs/decisions.md` entry,
   as does any departure from Section 3.
4. **Park scope creep** in `docs/backlog.md`.
5. **Report only numbers produced by running the code.** A figure that can't be verified is
   marked as such, never filled with a placeholder.
6. **Check documentation** with the documentation checks (`.claude/skills/docs-check/SKILL.md`)
   whenever it changes.
7. **Commit small:** single-purpose Conventional Commits.

## Close a stage

1. **Confirm the stage's "Done when" item is met,** as set in the stage plan in
   `scope_and_rationale.md` (Section 3).
2. **Write the stage report,** `reports/stageN_<name>.md`: what was built, what it found, what it
   doesn't show, and what it means for the next stage.
3. **Update the documents that own each fact** (e.g. `data/README.md`, `docs/decisions.md`) and
   the README's stage table.
4. **Run the documentation checks** across every document.
5. **Run a validator review,** covering the independent validator's remit in CLAUDE.md
   ("Personas"). A fresh-context review (a new session or separate agent that sees only code and
   results) is offered for stronger independence. Findings are fixed or recorded before the stage
   closes.
6. **Complete the pre-merge checklist** in DEVELOPMENT.md ("Before a pull request").
7. **Merge and tag.** The owner merges the stage branch into `main` and tags the release named in
   Section 3 (e.g. `v0.2`). `main` holds verified work only.
