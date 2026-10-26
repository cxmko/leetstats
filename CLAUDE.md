# CLAUDE.md: LeetStats

A static, single-file practice app (`index.html`) for NumPy / pandas / plotting /
scikit-learn / statistics / quant-research "bricks". Problems are authored in
Python files, validated by `build.py`, and embedded into the page. Python runs
in the browser through Pyodide 314.0.7 (pinned) inside a Web Worker.

Read this file before adding or editing problems (DEVELOPMENT.md has the user-facing build docs). It is meant to be enough on
its own.

## Golden rules

1. **Problem IDs are permanent** (`np-001`, `pd-047`, ...). Never renumber or
   reuse one: users' progress, flashcard history and review schedules are
   keyed by id. To retire a problem, delete it (its progress is then ignored).
   New problems take the next free number of their section prefix.
2. **Every problem must pass validation** (below) before it ships. Failing
   problems are automatically left out of `index.html`.
3. **Target exactly the Pyodide 314.0.7 stack**: Python 3.14.2, NumPy 2.4.6,
   pandas 3.0.2, scikit-learn 1.8.0, matplotlib 3.10.8, SciPy 1.18.0,
   statsmodels 0.14.6, LightGBM 4.6.0, seaborn 0.13.2 (micropip). No pyarrow.
   Idiomatic current APIs only: no deprecated calls, no chained assignment,
   no `n_jobs`, no `fetch_*` datasets (no downloads).
4. **Keep data small** (around 5k rows or fewer, except a deliberate
   large-input test): a Submit (reference plus candidate on all tests) must
   take 3 s or less in Pyodide.

## Files

| Path | Role |
|---|---|
| `problems/_meta.py` | `SECTIONS` (key, id prefix, title, packages to preload), `TAGS` vocabulary per section, `CHAINS`, allowed doc domains |
| `problems/<section>.py` | `SECTION = "<key>"` and `PROBLEMS = [dict(...), ...]` |
| `problems/path.txt` | learning-path order (one id per line; `#` comments). Insert new ids where they belong. |
| `content/cards.py` | `RECALL_EXTRA` (front/back syntax cards) and `PREDICT` (snippets whose output is captured at build time) |
| `content/playground.py` | `PROMPTS`: open-ended prompts with step-by-step walkthroughs (each step's code is executed at build time) |
| `runtime/datasets.py` | shared seeded generators (`D.<name>` in problem code) |
| `runtime/harness.py` | grading: `evaluate`, `compare`, `plot_info`, `preview`, `Test`, `REF`, playground runner. Runs in the browser AND at build time. |
| `runtime/validate.py` | build-time validation of problems, snippets, walkthroughs |
| `build.py` | static checks, then the engine run (cached by content hash), then `index.html` + `COVERAGE.md` |
| `src/` | `template.html`, `app.css`, `app.js` (UI), `worker.js` (Pyodide worker) |
| `tools/run_pyodide.mjs` | runs `runtime/validate.py` inside Pyodide under Node |
| `.build/cache.json` | validation cache (safe to delete; forces revalidation) |

## Problem schema

```python
dict(
    id="pd-067",                       # permanent; prefix must match the section
    title="Revenue per weekday",       # task-like; also the recall-card front
    difficulty="Medium",               # Easy | Medium | Hard
    tags=["aggregation", "dates & times"],   # from TAGS[section]; first = Stats topic
    signature="def solve(orders: pd.DataFrame) -> pd.Series:",
    statement="""...markdown...""",
    setup="""
EXAMPLE = lambda: {"orders": D.orders(seed=0, n=20)}
""",
    tests="""
TESTS = [
    lambda: {"orders": D.orders(seed=1, n=200)},
    lambda: {"orders": D.orders(seed=2, n=3000)},
    Test(lambda: {"orders": D.orders(seed=3, n=1)}, "single order"),
]
""",
    compare=dict(check_dtype=True),     # optional
    hint1="`s.dt.day_name()` then `groupby(...).sum()`.",
    hint2="orders.groupby(orders['order_date'].dt.day_name())['revenue'].sum()",
    solution="""
def solve(orders):
    return orders.groupby(orders["order_date"].dt.day_name())["revenue"].sum()
""",
    explanation="""...1-3 lines: why, pitfall, alternative...""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.Series.dt.day_name.html"],
    wrong_solutions=[dict(code="""...""", why="mean instead of sum")],
    # optional: starter=, plot=dict(returns=, checks=[...]), mutation_check=True,
    #           chain="churn", step=6, allow_in_statement=["default_rng"], recall="..."
)
```

### How grading works (`runtime/harness.py`)

- `setup` then `tests` are executed in a namespace with `np`, `pd`, `D`
  (datasets), `Test`, `REF`, `fail`, `compare`, `same_partition`,
  `allclose_up_to_sign`, `plot_info`. They must define `EXAMPLE` (Run) and
  `TESTS` (Submit), lists of **factories**, which are called anew for every
  use so in-place mutation can't leak between runs.
- For each test: build inputs, run the user's `solve(**inputs)`, build fresh
  inputs, run the reference, then grade:
  - `check(got, exp, inputs)` if `tests` defines it (return None or a message,
    or call `fail("msg")`); otherwise
  - `compare(got, exp, **problem["compare"])`, which reports the first
    difference (type, shape, columns, index, dtype, then values). Defaults:
    `rtol=1e-5`, `atol=1e-8`, `check_dtype=False`, column order checked,
    index checked, `check_names=False`. Datetime units and str/object are
    treated as the same dtype family.
  - plot problems: structural checks from `plot["checks"]` against the
    reference structure (precomputed at build time and embedded, so Submit
    doesn't redraw the reference). Available keys:
    figure level `type`, `n_axes`, `colorbar`, `suptitle`, `shared_x`,
    `shared_y`, `twin`; axes level `title`, `xlabel`, `ylabel`, `xscale`,
    `yscale`, `lines`, `line_points`, `flat_lines`, `vertical_lines`, `bars`,
    `pathpatches`, `containers`, `points`, `scatter_groups`, `polys`,
    `meshes`, `images`, `texts`, `legend`, `legend_labels`, `xticklabels`,
    `yticklabels`, `xdate`, `xformatter`, `yformatter`. Never check colors
    or styles.
- `Test(factory, "name", timed=True)` also fails if the user is more than 15x
  slower than the reference (and > 0.5 s): use it with a large input when a
  Python loop would otherwise pass. Make sure the loop version really is that
  slow (validate a loop wrong solution).
- `mutation_check=True` fails a solution that modifies its inputs.
- Chains: a step's inputs come from the previous step's **reference** via
  `REF("ch-00k", **inputs)` inside `setup` factories.
- Randomness: if many outputs are valid (RNG-based resampling, cluster ids,
  PCA signs), write a property-based `check` (see `np-016`, `st-004`,
  `ch-017`, `np-033`).

### Validation rules (enforced by `build.py`)

Static: required fields; id format; tags in the vocabulary and not naming a
hinted function (constructors like `Series` are ignored); for non-sklearn
sections the statement's code spans must not contain functions named in
Hint 1 (use `allow_in_statement` for names the spec genuinely needs);
signature params == solution params; docs on official domains; Medium/Hard
have >= 1 wrong solution; plot problems have `plot=`; chain problems have
`chain`/`step`; fix-the-bug problems have a `starter`. Warnings (not errors):
solution > 8 lines (15 for Hard), explanation > 600 chars.

Dynamic (engine): `EXAMPLE` keys == signature params; >= 3 tests; the
reference passes all tests **twice** with **no warnings**; it passes the
example; the starter fails; every wrong solution fails; Submit time within the
budget (3 s Pyodide / 1.5 s CPython); example previews and target images are
generated.

## House style

- **Statements** frame a small realistic task ("each customer's share of
  their region's revenue"), not API trivia. State the exact output: type,
  shape, column names and order, index (kept, reset or named), sort order and
  tie rule, dtype or rounding when it matters (then set
  `compare=dict(check_dtype=True)`). Tests may only fail on what the
  statement specifies. Say *what* to compute, never *which function*
  (sklearn and chain statements may name the estimator when using it is the
  point).
- **Hint 1** names the function/method, in backticks. **Hint 2** is the bare
  call shape with key arguments (code, no prose), since it becomes the
  Bricks cheat sheet and the recall card.
- **Explanation**: 1-3 sentences: why this idiom, the common pitfall, the
  alternative (transform vs agg, fit on train only...). Mention pandas 2 vs 3
  differences when relevant (copy-on-write, `str` dtype, `observed=True`,
  `stack` keeping NaN, `'ME'`/`'h'` aliases).
- **Tests**: >= 3 hidden tests on data different from the example (other
  seeds, sizes, values), including an edge case (NaN, ties, empty group,
  single row, duplicate keys, boundary values). Name edge-case tests:
  `Test(..., "ties at the cut-off")`.
- **Wrong solutions**: realistic mistakes (fit on all data, `shift(-1)`,
  summing simple returns, `transform` vs `agg`, wrong axis, missing
  `keepdims`, unsorted ties...). If one passes, add a test that catches it,
  or drop it if it is actually correct.
- Difficulty mix target across the app: about 40% Easy, 45% Medium, 15% Hard.
- Reference solutions: vectorized, current API, 1-8 lines.

## Data generators (`runtime/datasets.py`, `D.*` in problems)

All are deterministic for `(seed, size)` and use `np.random.default_rng`.
**Never change existing behaviour** (problems and expected outputs depend on
it); add new parameters with backward-compatible defaults, or new functions.

| Generator | Columns / output |
|---|---|
| `customers(seed, n=40)` | customer_id (C001..), name, region, segment, signup_date, age |
| `orders(seed, n=200, n_customers=40, unknown_share=0.03)` | order_id, customer_id, order_date, region, category, quantity, unit_price, revenue (sorted by order_id/date; some unknown customers) |
| `orders_raw(seed, n, n_customers, dup_share)` | text dates, `$1,234.50` prices, 'unknown' quantities, region spelling variants, duplicates, discount with NaN |
| `orders_csv(seed, n, sep, decimal, na)` | orders_raw as CSV text |
| `hr(seed, n=150, missing_share)` | employee_id, department, level, city, remote, hire_date, years_experience, performance, salary (NaN), bonus (NaN) |
| `hr_raw(seed, n, dup_share)` | salary as '85,000'/'n/a', department variants, DD/MM/YYYY dates, repeated employees with an `updated` timestamp |
| `churn(seed, n=600, messy=False)` | customer_id, tenure, contract, internet, payment_method, monthly_charges, total_charges, support_calls, senior, region, churned (~27%); messy: text total_charges with blanks, NaN charges, contract variants, duplicates |
| `prices(seed, n_days=250, n_tickers=20, start, gaps=False)` | long panel date, ticker, close, volume (one-factor returns) |
| `prices_wide(...)` | close prices, date x ticker |
| `market_returns(seed, n_days, beta, alpha, idio)` | (stock, market) daily return Series |
| `factor_panel(seed, n_dates=36, n_tickers=60, ic=0.08)` | monthly date, ticker, momentum, value, size, fwd_ret (weak momentum signal, NaN, fat tails) |
| `sensors(seed, n_sensors=3, days=2, freq='15min', ...)` | timestamp, sensor_id, temperature, humidity with gaps, NaN, spikes |
| `ab_test(seed, n=2000, lift, base_rate)` | user_id, group A/B, device, converted, revenue, time_on_site |
| `to_csv_text(df, **kw)` | CSV string |

sklearn's bundled `load_*` (iris, wine, breast_cancer, diabetes, digits) and
`make_*` generators are fine. `fetch_*` is not (it downloads).

## Adding problems: exact steps

1. Read `COVERAGE.md` (bricks per section and topic) and skim the section
   file so you don't duplicate an existing brick.
2. Pick ids: the next free numbers for the prefix (check with
   `grep -o 'id="pd-[0-9]*"' problems/pandas.py | sort | tail -1`).
3. Append the dicts to `problems/<section>.py` (keep the existing format).
   New tags must be added to `TAGS[section]` in `problems/_meta.py` and must
   not name a function.
4. Insert the ids into `problems/path.txt` at the right place (easy to hard
   within the section; chain steps in order).
5. Validate and rebuild:
   - Pyodide engine (preferred; needs Node 18+ and `cd tools && npm install` once):
     `python build.py`. On the author's machine, Node may live in the session
     scratchpad, so pass `--node <path>` if `node` isn't on PATH.
   - Or CPython pinned env: `python build.py --engine cpython --python <venv python>`.
   - `--only id1,id2` to iterate on a few; plain `python build.py`
     validates only new/changed problems. Changing anything in `runtime/`
     invalidates the cache, so everything revalidates (about 4 min in Pyodide).
6. Read the report: fix or drop every `FAIL`/`DROPPED` entry (wrong solution
   passes → add a catching test; reference warns → use the current API; too
   slow → shrink data or folds). Re-run until clean.
7. `COVERAGE.md` and `index.html` are regenerated by the build. Update
   `BUILD_LOG.md` with a short dated entry.
8. Optionally run the browser smoke test (see BUILD_LOG.md) or open
   `index.html` and solve the new problem once.

Flashcards: add `RECALL_EXTRA` / `PREDICT` entries in `content/cards.py`
(new ids `rx-NNN` / `po-NNN`). Never write predict-card outputs by hand: the
build runs the snippet. Playground prompts: `content/playground.py`; each
step's code must run without errors or warnings in the preloaded namespace.

## Gotchas learned building this

- pandas 3: default `str` dtype (`.str.contains` returns False on missing
  values, `select_dtypes(include=object)` warns; use
  `dtype_exclude='number'`), copy-on-write (chained assignment never
  works), `groupby(observed=True)` default, `stack()` keeps NaN, datetimes
  default to `datetime64[us]`, offset aliases `'ME'`, `'h'`, `'min'`.
- scikit-learn 1.8: `root_mean_squared_error` (the `squared=` arg is gone),
  `OneHotEncoder(sparse_output=...)`, `boxplot(tick_labels=...)` in matplotlib 3.10.
- LightGBM 4: early stopping only through `callbacks=[lgb.early_stopping(n)]`.
- Pyodide emits internal warnings that the harness ignores
  (`IGNORED_WARNINGS`): matplotlib's float-coordinate deprecation, seaborn's
  `vert` PendingDeprecationWarning, `JsProxy.as_object_map`.
- file:// constraints: the worker is a classic Blob worker with
  `importScripts` shadowed so `pyodide.mjs` loads via dynamic `import()`
  (module workers from blob URLs don't start on file:// pages).
- Windows + bash heredocs: Python snippets that contain `\n` inside strings
  get mangled; use the Edit tool for such changes.
