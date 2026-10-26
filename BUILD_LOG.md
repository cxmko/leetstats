# Build log

A running record of what has been built and validated, so work can resume
after an interruption. Newest entries at the bottom.

## 2026-10-26: runtime and vertical slice

- Runtime: Pyodide **314.0.7** (latest stable, 2026-09-14): Python 3.14.2,
  NumPy 2.4.6, pandas 3.0.2, scikit-learn 1.8.0, matplotlib 3.10.8,
  SciPy 1.18.0, statsmodels 0.14.6, LightGBM 4.6.0. Seaborn is not bundled:
  0.13.2 (latest on PyPI) is installed with micropip and works with pandas
  3.0.2 (histplot/boxplot/violinplot/scatterplot/heatmap/catplot/relplot/
  pairplot all smoke-tested inside Pyodide).
- file:// findings (Edge 156 / Chrome 155):
  - `importScripts()` fails inside a `blob:null` worker, and module workers
    from blob URLs never start.
  - Pyodide 314 refuses "classic" workers (it probes `importScripts`).
  - Fix: classic Blob worker, shadow `self.importScripts` with a throwing
    function, then `import()` `pyodide.mjs` dynamically. NumPy + pandas
    are ready about 3 s after boot on a warm cache.
- Pyodide-only finding: its matplotlib build emits a
  `MatplotlibDeprecationWarning` ("x parameter as float") while drawing text.
  The harness now renders plots outside the user-warning capture and ignores
  that message.
- Validation engines: CPython 3.14.2 venv pinned to the versions above
  (`requirements-validate.txt`), and Pyodide under Node 24
  (`tools/run_pyodide.mjs`). The final runs use the Pyodide engine.
- Vertical slice (np-010, pd-036, pl-001, sk-002, st-001, qt-002, ch-002,
  ch-003, bug-003): validated in both engines; browser check in Edge from
  file:// passed 33/34 (the failing check was a test-script bug). Problems
  from 4 sections solved, plot graded, Stop and the 10 s limit work,
  tracebacks show editor line numbers, review mode starts blank, progress
  survives a reload, playground namespace persists, flashcards work.

## 2026-10-26: sections

- numpy: 34 written, all validated (CPython + Pyodide). Fixes along the way:
  a missing flat-days test, a wrong solution that couldn't be distinguished
  by timing (replaced), and a spoiler-check false positive (module paths).
- pandas: 66 written, all validated. Findings: pandas 3 `str` dtype makes
  `.str.contains` return False on missing values without `na=False`
  (explanation updated; tests use object dtype); `select_dtypes(include=object)`
  warns on `str` columns (references use `dtype_exclude='number'`).
- plotting: 23 written, all validated. Harness changes: FacetGrid detection,
  canvas drawn only when tick labels are checked, expected plot structures
  precomputed at build time so Submit doesn't re-run the reference; ignore the
  seaborn 0.13.2 + matplotlib 3.10 `vert` PendingDeprecationWarning and
  Pyodide's `JsProxy.as_object_map` warning (raised by sklearn's KMeans).
- sklearn: 36 written, all validated in Pyodide (Submit <= 1.5 s); several
  CV-heavy problems use 3 folds to stay within the time budget.
- stats: 8, quant: 12, all validated in Pyodide. (CPython on this machine
  can't import statsmodels from the deep scratchpad venv: Windows MAX_PATH.)

- chains: 18 (4 chains), bugs: 12, all validated in Pyodide. Difficulties
  re-graded to 82 Easy / 102 Medium / 27 Hard (39/48/13%).
- Added pd-067 (describe) and pd-068 (as-of forward-fill alignment); hidden
  tests on sklearn's iris, digits and diabetes datasets.
- Flashcards: 62 predict-the-output snippets (outputs captured in Pyodide),
  50 extra recall cards. Playground: 8 prompts, all walkthroughs execute.
- Docs: 279 URLs checked (`build.py --check-links`); pandas 3 moved the
  groupby pages to `pandas.api.typing.*`, fixed.
- App fixes found by browser testing: review list excluded peeked/flagged
  problems that were never run; Python jobs now queue instead of failing
  while busy; dark-mode syntax colours; scroll to the solution on accept.

## 2026-10-26: final verification

- Full `build.py --all` inside Pyodide: 211/211 problems, 62/62 snippets,
  8/8 walkthroughs; slowest Submit 1.3 s.
- Browser (file://): `tools/browser_check.py` 34/34 in Edge and Chrome;
  `tools/browser_extras.py` 26/26 in Edge and Chrome.

| Section | Status |
|---|---|
| numpy | done (34) |
| pandas | done (68) |
| plotting | done (23) |
| sklearn | done (36) |
| stats | done (8) |
| quant | done (12) |
| chains | done (18) |
| bugs | done (12) |
| cards / playground | done (62 + 50 cards, 8 prompts) |

## 2026-10-26: renamed to LeetStats

- App renamed from "DS Drill" to **LeetStats**; logo from `logo/logo.png`.
  `logo/icon-light.png`, `icon-dark.png` (grey lightened for dark mode),
  `favicon.png` and `logo-512.png` (README) are generated from it and the
  icons are embedded in `index.html` as data URIs.
- The localStorage key stays `dsdrill.v1` so existing progress carries over;
  exports are now `leetstats-progress-YYYY-MM-DD.json` (old exports still import).
- Today now draws new problems from every selected section (1 per section by
  default, interleaved); section chips toggle sections.
- Full revalidation in Pyodide: 211/211 problems, 62/62 snippets, 8/8
  walkthroughs. Browser: 34/34 core and 26/26 extras in Edge; also checked
  over an http origin and with iPhone emulation.
