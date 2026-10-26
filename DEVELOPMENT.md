# LeetStats: development guide

<img src="logo/logo-512.png" alt="LeetStats logo" width="180">

A LeetCode-style practice app for data-science fluency: NumPy, pandas,
matplotlib/seaborn, scikit-learn, statistics and quant research. It's built
from many short, single-concept problems ("bricks") that you drill until the
syntax is automatic, plus open-ended prompts where you assemble them yourself.

**Open `index.html` by double-clicking it.** There's no server and nothing to
install. The only network use is loading Pyodide (Python compiled to
WebAssembly) and its packages from the jsDelivr CDN, plus seaborn from PyPI
and the editor (CodeMirror 5) from cdnjs. Flashcards, Bricks and Stats work
offline once the page is open.

Tested from `file://` in Microsoft Edge and Google Chrome on Windows 11.

## What's inside

| | |
|---|---|
| Problems | 211 validated problems in 8 sections (see `COVERAGE.md`) |
| Runtime | Pyodide 314.0.7 in a Web Worker: Python 3.14.2, NumPy 2.4.6, pandas 3.0.2, scikit-learn 1.8.0, matplotlib 3.10.8, SciPy 1.18.0, statsmodels 0.14.6, LightGBM 4.6.0, seaborn 0.13.2 (via micropip) |
| Views | Problems, Today, Review, Flashcards, Playground, Mock interview, Bricks (cheat sheet), Stats |

- **Problems**: statement, worked example (input tables with shapes and
  dtypes, expected output, target figure for plots), a stopwatch, Run (on
  the example) and Submit (hidden tests). After a failure you get the first
  failing test's input, expected vs got, and what differs first. Hint 1 names
  the function, Hint 2 shows the call shape, and the solution unlocks after a
  failed submit or "give up". Viewing it puts the problem into review.
- **Review**: spaced repetition. Failed, peeked and flagged problems come
  back, and solved ones return after about 1, 3, 7, 21 and 60 days. In review
  the editor starts from the blank starter.
- **Today**: due reviews, then new problems drawn from every section you
  select (default: 1 per section, interleaved: NumPy, pandas, plotting,
  scikit-learn, stats, quant, chains, fix-the-bug), a daily streak and a
  30-day history chart. Toggle sections and the per-section count on the
  Today page.
- **Flashcards**: recall cards (one per problem, plus 50 extras) and 62
  predict-the-output cards whose answers were produced by running the code.
  They use the same scheduler (Again / Hard / Good / Easy, keys 1-4).
- **Playground**: an ungraded editor with every dataset preloaded and a
  persistent namespace, plus 8 open-ended interview prompts with reference
  walkthroughs.
- **Mock**: one prompt, 45 minutes, no hints. Afterwards you score yourself
  on a 7-point rubric and see the walkthrough. Attempts are saved.
- **Stats**: per-topic accuracy, median time to solve, peek rate, reviews
  due, "drill weakest topic", and **Copy my stats for Claude**.

Keyboard: `Ctrl/Cmd+Enter` runs, `Ctrl/Cmd+Shift+Enter` submits, `Alt+N`
goes to the next problem (or just `N` after an accepted submit), and
`Ctrl/Cmd+/` toggles a comment. The `⋯` menu has export/import, the shortcut
list and "copy stats".

Progress lives in this browser's `localStorage` (key `dsdrill.v1`, kept from the app's earlier name so progress carries over). Use
**Export** to back it up or move it to another browser. Everything is keyed
by permanent problem IDs, so rebuilding the app with new problems never loses
history.

## Project layout

```
index.html                 generated app: open this
build.py                   validate problems, then generate index.html + COVERAGE.md
COVERAGE.md                generated: every section / topic / brick with problem ids
BUILD_LOG.md               build history and findings
CLAUDE.md                  instructions for adding problems with Claude Code
problems/
  _meta.py                 sections, topic-tag vocabulary, chain names
  numpy.py, pandas.py, plotting.py, sklearn.py, stats.py, quant.py, chains.py, bugs.py
  path.txt                 learning-path order (separate from ids)
content/
  cards.py                 extra recall cards + predict-the-output snippets
  playground.py            open-ended prompts with walkthroughs
runtime/
  datasets.py              shared seeded data generators
  harness.py               grading/comparison/preview code (runs in the browser AND at build time)
  validate.py              build-time validation runner
src/
  template.html, app.css, app.js, worker.js
tools/
  run_pyodide.mjs, package.json   validation inside Pyodide under Node
  browser_check.py, browser_extras.py   Playwright smoke tests (file://, Edge/Chrome)
requirements-validate.txt  CPython environment pinned to Pyodide's versions
.claude/skills/add-problems/SKILL.md   /add-problems for Claude Code
```

## Problem schema

One `dict(...)` per problem in `problems/<section>.py`:

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | Permanent id `<prefix>-NNN` (`np`, `pd`, `pl`, `sk`, `st`, `qt`, `ch`, `bug`). Never reused or renumbered. |
| `title` | yes | Short task-like title, also the front of its recall flashcard. |
| `difficulty` | yes | `Easy`, `Medium` or `Hard`. |
| `tags` | yes | 1-3 topic tags from `problems/_meta.py`; the first is the topic used in Stats. Tags never name the function. |
| `statement` | yes | Markdown: the task and the exact output (type, shape, columns and order, index, sort order, dtype/rounding when they matter). Says *what*, not *which function*. |
| `signature` | yes | `def solve(...) -> ...:` |
| `setup` | yes | Python that defines `EXAMPLE` (a zero-arg function returning the `solve` kwargs) and helpers. Uses `D.<generator>`, `np`, `pd`, `REF(...)`. |
| `tests` | yes | Python that defines `TESTS`: at least 3 factories (or `Test(factory, name, timed=False)`) on different data than the example, including an edge case. Optional `check(got, exp, inputs)` for custom grading. |
| `hint1` | yes | Markdown naming the function/method. |
| `hint2` | yes | The call shape (code), also shown on the Bricks page and the recall card. |
| `solution` | yes | Reference solution (1-8 lines; up to ~15 for Hard). |
| `explanation` | yes | 1-3 lines: why this idiom, the pitfall, the alternative. |
| `docs` | yes | Official API-reference URLs. |
| `wrong_solutions` | Medium/Hard | Realistic mistakes; each must fail. Validation only, stripped from the app. |
| `starter` | no | Defaults to the signature plus `pass`. For fix-the-bug problems it is the buggy code. |
| `compare` | no | Comparison options: `rtol`, `atol`, `check_dtype`, `check_like`, `check_names`, `check_index`, `ignore_index`, `sort_rows`, `ordered`, `check_exact`. |
| `plot` | plotting | `dict(returns="Axes"/"Figure"/"FacetGrid", checks=[...])`: structural checks such as `lines`, `bars`, `points`, `title`, `xlabel`, `xscale`, `n_axes`, `colorbar`, `legend`... |
| `mutation_check` | no | Fail if `solve` modifies its inputs. |
| `chain`, `step` | chains | Chain key and step number; steps get previous outputs via `REF("ch-NNN", ...)`. |
| `allow_in_statement` | no | Function names the statement may mention (e.g. an RNG it must specify). |
| `target_image` | generated | Rendered from the reference for plot problems. |

## Building and validating

```bash
python build.py                 # validate new/changed problems only, then rebuild index.html
python build.py --all           # revalidate everything
python build.py --only pd-047   # (re)validate specific ids
python build.py --no-validate   # rebuild the page from cached results
python build.py --engine pyodide|cpython   # default: pyodide if Node + tools/node_modules exist
```

Validation rules: the reference passes every test **twice** with no
warnings, within the time budget (Submit <= 3 s in Pyodide); the blank
starter fails; every wrong solution fails; there are at least 3 hidden tests.
Failing problems are left out of the page and listed in the build report and
in `COVERAGE.md`.

**Validation engines.**

- *Pyodide (recommended, the exact browser runtime)*: install Node 18+, run
  `cd tools && npm install` once, then build normally. It downloads packages
  from the CDN on first use.
- *CPython*: `uv venv --python 3.14 .venv && uv pip install -r requirements-validate.txt`,
  then `python build.py --engine cpython --python .venv/Scripts/python.exe`.
  Don't install pyarrow (Pyodide's pandas runs without it). On Windows, a very
  deep folder path can break the statsmodels import (MAX_PATH); use the
  Pyodide engine or a shorter path.

Requirements for `build.py` itself: just Python 3.10+.

## Adding problems

See `CLAUDE.md` (written so a future Claude session can add problems from it
alone) or, in Claude Code, run:

```
/add-problems 5 pandas "time series" Medium
```

Paste the output of **Copy my stats for Claude** after the command to target
your weak spots.

## Known limitations

- The first Pyodide load downloads about 30 MB (cached by the browser
  afterwards). NumPy and pandas are ready after a few seconds; the rest loads
  in the background, as the status pill shows.
- WebAssembly has no threads: never set `n_jobs`, and big models are slow.
- Runs are limited to 10 s (Playground 60 s). Stop restarts the interpreter,
  which also resets the Playground namespace.
- Progress is per browser. Export it if you clear site data.
