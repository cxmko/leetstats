---
name: add-problems
description: Add new validated practice problems to LeetStats. Usage /add-problems <count> <section> [topic] [difficulty], optionally followed by pasted "Copy my stats for Claude" output to target weak spots. Writes problems in the existing format, validates them with build.py, rebuilds index.html and COVERAGE.md, and reports what was added.
---

# /add-problems

Arguments: `<count> <section> [topic] [difficulty]`

- `section`: one of `numpy`, `pandas`, `plotting`, `sklearn`, `stats`,
  `quant`, `chains`, `bugs` (see `problems/_meta.py`).
- `topic` (optional): a tag from `TAGS[section]`, or a new topic phrase
  (then add a tag that doesn't name a function).
- `difficulty` (optional): `Easy`, `Medium`, `Hard`; otherwise aim for the
  app-wide mix (about 40/45/15).
- If the user pasted stats from the app ("LeetStats stats ... Weakest
  topics ..."), use them to choose topics: favour the weakest topics and
  the bricks behind repeatedly failed/peeked problems, with new bricks (not
  rewordings of existing problems). If the section argument conflicts with
  the stats, follow the arguments.

## Procedure

1. **Read the context first**: `CLAUDE.md` (schema, house style, validation
   rules), `COVERAGE.md` (existing bricks per topic), and the target
   `problems/<section>.py` (format and the last id). Don't duplicate a
   brick already covered: each new problem must drill a different call
   shape or a genuinely different pitfall.
2. **Plan** `count` problems: one brick each, a small realistic framing,
   the exact output contract, at least 3 hidden tests on different data with
   an edge case, 1-2 realistic wrong solutions (required for Medium/Hard), and
   hints (Hint 1 names the function, Hint 2 shows the call shape).
   Reuse the generators in `runtime/datasets.py` (`D.*`); add a generator
   only if really needed (new function or backward-compatible parameter,
   never a behaviour change).
3. **Write** the dicts at the end of `problems/<section>.py` with new
   permanent ids (next free numbers; never reuse or renumber). Add any new
   tag to `problems/_meta.py`. Insert the ids into `problems/path.txt`
   where they belong (easy to hard within the section).
4. **Validate and rebuild**:
   ```bash
   python build.py --only <new ids>        # fast iteration
   python build.py                         # final: validates anything changed, rebuilds index.html + COVERAGE.md
   ```
   Use the Pyodide engine when available (Node + `tools/node_modules`; pass
   `--node <path>` if needed), otherwise `--engine cpython --python <pinned venv python>`.
5. **Fix or drop failures**: read every `FAIL` line.
   - A wrong solution passes: add a test that distinguishes it, or remove
     it if it is actually a correct alternative.
   - The reference emits a warning: switch to the non-deprecated API.
   - Spoiler checks: reword the statement (what, not which function) or
     the tag.
   - Too slow: smaller data or fewer CV folds.
   Re-run until the report shows no failures for the new ids. If one can't
   be fixed, delete it and say so.
6. **Check** that `COVERAGE.md` lists the new bricks and `index.html` was
   rewritten (the build prints its size). Add a dated line to `BUILD_LOG.md`.
7. **Report**: a table of the added problems (id, title, difficulty, tags,
   brick from Hint 1), anything dropped and why, the new section and total
   counts from the build report, and a reminder that existing progress is
   kept (ids are permanent; new problems show a "NEW" badge).

## Quality bar (same as the existing problems)

- Statement: task plus exact output (type, shape, columns and order, index,
  sort order and ties, dtype/rounding when relevant). Tests never fail on
  anything unspecified; set `compare=` flags and tolerances accordingly.
- Current, idiomatic, vectorized code for pandas 3.0 / NumPy 2.4 /
  scikit-learn 1.8; valid on pandas 2.2 where possible. Mention
  differences in the explanation.
- Explanation: 1-3 sentences (why, pitfall, alternative).
- Plot problems: return Figure/Axes/FacetGrid as stated; check structure
  only (`plot=dict(returns=..., checks=[...])`).
- Submit within about 2 s: small data; no `n_jobs`; no `fetch_*`.
