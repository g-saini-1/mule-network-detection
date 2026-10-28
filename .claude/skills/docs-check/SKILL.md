---
name: docs-check
description: Documentation quality checks for this repository. Use whenever documentation changes (README, data/README.md, docs/, reports/, CLAUDE.md, docstrings) and as part of the validator review at the end of every stage.
---

# Documentation checks

## Scope

- **After a documentation change:** check the changed files, every file they link to, and every
  file that links to them.
- **At the end of a stage:** check every document, as part of the validator review.

Report the findings and wait for confirmation before fixing them.

## Method

Run the mechanical checks (links, paths, style, private details, placeholders) with `grep` until
`make docs-check` exists (planned in `docs/backlog.md`). Review the rest by reading.

## Checks

1. **No duplication:** each fact is stated once, in the document that owns it (`CLAUDE.md`,
   "Where information lives"), and other documents link to it. A summary may repeat a headline
   figure, but not its detail or reasoning.
2. **Accurate:** every number matches its source (run output, `data/README.md` or the code),
   every claim about code matches the code, and nothing unverified is stated.
3. **Consistent:** the same fact has the same number and meaning everywhere; links, section
   names, rule numbers (e.g. R1 to R7) and table numbers resolve; superseded decisions are never
   described as current.
4. **Complete:** each closed stage's "Learn", "Build" and "Done when" items in
   `scope_and_rationale.md` are covered by its report, and every current decision in
   `docs/decisions.md` is reflected in the documents it affects.
5. **Claims within the evidence:** nothing claims more than the stage shows, and external-facing
   pages (README, stage reports) state that the data is synthetic.
6. **Departures from scope logged:** anything done differently from `scope_and_rationale.md` has
   a `docs/decisions.md` entry.
7. **Docs match the repository:** commands, `make` targets, file paths, function and column names
   in docs, `CLAUDE.md` and `.claude/settings.json` exist as written.
8. **Current state is current:** status lines, "next" pointers and the README's stage table match
   the actual state of the work.
9. **Safe to publish:** committed files hold no personal email addresses, local machine paths or
   credentials; the only credential reference is the `~/.kaggle/access_token` location.
10. **Cross-references after moves:** whenever content moves within or across documents, re-check
    table numbers, figure numbers, file paths and "see above/below" pointers.
11. **House style:** the parent `CLAUDE.md` writing and formatting rules (e.g. no em-dashes, no
    "include", British spelling, sentence-case headings, "Table N." captions), and no placeholder
    text.
