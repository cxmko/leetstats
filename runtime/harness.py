"""LeetStats harness: runs code against a problem, compares outputs and
renders previews. The same file runs in the browser worker (Pyodide) and in
build-time validation (CPython or Pyodide under Node), so problems are graded
identically in both places.

Entry points:
    run_job(job: dict) -> dict      # used by the browser worker
    evaluate(prob, code, ...)       # used by run_job and by validate.py
"""
import ast
import base64
import contextlib
import io
import math
import os
import sys
import time
import traceback
import warnings

os.environ.setdefault("MPLBACKEND", "Agg")

import numpy as np
import pandas as pd

import datasets as D

pd.set_option("display.width", 120)
pd.set_option("display.max_columns", 30)

USER_FILE = "<solution>"
SOLUTIONS = {}          # problem id -> reference solution code (used by REF)
SLOW_FACTOR = 15.0      # timed tests fail when user time > max(SLOW_MIN, SLOW_FACTOR * ref)
SLOW_MIN = 0.5
MAX_STDOUT = 20000
# Warnings raised inside library internals that user code cannot avoid
# (Pyodide's matplotlib build passes floats to its Agg text renderer).
IGNORED_WARNINGS = [r"The [xy] parameter as float was deprecated",
                    r"vert: bool will be deprecated",   # seaborn 0.13.2 + matplotlib 3.10 boxplot
                    r"JsProxy.as_object_map\(\) is deprecated"]   # Pyodide internals (sklearn threadpool probe)


# ---------------------------------------------------------------------------
# Problem definition helpers (available inside `setup` and `tests` code)
# ---------------------------------------------------------------------------
class Test:
    """A hidden test: `make` builds fresh inputs (a dict of solve() kwargs).

    timed=True marks a large-input test: it also fails when the solution is
    more than SLOW_FACTOR times slower than the reference (and > SLOW_MIN s).
    """

    def __init__(self, make, name=None, timed=False):
        self.make, self.name, self.timed = make, name, timed


def _as_test(t):
    return t if isinstance(t, Test) else Test(t)


class CheckFailed(Exception):
    pass


def fail(msg):
    """Call from a custom check() to report a failure."""
    raise CheckFailed(msg)


def same_partition(a, b):
    """True if label arrays a and b define the same clustering (any label
    permutation)."""
    a, b = np.asarray(a).ravel(), np.asarray(b).ravel()
    if a.shape != b.shape:
        return False
    pairs = set(zip(a.tolist(), b.tolist()))
    return len(pairs) == len(set(a.tolist())) == len(set(b.tolist()))


def allclose_up_to_sign(a, b, axis=0, rtol=1e-5, atol=1e-6):
    """Compare arrays allowing each column (axis=0) or row (axis=1) to flip
    sign, as PCA/SVD components may."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if a.shape != b.shape:
        return False
    if a.ndim == 1:
        return np.allclose(a, b, rtol, atol) or np.allclose(a, -b, rtol, atol)
    if axis == 1:
        a, b = a.T, b.T
    return all(np.allclose(a[:, j], b[:, j], rtol, atol) or np.allclose(a[:, j], -b[:, j], rtol, atol)
               for j in range(a.shape[1]))


_REF_CACHE = {}


def REF(problem_id, **inputs):
    """Run another problem's reference solution (used by chain steps so each
    step receives the reference output of the previous one)."""
    fn = _REF_CACHE.get(problem_id)
    if fn is None:
        fn = _REF_CACHE[problem_id] = compile_function(SOLUTIONS[problem_id], f"<ref {problem_id}>")
    return fn(**inputs)


def setup_namespace():
    return {"np": np, "pd": pd, "D": D, "Test": Test, "REF": REF, "fail": fail,
            "compare": compare, "same_partition": same_partition,
            "allclose_up_to_sign": allclose_up_to_sign, "plot_info": plot_info,
            "__name__": "problem_setup"}


def load_problem(prob):
    ns = setup_namespace()
    exec(compile(prob.get("setup") or "", f"<setup {prob['id']}>", "exec"), ns)
    exec(compile(prob.get("tests") or "", f"<tests {prob['id']}>", "exec"), ns)
    if "EXAMPLE" not in ns or "TESTS" not in ns:
        raise ValueError(f"{prob['id']}: setup/tests must define EXAMPLE and TESTS")
    return ns


# ---------------------------------------------------------------------------
# Executing user code
# ---------------------------------------------------------------------------
def _plotting_modules():
    mods = {}
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        plt.show = lambda *a, **k: None   # non-interactive backend: show() is a no-op
        mods["plt"] = plt
    except ImportError:
        return mods
    try:
        import seaborn as sns
        mods["sns"] = sns
    except ImportError:
        pass
    return mods


def user_namespace():
    """Fresh namespace for each run: np, pd, plt and sns pre-imported."""
    ns = {"__name__": "__main__", "__builtins__": __builtins__, "np": np, "pd": pd}
    ns.update(_plotting_modules())
    return ns


def compile_function(code, filename, name="solve"):
    ns = user_namespace()
    exec(compile(code, filename, "exec"), ns)
    fn = ns.get(name)
    if not callable(fn):
        raise NameError(f"no function named {name}() was defined")
    return fn


class UserError(Exception):
    """An exception raised by user code, with a pre-formatted traceback."""

    def __init__(self, text):
        super().__init__(text)
        self.text = text


def format_user_exception(exc, code):
    lines = code.splitlines()
    if isinstance(exc, SyntaxError) and exc.filename == USER_FILE:
        out = [f"Line {exc.lineno}"]
        if exc.lineno and 0 < exc.lineno <= len(lines):
            src = lines[exc.lineno - 1]
            out.append("    " + src.strip())
            if exc.offset:
                pad = exc.offset - 1 - (len(src) - len(src.lstrip()))
                out.append("    " + " " * max(pad, 0) + "^")
        out.append(f"{type(exc).__name__}: {exc.msg}")
        return "\n".join(out)
    frames = [f for f in traceback.extract_tb(exc.__traceback__) if f.filename == USER_FILE]
    out = []
    if frames:
        out.append("Traceback (most recent call last):")
        for f in frames:
            src = lines[f.lineno - 1].strip() if f.lineno and 0 < f.lineno <= len(lines) else ""
            out.append(f"  Line {f.lineno}, in {f.name}")
            if src:
                out.append(f"    {src}")
    out.extend(s.rstrip("\n") for s in traceback.format_exception_only(type(exc), exc))
    return "\n".join(out)


def compile_user(code):
    try:
        return compile_function(code, USER_FILE)
    except Exception as exc:  # SyntaxError, NameError, errors at import time
        raise UserError(format_user_exception(exc, code)) from None


@contextlib.contextmanager
def capture():
    """Capture stdout and warnings raised while user code runs."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        for pattern in IGNORED_WARNINGS:
            warnings.filterwarnings("ignore", message=pattern)
        yield buf, w


def _warning_lines(records):
    seen, out = set(), []
    for r in records:
        msg = f"{r.category.__name__}: {r.message}"
        if msg not in seen:
            seen.add(msg)
            out.append(msg)
    return out[:10]


def _close_figures():
    if "matplotlib.pyplot" in sys.modules:
        sys.modules["matplotlib.pyplot"].close("all")


# ---------------------------------------------------------------------------
# Plots: structural summaries (never colors or style)
# ---------------------------------------------------------------------------
def is_plot(obj):
    if "matplotlib" not in sys.modules:
        return False
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure, SubFigure
    if isinstance(obj, (Figure, SubFigure, Axes)):
        return True
    fig = getattr(obj, "figure", None)
    return isinstance(fig, Figure) and hasattr(obj, "axes")   # seaborn FacetGrid & co.


def _fig(obj):
    """Figure behind an Axes, a Figure, or a seaborn grid (FacetGrid etc.)."""
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure, SubFigure
    if isinstance(obj, Axes):
        return obj.figure
    if isinstance(obj, (Figure, SubFigure)):
        return obj
    return obj.figure


def _ax_info(ax):
    from matplotlib.collections import PathCollection, PolyCollection, QuadMesh
    from matplotlib.patches import PathPatch, Rectangle
    import matplotlib.dates as mdates
    leg = ax.get_legend()
    xf, yf = ax.xaxis.get_major_formatter(), ax.yaxis.get_major_formatter()
    date_fmt = (mdates.AutoDateFormatter, mdates.ConciseDateFormatter, mdates.DateFormatter)

    def flat(seq):
        try:
            arr = np.asarray(seq, dtype=float)
            return bool(arr.size >= 2 and np.all(arr == arr[0]))
        except (TypeError, ValueError):
            return False

    scatter = [c for c in ax.collections if isinstance(c, PathCollection)]
    return {
        "title": ax.get_title(),
        "xlabel": ax.get_xlabel(),
        "ylabel": ax.get_ylabel(),
        "xscale": ax.get_xscale(),
        "yscale": ax.get_yscale(),
        "lines": len(ax.lines),
        "line_points": [len(l.get_xdata()) for l in ax.lines],
        "flat_lines": sum(flat(l.get_ydata()) for l in ax.lines),
        "vertical_lines": sum(flat(l.get_xdata()) for l in ax.lines),
        "bars": sum(isinstance(p, Rectangle) for p in ax.patches),
        "pathpatches": sum(isinstance(p, PathPatch) for p in ax.patches),
        "containers": len(ax.containers),
        "points": int(sum(len(c.get_offsets()) for c in scatter)),
        "scatter_groups": sum(len(c.get_offsets()) > 0 for c in scatter),
        "polys": sum(isinstance(c, PolyCollection) for c in ax.collections),
        "meshes": sum(isinstance(c, QuadMesh) for c in ax.collections),
        "images": len(ax.images),
        "texts": len(ax.texts),
        "legend": leg is not None,
        "legend_labels": [t.get_text() for t in leg.get_texts()] if leg is not None else [],
        "xticklabels": [t.get_text() for t in ax.get_xticklabels()],
        "yticklabels": [t.get_text() for t in ax.get_yticklabels()],
        "xdate": isinstance(xf, date_fmt),
        "xformatter": type(xf).__name__,
        "yformatter": type(yf).__name__,
    }


TICK_KEYS = {"xticklabels", "yticklabels"}


def plot_info(obj, draw=True):
    """Structure of a Figure / Axes / seaborn grid, as a plain dict. Tick
    label texts are only final after a draw, which is the slow part, so
    draw=False skips it when no tick labels are checked."""
    from matplotlib.axes import Axes
    fig = _fig(obj)
    if draw:
        fig.canvas.draw()
    all_axes = fig.axes
    main = [a for a in all_axes if a.get_label() != "<colorbar>"]
    shown = [obj] if isinstance(obj, Axes) else main
    first = main[0] if main else None
    sup = fig.get_suptitle() if hasattr(fig, "get_suptitle") else ""
    pos = [tuple(np.round(a.get_position().bounds, 3)) for a in main]
    return {
        "type": "Axes" if isinstance(obj, Axes) else type(obj).__name__,
        "n_axes": len(main),
        "colorbar": len(main) != len(all_axes),
        "suptitle": sup,
        "shared_x": bool(first) and len(main) > 1 and all(first.get_shared_x_axes().joined(first, a) for a in main),
        "shared_y": bool(first) and len(main) > 1 and all(first.get_shared_y_axes().joined(first, a) for a in main),
        "twin": len(pos) != len(set(pos)),
        "axes": [_ax_info(a) for a in shown],
    }


AXES_KEYS = {"title", "xlabel", "ylabel", "xscale", "yscale", "lines", "line_points", "flat_lines",
             "vertical_lines", "bars", "pathpatches", "containers", "points", "scatter_groups",
             "polys", "meshes", "images", "texts", "legend", "legend_labels", "xticklabels",
             "yticklabels", "xdate", "xformatter", "yformatter"}
FIG_KEYS = {"type", "n_axes", "colorbar", "suptitle", "shared_x", "shared_y", "twin"}
DEFAULT_PLOT_CHECKS = ["type", "n_axes", "title", "xlabel", "ylabel"]


def figure_png(obj, dpi=80):
    fig = _fig(obj)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    return base64.b64encode(buf.getvalue()).decode("ascii")


class PlotResult:
    """A rendered plot: structure + PNG, captured before figures are closed."""

    def __init__(self, obj=None, dpi=80, png=True, draw=True, info=None):
        if info is not None:                 # precomputed at build time
            self.type, self.info, self.png = info["type"], info, None
            return
        self.type = type(obj).__name__
        self.png = figure_png(obj, dpi) if png else None     # saving draws the figure
        self.info = plot_info(obj, draw=draw and not png)


def compare_plots(got, exp, checks):
    if not isinstance(got, PlotResult):
        return f"Expected a matplotlib/seaborn plot object ({exp.info['type']}), got {type_name(got)}"
    gi, ei = got.info, exp.info
    checks = checks or DEFAULT_PLOT_CHECKS
    for key in checks:
        if key in FIG_KEYS:
            if gi[key] != ei[key]:
                label = {"type": "returned object type", "n_axes": "number of subplots"}.get(key, key)
                return f"Figure: expected {label} = {ei[key]!r}, got {gi[key]!r}"
    for key in checks:
        if key in AXES_KEYS:
            for i, (ga, ea) in enumerate(zip(gi["axes"], ei["axes"])):
                if ga[key] != ea[key]:
                    where = f"Axes {i}" if len(ei["axes"]) > 1 else "Axes"
                    return f"{where}: expected {key} = {ea[key]!r}, got {ga[key]!r}"
            if len(gi["axes"]) != len(ei["axes"]):
                return f"Figure: expected {len(ei['axes'])} axes, got {len(gi['axes'])}"
        elif key not in FIG_KEYS:
            raise KeyError(f"unknown plot check {key!r}")
    return None


# ---------------------------------------------------------------------------
# Comparing results: return None when equal, else a message describing what
# differs first (type, shape, columns, index, dtype or values).
# ---------------------------------------------------------------------------
def type_name(x):
    if isinstance(x, PlotResult):
        return x.type
    return type(x).__name__


def _fmt(v):
    if isinstance(v, float) or isinstance(v, np.floating):
        return repr(float(v)) if not math.isnan(v) else "NaN"
    if isinstance(v, (pd.Timestamp, np.datetime64)):
        ts = pd.Timestamp(v)
        return str(ts.date()) if ts == ts.normalize() else str(ts)
    s = repr(v)
    return s if len(s) < 120 else s[:117] + "..."


def _dtype_family(dt):
    """dtype label used for comparison: datetime units and object-vs-str
    string storage are treated as equal (they vary across pandas versions)."""
    if isinstance(dt, pd.CategoricalDtype):
        return "category"
    if pd.api.types.is_datetime64_any_dtype(dt):
        return f"datetime64[{getattr(dt, 'tz', None)}]"
    if pd.api.types.is_timedelta64_dtype(dt):
        return "timedelta64"
    if pd.api.types.is_string_dtype(dt) or dt == object:
        return "string/object"
    return str(dt)


def _is_num_kind(arr):
    return arr.dtype.kind in "biuf"


def _values_mismatch(g, e, rtol, atol, exact=False):
    """First position where 1-d arrays g, e differ (NaN == NaN), or None."""
    g = np.asarray(g)
    e = np.asarray(e)
    if g.dtype.kind in "biuf" and e.dtype.kind in "biuf":
        gf, ef = g.astype(float), e.astype(float)
        ok = (gf == ef) if exact else np.isclose(gf, ef, rtol=rtol, atol=atol, equal_nan=True)
        ok |= np.isnan(gf) & np.isnan(ef)
    elif g.dtype.kind in "mM" and e.dtype.kind in "mM":
        ok = (g == e) | (pd.isna(g) & pd.isna(e))
    else:
        gs, es = pd.Series(g, dtype=object), pd.Series(e, dtype=object)
        ok = np.empty(len(gs), dtype=bool)
        for i, (a, b) in enumerate(zip(gs, es)):
            na_a, na_b = _isna_scalar(a), _isna_scalar(b)
            if na_a or na_b:
                ok[i] = na_a and na_b
            elif _is_number(a) and _is_number(b) and not isinstance(a, bool) and not isinstance(b, bool):
                ok[i] = (a == b) if exact else bool(np.isclose(float(a), float(b), rtol=rtol, atol=atol))
            else:
                try:
                    ok[i] = bool(a == b)
                except Exception:
                    ok[i] = False
    bad = np.flatnonzero(~np.asarray(ok, dtype=bool))
    return int(bad[0]) if len(bad) else None


def _isna_scalar(v):
    try:
        return bool(pd.isna(v)) if np.ndim(v) == 0 else False
    except (TypeError, ValueError):
        return False


def _is_number(v):
    return isinstance(v, (int, float, np.integer, np.floating, np.bool_)) and not isinstance(v, bool)


def _index_mismatch(gi, ei, rtol, atol):
    if len(gi) != len(ei):
        return f"length {len(ei)} expected, got {len(gi)}"
    if isinstance(ei, pd.MultiIndex) != isinstance(gi, pd.MultiIndex) or (
            isinstance(ei, pd.MultiIndex) and ei.nlevels != gi.nlevels):
        return f"expected {_index_desc(ei)}, got {_index_desc(gi)}"
    if isinstance(ei, pd.MultiIndex):
        for lev in range(ei.nlevels):
            pos = _values_mismatch(gi.get_level_values(lev), ei.get_level_values(lev), rtol, atol)
            if pos is not None:
                return f"label {pos} expected {_fmt(ei[pos])}, got {_fmt(gi[pos])}"
        return None
    pos = _values_mismatch(gi.to_numpy(), ei.to_numpy(), rtol, atol)
    if pos is not None:
        return f"label at position {pos} expected {_fmt(ei[pos])}, got {_fmt(gi[pos])}"
    return None


def _index_desc(ix):
    if isinstance(ix, pd.MultiIndex):
        return f"a MultiIndex with levels {list(ix.names)}"
    if isinstance(ix, pd.RangeIndex) or (ix.dtype.kind == "i" and ix.equals(pd.RangeIndex(len(ix)))):
        return "a default 0..n-1 index"
    return f"an index named {ix.name!r}" if ix.name is not None else "an unnamed index"


def _sort_frame(df):
    df = df.reset_index(drop=True)
    try:
        return df.sort_values(list(df.columns), kind="stable", na_position="last").reset_index(drop=True)
    except TypeError:
        return df


class Opts:
    def __init__(self, rtol=1e-5, atol=1e-8, check_dtype=False, check_like=False, check_names=False,
                 check_index=True, sort_rows=False, ignore_index=False, ordered=True,
                 check_exact=False, check_column_order=True):
        self.rtol, self.atol, self.check_dtype = rtol, atol, check_dtype
        self.check_like, self.check_names, self.check_index = check_like, check_names, check_index
        self.sort_rows, self.ignore_index, self.ordered = sort_rows, ignore_index, ordered
        self.check_exact, self.check_column_order = check_exact, check_column_order


def compare(got, exp, path="Result", **opts):
    """None if got matches exp, else a message describing the first
    difference. Options (all optional; set per problem in `compare`):

    rtol/atol      float tolerance (default 1e-5 / 1e-8)
    check_dtype    compare dtypes (datetime units and str/object are treated as equal)
    check_like     ignore row and column order (align on labels)
    check_column_order  (default True) column order must match
    check_names    compare Series.name and index names
    check_index    compare the index (default True)
    ignore_index   reset both indexes before comparing
    sort_rows      sort rows by all columns before comparing (implies ignore_index)
    ordered        for lists/arrays of scalars: False compares sorted values
    check_exact    exact float comparison
    """
    o = opts if isinstance(opts, Opts) else Opts(**opts)
    return _cmp(got, exp, o, path)


def _cmp(got, exp, o, path):
    if isinstance(exp, PlotResult):
        return compare_plots(got, exp, None)
    if isinstance(exp, pd.DataFrame):
        if not isinstance(got, pd.DataFrame):
            return f"{path}: expected a DataFrame, got {type_name(got)}"
        return _cmp_df(got, exp, o, path)
    if isinstance(exp, pd.Series):
        if not isinstance(got, pd.Series):
            return f"{path}: expected a Series, got {type_name(got)}"
        return _cmp_series(got, exp, o, path)
    if isinstance(exp, pd.Index):
        if not isinstance(got, (pd.Index, np.ndarray, list)):
            return f"{path}: expected an Index, got {type_name(got)}"
        return _cmp_array(np.asarray(got), exp.to_numpy(), o, path)
    if isinstance(exp, np.ndarray):
        if not isinstance(got, np.ndarray):
            return f"{path}: expected a NumPy array, got {type_name(got)}"
        return _cmp_array(got, exp, o, path)
    if isinstance(exp, dict):
        if not isinstance(got, dict):
            return f"{path}: expected a dict, got {type_name(got)}"
        missing = [k for k in exp if k not in got]
        extra = [k for k in got if k not in exp]
        if missing:
            return f"{path}: missing key(s) {missing}"
        if extra:
            return f"{path}: unexpected key(s) {extra}"
        for k in exp:
            msg = _cmp(got[k], exp[k], o, f"{path}[{k!r}]")
            if msg:
                return msg
        return None
    if isinstance(exp, (list, tuple)):
        if not isinstance(got, (list, tuple)):
            return f"{path}: expected a {type(exp).__name__} of length {len(exp)}, got {type_name(got)}"
        if len(got) != len(exp):
            return f"{path}: expected length {len(exp)}, got {len(got)}"
        g, e = list(got), list(exp)
        if not o.ordered:
            try:
                g, e = sorted(g), sorted(e)
            except TypeError:
                pass
        for i, (a, b) in enumerate(zip(g, e)):
            msg = _cmp(a, b, o, f"{path}[{i}]")
            if msg:
                return msg
        return None
    if isinstance(exp, (set, frozenset)):
        if not isinstance(got, (set, frozenset)):
            return f"{path}: expected a set, got {type_name(got)}"
        if set(got) != set(exp):
            return (f"{path}: sets differ; missing {sorted(set(exp) - set(got), key=str)[:5]}, "
                    f"unexpected {sorted(set(got) - set(exp), key=str)[:5]}")
        return None
    if exp is None:
        return None if got is None else f"{path}: expected None, got {type_name(got)}"
    if isinstance(exp, (bool, np.bool_)):
        if not isinstance(got, (bool, np.bool_)):
            return f"{path}: expected a bool, got {type_name(got)}"
        return None if bool(got) == bool(exp) else f"{path}: expected {bool(exp)}, got {bool(got)}"
    if _is_number(exp):
        if isinstance(got, np.ndarray) and got.ndim == 0:
            got = got.item()
        if not _is_number(got):
            return f"{path}: expected a number, got {type_name(got)}"
        if isinstance(exp, (int, np.integer)) and o.check_dtype and not isinstance(got, (int, np.integer)):
            return f"{path}: expected an integer, got {type_name(got)} {_fmt(got)}"
        e, g = float(exp), float(got)
        if math.isnan(e) or math.isnan(g):
            return None if math.isnan(e) and math.isnan(g) else f"{path}: expected {_fmt(exp)}, got {_fmt(got)}"
        ok = (g == e) if o.check_exact else math.isclose(g, e, rel_tol=o.rtol, abs_tol=o.atol)
        return None if ok else f"{path}: expected {_fmt(exp)}, got {_fmt(got)}"
    if isinstance(exp, str):
        if not isinstance(got, str):
            return f"{path}: expected a str, got {type_name(got)}"
        return None if got == exp else f"{path}: expected {exp!r}, got {got!r}"
    if isinstance(exp, (pd.Timestamp, np.datetime64)):
        try:
            return None if pd.Timestamp(got) == pd.Timestamp(exp) else f"{path}: expected {_fmt(exp)}, got {_fmt(got)}"
        except (TypeError, ValueError):
            return f"{path}: expected a timestamp, got {type_name(got)}"
    if type(got) is not type(exp):
        return f"{path}: expected {type_name(exp)}, got {type_name(got)}"
    try:
        return None if got == exp else f"{path}: expected {_fmt(exp)}, got {_fmt(got)}"
    except Exception:
        return None


def _cmp_df(g, e, o, path):
    if o.sort_rows:
        g, e = _sort_frame(g), _sort_frame(e)
    elif o.ignore_index:
        g, e = g.reset_index(drop=True), e.reset_index(drop=True)
    if g.shape != e.shape:
        return f"{path}: shape differs: expected {e.shape}, got {g.shape}"
    gc, ec = list(g.columns), list(e.columns)
    if gc != ec:
        if set(map(str, gc)) != set(map(str, ec)) or len(set(gc)) != len(gc):
            missing = [c for c in ec if c not in gc]
            extra = [c for c in gc if c not in ec]
            return f"{path}: columns differ: missing {missing}, unexpected {extra} (expected {ec})"
        if o.check_column_order and not o.check_like:
            return f"{path}: column order differs: expected {ec}, got {gc}"
        g = g[ec]
    if o.check_like and o.check_index and g.index.is_unique and e.index.is_unique:
        if set(g.index) == set(e.index):
            g = g.reindex(e.index)
    if o.check_index:
        msg = _index_mismatch(g.index, e.index, o.rtol, o.atol)
        if msg:
            return f"{path}: index differs ({_index_desc(e.index)} expected): {msg}"
        if o.check_names and list(g.index.names) != list(e.index.names):
            return f"{path}: index names differ: expected {list(e.index.names)}, got {list(g.index.names)}"
    if o.check_dtype:
        for c in ec:
            if _dtype_family(g[c].dtype) != _dtype_family(e[c].dtype):
                return f"{path}: dtype of column {c!r} differs: expected {e[c].dtype}, got {g[c].dtype}"
    for j, c in enumerate(ec):
        gcol, ecol = g.iloc[:, j], e.iloc[:, j]
        pos = _values_mismatch(_plain(gcol), _plain(ecol), o.rtol, o.atol, o.check_exact)
        if pos is not None:
            return (f"{path}: value differs at row {_fmt(e.index[pos])}, column {c!r}: "
                    f"expected {_fmt(ecol.iloc[pos])}, got {_fmt(gcol.iloc[pos])}")
    return None


def _plain(s):
    """Series -> numpy array suitable for value comparison."""
    if isinstance(s.dtype, pd.CategoricalDtype):
        return s.astype(object).to_numpy()
    if isinstance(s.dtype, pd.api.extensions.ExtensionDtype) and s.dtype.kind in "biuf":
        return s.to_numpy(dtype=float, na_value=np.nan)
    if s.dtype.kind == "M" and getattr(s.dtype, "tz", None) is None:
        return s.to_numpy().astype("datetime64[ns]")
    return s.to_numpy()


def _cmp_series(g, e, o, path):
    if o.sort_rows:
        g = g.sort_values(kind="stable").reset_index(drop=True)
        e = e.sort_values(kind="stable").reset_index(drop=True)
    elif o.ignore_index:
        g, e = g.reset_index(drop=True), e.reset_index(drop=True)
    if len(g) != len(e):
        return f"{path}: length differs: expected {len(e)}, got {len(g)}"
    if o.check_names and g.name != e.name:
        return f"{path}: Series name differs: expected {e.name!r}, got {g.name!r}"
    if o.check_like and o.check_index and g.index.is_unique and e.index.is_unique and set(g.index) == set(e.index):
        g = g.reindex(e.index)
    if o.check_index:
        msg = _index_mismatch(g.index, e.index, o.rtol, o.atol)
        if msg:
            return f"{path}: index differs ({_index_desc(e.index)} expected): {msg}"
        if o.check_names and list(g.index.names) != list(e.index.names):
            return f"{path}: index names differ: expected {list(e.index.names)}, got {list(g.index.names)}"
    if o.check_dtype and _dtype_family(g.dtype) != _dtype_family(e.dtype):
        return f"{path}: dtype differs: expected {e.dtype}, got {g.dtype}"
    pos = _values_mismatch(_plain(g), _plain(e), o.rtol, o.atol, o.check_exact)
    if pos is not None:
        return f"{path}: value differs at index {_fmt(e.index[pos])}: expected {_fmt(e.iloc[pos])}, got {_fmt(g.iloc[pos])}"
    return None


def _cmp_array(g, e, o, path):
    if g.shape != e.shape:
        return f"{path}: shape differs: expected {e.shape}, got {g.shape}"
    if o.check_dtype and g.dtype != e.dtype:
        if not (g.dtype.kind == e.dtype.kind == "U" or (g.dtype.kind in "OU" and e.dtype.kind in "OU")):
            return f"{path}: dtype differs: expected {e.dtype}, got {g.dtype}"
    gf, ef = g.ravel(), e.ravel()
    if not o.ordered:
        gf, ef = np.sort(gf), np.sort(ef)
    pos = _values_mismatch(gf, ef, o.rtol, o.atol, o.check_exact)
    if pos is not None:
        where = np.unravel_index(pos, e.shape) if o.ordered and e.ndim > 1 else (pos,)
        where = tuple(int(i) for i in where)
        label = where if len(where) > 1 else where[0]
        return f"{path}: value differs at position {label}: expected {_fmt(ef[pos])}, got {_fmt(gf[pos])}"
    return None


# ---------------------------------------------------------------------------
# Previews (JSON-friendly renderings of values for the UI)
# ---------------------------------------------------------------------------
def _df_html(df, max_rows=10):
    with pd.option_context("display.precision", 4, "display.max_colwidth", 40):
        return df.to_html(max_rows=max_rows, max_cols=14, border=0, classes="df", na_rep="NaN")


def preview(obj, max_rows=10, depth=0):
    if isinstance(obj, PlotResult):
        return {"kind": "figure", "png": obj.png, "type": obj.type}
    if is_plot(obj):
        return {"kind": "figure", "png": figure_png(obj), "type": type(obj).__name__}
    if isinstance(obj, pd.DataFrame):
        return {"kind": "df", "shape": list(obj.shape),
                "dtypes": [[str(c), str(t)] for c, t in obj.dtypes.items()],
                "index": _index_desc(obj.index), "html": _df_html(obj, max_rows)}
    if isinstance(obj, pd.Series):
        name = obj.name if obj.name is not None else ""
        return {"kind": "series", "shape": [len(obj)], "dtype": str(obj.dtype),
                "name": None if obj.name is None else str(obj.name), "index": _index_desc(obj.index),
                "html": _df_html(obj.to_frame(name=name), max_rows)}
    if isinstance(obj, pd.Index):
        return {"kind": "text", "type": type(obj).__name__, "text": repr(obj)[:3000]}
    if isinstance(obj, np.ndarray):
        with np.printoptions(threshold=80, edgeitems=4, linewidth=100, precision=4, suppress=True):
            text = np.array2string(obj, separator=", ") if obj.size else repr(obj)
        return {"kind": "array", "shape": list(obj.shape), "dtype": str(obj.dtype), "text": text[:5000]}
    if depth < 2 and isinstance(obj, (list, tuple)) and 0 < len(obj) <= 8 and any(
            isinstance(v, (pd.DataFrame, pd.Series, np.ndarray, PlotResult)) or is_plot(v) for v in obj):
        return {"kind": "seq", "type": type(obj).__name__,
                "items": [preview(v, max_rows, depth + 1) for v in obj]}
    if depth < 2 and isinstance(obj, dict) and 0 < len(obj) <= 12 and any(
            isinstance(v, (pd.DataFrame, pd.Series, np.ndarray, PlotResult)) for v in obj.values()):
        return {"kind": "dict", "items": [[repr(k), preview(v, max_rows, depth + 1)] for k, v in obj.items()]}
    if hasattr(obj, "get_params") and hasattr(obj, "fit"):
        return {"kind": "text", "type": type(obj).__name__, "text": repr(obj)[:3000]}
    text = _pretty(obj)
    return {"kind": "text", "type": type(obj).__name__, "text": text[:5000]}


def _pretty(obj):
    if isinstance(obj, float) or isinstance(obj, np.floating):
        return repr(float(obj))
    if isinstance(obj, dict) and len(obj) > 1:
        return "{\n" + "\n".join(f"    {k!r}: {_pretty(v)}," for k, v in obj.items()) + "\n}"
    return repr(obj)


# ---------------------------------------------------------------------------
# Running a problem
# ---------------------------------------------------------------------------
def _call(fn, inputs):
    t0 = time.perf_counter()
    out = fn(**inputs)
    return out, time.perf_counter() - t0


def _capture_result(obj, png=True, draw=True):
    """Convert plot objects into PlotResult (structure + PNG) before the
    figures are closed; other values pass through."""
    if is_plot(obj):
        return PlotResult(obj, png=png, draw=draw)
    return obj


def _make_inputs(test):
    inputs = test.make()
    if not isinstance(inputs, dict):
        raise TypeError("test input factories must return a dict of keyword arguments")
    return inputs


def _check(P, prob, got, exp, test):
    plot = prob.get("plot")
    if plot and isinstance(exp, PlotResult):
        msg = compare_plots(got, exp, plot.get("checks"))
        if msg:
            return msg
    custom = P.get("check")
    if custom is not None:
        try:
            msg = custom(got, exp, _make_inputs(test))
        except CheckFailed as e:
            return str(e)
        except AssertionError as e:
            return str(e) or "custom check failed"
        except Exception as e:
            return f"{type(e).__name__} while checking your result: {e}"
        return msg or None
    if plot and isinstance(exp, PlotResult):
        return None
    return compare(got, exp, **(prob.get("compare") or {}))


def _render(fn, test):
    """Re-run fn on fresh inputs and capture its plot with a PNG (or None)."""
    _close_figures()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            out = fn(**_make_inputs(test))
            return _capture_result(out, png=True) if is_plot(out) else None
    except Exception:
        return None
    finally:
        _close_figures()


def _inputs_changed(before, after, opts):
    for k, v in before.items():
        if compare(after[k], v, check_dtype=True) is not None:
            return k
    return None


def evaluate(prob, code, which="tests", details=True, png=True, ref_fn=None):
    """Grade `code` on a problem.

    which: "example" (Run) or "tests" (Submit). Returns a dict with
    passed (bool), cases [{name, passed, error, time, ref_time}], and for the
    first failing case (or the example) previews of inputs/expected/got.
    Errors in the problem definition itself raise.
    """
    P = load_problem(prob)
    if ref_fn is None:
        ref_fn = compile_function(prob["solution"], f"<reference {prob['id']}>")
    if prob.get("expected_plots") and len(prob["expected_plots"]["tests"]) != len(P["TESTS"]):
        prob = {k: v for k, v in prob.items() if k != "expected_plots"}
    tests = [Test(P["EXAMPLE"], "Example")] if which == "example" else [_as_test(t) for t in P["TESTS"]]
    checks = (prob.get("plot") or {}).get("checks") or DEFAULT_PLOT_CHECKS
    need_draw = bool(TICK_KEYS & set(checks))
    pre = prob.get("expected_plots")
    result = {"passed": True, "cases": [], "stdout": "", "warnings": [], "compile_error": None}
    _close_figures()
    try:
        user_fn = compile_user(code)
    except UserError as e:
        result.update(passed=False, compile_error=e.text)
        return result
    for i, test in enumerate(tests):
        name = test.name or f"Test {i + 1}"
        case = {"name": name, "passed": False, "error": None, "diff": None, "time": None, "ref_time": None}
        inputs_u = _make_inputs(test)
        before = _make_inputs(test) if prob.get("mutation_check") else None
        got = None
        with capture() as (buf, wrec):
            try:
                got, case["time"] = _call(user_fn, inputs_u)
            except Exception as exc:
                case["error"] = format_user_exception(exc, code)
        stdout = buf.getvalue()
        if case["error"] is None:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                got = _capture_result(got, png=png and details and which == "example", draw=need_draw)
        result["warnings"].extend(w for w in _warning_lines(wrec) if w not in result["warnings"])
        open_figs = []
        if case["error"] is None and not isinstance(got, PlotResult) and "matplotlib.pyplot" in sys.modules:
            plt = sys.modules["matplotlib.pyplot"]
            if plt.get_fignums() and details and which == "example":
                open_figs = [figure_png(plt.figure(n)) for n in plt.get_fignums()[:3]]
        _close_figures()
        if pre:   # plot problems: expected structure precomputed at build time
            exp = PlotResult(info=pre["example"] if which == "example" else pre["tests"][i])
        else:
            exp, case["ref_time"] = _call(ref_fn, _make_inputs(test))
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                exp = _capture_result(exp, png=False, draw=need_draw)   # target image is embedded
            _close_figures()
        if case["error"] is None:
            msg = _check(P, prob, got, exp, test)
            if msg is None and before is not None:
                k = _inputs_changed(before, inputs_u, None)
                if k:
                    msg = f"solve() modified its input {k!r} in place; work on a copy instead"
            if msg is None and test.timed and case["ref_time"] is not None and                     case["time"] > max(SLOW_MIN, SLOW_FACTOR * case["ref_time"]):
                msg = (f"Too slow on a large input: {case['time']:.2f}s vs {case['ref_time']:.3f}s "
                       f"for the reference. Vectorize instead of looping in Python.")
            case["diff"] = msg
            case["passed"] = msg is None
        if len(stdout) > MAX_STDOUT:
            stdout = stdout[:MAX_STDOUT] + "\n... (output truncated)"
        if which == "example":
            result["stdout"] = stdout
        result["cases"].append(case)
        if not case["passed"] and result["passed"]:
            result["passed"] = False
            if details and png and (isinstance(exp, PlotResult) or isinstance(got, PlotResult)):
                # Plots were captured without images (fast path); redraw this case.
                exp = _render(ref_fn, test) or exp
                if case["error"] is None and isinstance(got, PlotResult):
                    with contextlib.redirect_stdout(io.StringIO()):
                        got = _render(user_fn, test) or got
            if details:
                result["failure"] = {
                    "index": i, "name": name, "stdout": stdout,
                    "inputs": {k: preview(v) for k, v in _make_inputs(test).items()},
                    "expected": preview(exp),
                    "got": None if case["error"] else preview(got),
                    "figures": open_figs,
                }
        if which == "example" and details:
            result["got"] = None if case["error"] else preview(got)
            result["figures"] = open_figs
    result["warnings"] = result["warnings"][:10]
    return result


# ---------------------------------------------------------------------------
# Playground: persistent namespace, notebook-style display of the last value
# ---------------------------------------------------------------------------
PLAYGROUND_PRELOAD = '''
orders = D.orders(seed=0, n=1500, n_customers=200)
customers = D.customers(seed=0, n=200)
orders_raw = D.orders_raw(seed=0, n=1500, n_customers=200)
hr = D.hr(seed=0, n=800)
hr_raw = D.hr_raw(seed=0, n=800)
churn = D.churn(seed=0, n=3000)
churn_raw = D.churn(seed=0, n=3000, messy=True)
prices = D.prices(seed=0, n_days=500, n_tickers=20)
prices_wide = D.prices_wide(seed=0, n_days=500, n_tickers=20)
factors = D.factor_panel(seed=0, n_dates=60, n_tickers=100)
sensors = D.sensors(seed=0, n_sensors=4, days=7)
ab = D.ab_test(seed=0, n=5000)
'''

PLAYGROUND_NAMES = ["orders", "customers", "orders_raw", "hr", "hr_raw", "churn", "churn_raw",
                    "prices", "prices_wide", "factors", "sensors", "ab"]

_PLAYGROUND = {}


def playground_reset():
    ns = user_namespace()
    ns["D"] = D
    exec(PLAYGROUND_PRELOAD, ns)
    _PLAYGROUND.clear()
    _PLAYGROUND.update(ns)
    return ns


def run_cell(code, ns, filename=USER_FILE):
    """Execute code in ns; if the last statement is an expression, return
    its value (like a notebook cell)."""
    tree = ast.parse(code, filename)
    last = None
    if tree.body and isinstance(tree.body[-1], ast.Expr):
        last = ast.Expression(tree.body.pop().value)
    exec(compile(tree, filename, "exec"), ns)
    if last is not None:
        return eval(compile(last, filename, "eval"), ns)
    return None


def playground_run(code):
    if not _PLAYGROUND:
        playground_reset()
    ns = _PLAYGROUND
    for k, v in _plotting_modules().items():    # plt/sns may have loaded after the reset
        ns.setdefault(k, v)
    out = {"stdout": "", "error": None, "value": None, "figures": [], "warnings": []}
    with capture() as (buf, wrec):
        try:
            value = run_cell(code, ns)
            if value is not None:
                out["value"] = preview(value, max_rows=20)
        except Exception as exc:
            out["error"] = format_user_exception(exc, code)
    out["stdout"] = buf.getvalue()[:MAX_STDOUT]
    out["warnings"] = _warning_lines(wrec)
    if "matplotlib.pyplot" in sys.modules:
        plt = sys.modules["matplotlib.pyplot"]
        shown = out["value"] and out["value"].get("kind") == "figure"
        if not shown:
            out["figures"] = [figure_png(plt.figure(n), dpi=90) for n in plt.get_fignums()[:6]]
        plt.close("all")
    return out


def playground_names():
    if not _PLAYGROUND:
        playground_reset()
    rows = []
    for name in PLAYGROUND_NAMES:
        v = _PLAYGROUND.get(name)
        if isinstance(v, pd.DataFrame):
            rows.append([name, f"{v.shape[0]} x {v.shape[1]}", ", ".join(map(str, v.columns))])
    return rows


# ---------------------------------------------------------------------------
# Worker entry point
# ---------------------------------------------------------------------------
def run_job(job):
    kind = job["kind"]
    try:
        if kind in ("run", "submit"):
            r = evaluate(job["problem"], job["code"], "example" if kind == "run" else "tests")
            r["kind"] = kind
            return r
        if kind == "playground":
            return playground_run(job["code"])
        if kind == "playground_reset":
            playground_reset()
            return {"ok": True, "names": playground_names()}
        if kind == "playground_names":
            return {"names": playground_names()}
        raise ValueError(f"unknown job kind {kind!r}")
    except Exception:
        return {"internal_error": traceback.format_exc()}
    finally:
        _close_figures()


def expected_plot_infos(prob, ref_fn=None):
    """Structure of the reference plot for the example and every test (used at
    build time; embedded in the page so Submit doesn't re-run the reference)."""
    P = load_problem(prob)
    ref_fn = ref_fn or compile_function(prob["solution"], f"<reference {prob['id']}>")
    checks = (prob.get("plot") or {}).get("checks") or DEFAULT_PLOT_CHECKS
    draw = bool(TICK_KEYS & set(checks))
    out = {"example": None, "tests": []}
    for i, test in enumerate([Test(P["EXAMPLE"])] + [_as_test(t) for t in P["TESTS"]]):
        _close_figures()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            info = plot_info(ref_fn(**_make_inputs(test)), draw=draw)
        _close_figures()
        if i == 0:
            out["example"] = info
        else:
            out["tests"].append(info)
    return out
