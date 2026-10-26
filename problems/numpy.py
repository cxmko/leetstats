SECTION = "numpy"

PROBLEMS = [
dict(
    id="np-001",
    title="Strike grid",
    difficulty="Easy",
    tags=["array creation"],
    signature="def solve(lo: float, hi: float, n: int) -> np.ndarray:",
    statement="""
An options desk wants `n` strikes evenly spaced from `lo` to `hi`, with **both ends included**.

Return a 1-D float array of length `n` (for `n == 1`, just `[lo]`).
""",
    setup="""
EXAMPLE = lambda: {"lo": 90.0, "hi": 110.0, "n": 5}
""",
    tests="""
TESTS = [
    lambda: {"lo": 0.5, "hi": 2.0, "n": 7},
    lambda: {"lo": -1.0, "hi": 1.0, "n": 101},
    Test(lambda: {"lo": 100.0, "hi": 120.0, "n": 1}, "single strike"),
    Test(lambda: {"lo": 0.1, "hi": 0.3, "n": 3}, "float step that arange gets wrong"),
]
""",
    hint1="`np.linspace(start, stop, num)` includes both endpoints by default.",
    hint2="np.linspace(lo, hi, n)",
    solution="""
def solve(lo, hi, n):
    return np.linspace(lo, hi, n)
""",
    explanation="""
`linspace` takes a **count** and includes the stop; `arange` takes a **step** and excludes the stop, and float steps can add or drop an element through rounding (try `np.arange(0.1, 0.3, 0.1)`). Use `arange` for integer ranges and `linspace` for grids.
""",
    docs=["https://numpy.org/doc/stable/reference/generated/numpy.linspace.html",
          "https://numpy.org/doc/stable/reference/generated/numpy.arange.html"],
    wrong_solutions=[
        dict(code="def solve(lo, hi, n):\n    return np.linspace(lo, hi, n, endpoint=False)", why="excludes hi"),
        dict(code="def solve(lo, hi, n):\n    step = (hi - lo) / max(n - 1, 1)\n    return np.arange(lo, hi + step, step)", why="arange with a float step"),
    ],
),
dict(
    id="np-002",
    title="Constant-correlation matrix",
    difficulty="Easy",
    tags=["array creation"],
    signature="def solve(n: int, rho: float) -> np.ndarray:",
    statement="""
Build the `n x n` correlation matrix of a constant-correlation model: `1.0` on the diagonal and `rho` everywhere else.

Return a float array.
""",
    setup="""
EXAMPLE = lambda: {"n": 4, "rho": 0.3}
""",
    tests="""
TESTS = [
    lambda: {"n": 10, "rho": -0.05},
    lambda: {"n": 3, "rho": 0.0},
    Test(lambda: {"n": 1, "rho": 0.5}, "1 x 1"),
    lambda: {"n": 25, "rho": 0.9},
]
""",
    hint1="Fill everything with `np.full((n, n), rho)`, then fix the diagonal with `np.fill_diagonal` or by adding `(1 - rho) * np.eye(n)`.",
    hint2="np.full((n, n), rho) + (1 - rho) * np.eye(n)",
    solution="""
def solve(n, rho):
    return np.full((n, n), rho) + (1 - rho) * np.eye(n)
""",
    explanation="""
`np.full(shape, value)` and `np.eye(n)` are the building blocks for structured matrices. `np.fill_diagonal(A, 1.0)` works too, but it modifies `A` in place and returns `None`, a common slip when you write `return np.fill_diagonal(...)`.
""",
    docs=["https://numpy.org/doc/stable/reference/generated/numpy.full.html",
          "https://numpy.org/doc/stable/reference/generated/numpy.eye.html",
          "https://numpy.org/doc/stable/reference/generated/numpy.fill_diagonal.html"],
    wrong_solutions=[
        dict(code="def solve(n, rho):\n    return np.full((n, n), rho)", why="diagonal not set"),
        dict(code="def solve(n, rho):\n    return np.eye(n) * rho + 1", why="wrong construction"),
        dict(code="def solve(n, rho):\n    A = np.full((n, n), rho)\n    return np.fill_diagonal(A, 1.0)", why="fill_diagonal returns None"),
    ],
),
dict(
    id="np-003",
    title="Pixels to float32 in [0, 1]",
    difficulty="Easy",
    tags=["dtypes"],
    signature="def solve(img: np.ndarray) -> np.ndarray:",
    statement="""
`img` is an image stored as `uint8` (values 0-255, any shape). Before feeding it to a model, scale it to `[0, 1]`.

Return an array of the same shape with dtype **float32** (the dtype is checked: float64 would double the memory).
""",
    setup="""
def make(seed, shape):
    rng = np.random.default_rng(seed)
    return {"img": rng.integers(0, 256, size=shape, dtype=np.uint8)}

EXAMPLE = lambda: {"img": np.array([[0, 128], [255, 64]], dtype=np.uint8)}
""",
    tests="""
TESTS = [
    lambda: make(1, (8, 8)),
    lambda: make(2, (32, 32, 3)),
    Test(lambda: {"img": np.array([255], dtype=np.uint8)}, "single pixel"),
]
""",
    compare=dict(check_dtype=True),
    hint1="Cast first with `.astype(np.float32)`, then divide by 255.",
    hint2="img.astype(np.float32) / 255",
    solution="""
def solve(img):
    return img.astype(np.float32) / 255
""",
    explanation="""
`img / 255` promotes uint8 to float64. Cast first: under NumPy 2's promotion rules (NEP 50), a float32 array divided by a Python number stays float32. Dividing by a NumPy float64 scalar would still upcast.
""",
    docs=["https://numpy.org/doc/stable/reference/generated/numpy.ndarray.astype.html",
          "https://numpy.org/doc/stable/user/basics.types.html"],
    wrong_solutions=[
        dict(code="def solve(img):\n    return img / 255", why="float64"),
        dict(code="def solve(img):\n    return img.astype(np.float32) // 255", why="floor division"),
    ],
),
dict(
    id="np-004",
    title="Hour-by-day matrix",
    difficulty="Easy",
    tags=["reshaping"],
    signature="def solve(readings: np.ndarray) -> np.ndarray:",
    statement="""
`readings` is a flat array of hourly meter readings covering whole days, in time order: day 1 hours 0-23, then day 2 hours 0-23, and so on.

Return a 2-D array with **one row per hour of the day (24 rows) and one column per day**, so `out[h, d]` is the reading at hour `h` of day `d`.
""",
    setup="""
def make(seed, days):
    rng = np.random.default_rng(seed)
    return {"readings": np.round(rng.gamma(3.0, 1.0, 24 * days), 2)}

EXAMPLE = lambda: {"readings": np.arange(48.0)}
""",
    tests="""
TESTS = [
    lambda: make(1, 3),
    lambda: make(2, 30),
    Test(lambda: make(3, 1), "one day"),
]
""",
    hint1="`reshape(-1, 24)` gives one row per day; then transpose with `.T`.",
    hint2="readings.reshape(-1, 24).T",
    solution="""
def solve(readings):
    return readings.reshape(-1, 24).T
""",
    explanation="""
`reshape` fills row by row (C order). The data is day-major, so reshape to `(days, 24)` first, then transpose. `reshape(24, -1)` has the right shape but scrambles the data: its first row is hours 0-23 of day 1, not hour 0 of every day. Equivalent: `readings.reshape(-1, 24, order='C').T` or `readings.reshape(24, -1, order='F')`.
""",
    docs=["https://numpy.org/doc/stable/reference/generated/numpy.reshape.html",
          "https://numpy.org/doc/stable/reference/generated/numpy.ndarray.T.html"],
    wrong_solutions=[
        dict(code="def solve(readings):\n    return readings.reshape(24, -1)", why="right shape, scrambled order"),
        dict(code="def solve(readings):\n    return readings.reshape(-1, 24)", why="not transposed"),
    ],
),
dict(
    id="np-005",
    title="Zero a row without touching the input",
    difficulty="Easy",
    tags=["views & copies"],
    signature="def solve(X: np.ndarray, i: int) -> np.ndarray:",
    statement="""
Return a version of the 2-D array `X` in which row `i` is all zeros.

`X` itself must **not** change: the caller reuses it afterwards (the tests check this).
""",
    setup="""
def make(seed, n, k, i):
    rng = np.random.default_rng(seed)
    return {"X": np.round(rng.normal(size=(n, k)), 3), "i": i}

EXAMPLE = lambda: {"X": np.arange(6.0).reshape(3, 2), "i": 1}
""",
    tests="""
TESTS = [
    lambda: make(1, 5, 3, 0),
    lambda: make(2, 40, 6, 39),
    Test(lambda: make(3, 1, 4, 0), "single row"),
]
""",
    mutation_check=True,
    hint1="Slices and plain assignment share memory with `X`; make an independent array with `X.copy()` first.",
    hint2="out = X.copy()\nout[i] = 0\nreturn out",
    solution="""
def solve(X, i):
    out = X.copy()
    out[i] = 0
    return out
""",
    explanation="""
`out = X` and basic slices like `X[:]` or `X[1:]` are **views** of the same memory, so writing through them changes `X`. Only `.copy()` (or fancy/boolean indexing) allocates new memory. `np.shares_memory(a, b)` tells you which one you have.
""",
    docs=["https://numpy.org/doc/stable/user/basics.copies.html",
          "https://numpy.org/doc/stable/reference/generated/numpy.ndarray.copy.html"],
    wrong_solutions=[
        dict(code="def solve(X, i):\n    X[i] = 0\n    return X", why="mutates the input"),
        dict(code="def solve(X, i):\n    out = X[:]\n    out[i] = 0\n    return out", why="a slice is a view"),
    ],
),
dict(
    id="np-006",
    title="Recent positive days",
    difficulty="Easy",
    tags=["indexing"],
    signature="def solve(returns: np.ndarray, n: int) -> tuple:",
    statement="""
`returns` is a 1-D array of daily returns, oldest first. Looking only at the **last `n` days**, return a tuple `(count, mean)`:

* `count`: the number of days with a strictly positive return (an int);
* `mean`: the average of those positive returns (a float; `nan` if there are none).
""",
    setup="""
def make(seed, size, n, shift=0.0):
    rng = np.random.default_rng(seed)
    return {"returns": np.round(rng.normal(shift, 0.01, size), 4), "n": n}

EXAMPLE = lambda: {"returns": np.array([0.02, -0.01, 0.005, 0.0, -0.003, 0.012]), "n": 4}
""",
    tests="""
TESTS = [
    lambda: make(1, 30, 10),
    lambda: make(2, 500, 250),
    Test(lambda: make(3, 20, 5, shift=-1.0), "no positive day"),
    Test(lambda: make(4, 12, 12), "n equals the length"),
    Test(lambda: {"returns": np.array([0.0, 0.01, 0.0, -0.02, 0.0]), "n": 5}, "flat days"),
]
""",
    hint1="Take the tail with `returns[-n:]`, then filter with a boolean mask: `x[x > 0]`.",
    hint2="recent = returns[-n:]\npos = recent[recent > 0]\nlen(pos), pos.mean()",
    solution="""
def solve(returns, n):
    recent = returns[-n:]
    pos = recent[recent > 0]
    return len(pos), float(pos.mean()) if len(pos) else float("nan")
""",
    explanation="""
A boolean mask selects the matching elements (and returns a copy). Guard the empty case yourself: `np.mean` of an empty array returns `nan` but also emits a RuntimeWarning. Note that `(x > 0).mean()` is the *share* of positive days, a different statistic.
""",
    docs=["https://numpy.org/doc/stable/user/basics.indexing.html#boolean-array-indexing"],
    wrong_solutions=[
        dict(code="def solve(returns, n):\n    recent = returns[:n]\n    pos = recent[recent > 0]\n    return len(pos), float(pos.mean()) if len(pos) else float('nan')", why="first n days"),
        dict(code="def solve(returns, n):\n    recent = returns[-n:]\n    pos = recent[recent >= 0]\n    return len(pos), float(pos.mean()) if len(pos) else float('nan')", why="counts zeros"),
    ],
),
dict(
    id="np-007",
    title="Probability of the true class",
    difficulty="Medium",
    tags=["indexing"],
    signature="def solve(probs: np.ndarray, labels: np.ndarray) -> np.ndarray:",
    statement="""
`probs` has shape `(n, k)`: one row of predicted class probabilities per sample. `labels` (length `n`) holds each sample's true class (an int in `0..k-1`).

Return the length-`n` array of the probability each sample assigned to its **own** true class.
""",
    setup="""
def make(seed, n, k):
    rng = np.random.default_rng(seed)
    p = rng.dirichlet(np.ones(k), size=n)
    return {"probs": np.round(p, 4), "labels": rng.integers(0, k, n)}

EXAMPLE = lambda: {"probs": np.array([[0.7, 0.2, 0.1], [0.1, 0.1, 0.8], [0.3, 0.6, 0.1]]),
                   "labels": np.array([0, 2, 1])}
""",
    tests="""
TESTS = [
    lambda: make(1, 6, 4),
    lambda: make(2, 1000, 10),
    Test(lambda: make(3, 1, 3), "single sample"),
]
""",
    hint1="Index with two integer arrays at once: rows `np.arange(n)` and columns `labels` (or `np.take_along_axis`).",
    hint2="probs[np.arange(len(labels)), labels]",
    solution="""
def solve(probs, labels):
    return probs[np.arange(len(labels)), labels]
""",
    explanation="""
Two integer arrays index element-wise pairs `(i, labels[i])`. `probs[:, labels]` instead selects whole **columns** and returns an `(n, n)` matrix. This one-liner is the core of every cross-entropy implementation.
""",
    docs=["https://numpy.org/doc/stable/user/basics.indexing.html#integer-array-indexing",
          "https://numpy.org/doc/stable/reference/generated/numpy.take_along_axis.html"],
    wrong_solutions=[
        dict(code="def solve(probs, labels):\n    return probs[:, labels]", why="n x n matrix"),
        dict(code="def solve(probs, labels):\n    return np.take(probs, labels)", why="flat indexing"),
    ],
),
dict(
    id="np-008",
    title="Winsorize at the 1st and 99th percentiles",
    difficulty="Easy",
    tags=["conditional logic", "statistics"],
    signature="def solve(x: np.ndarray) -> np.ndarray:",
    statement="""
Tame outliers in a 1-D float array: compute the 1st and 99th percentiles of `x` (NumPy's default linear interpolation) and cap every value into that range.

Return a float array of the same shape.
""",
    setup="""
def make(seed, n):
    rng = np.random.default_rng(seed)
    return {"x": np.round(rng.standard_t(3, n) * 10, 3)}

EXAMPLE = lambda: make(0, 12)
""",
    tests="""
TESTS = [
    lambda: make(1, 50),
    lambda: make(2, 5000),
    Test(lambda: {"x": np.full(7, 3.5)}, "constant array"),
]
""",
    hint1="`np.percentile(x, [1, 99])` (percents, not fractions), then `np.clip(x, lo, hi)`.",
    hint2="lo, hi = np.percentile(x, [1, 99])\nnp.clip(x, lo, hi)",
    solution="""
def solve(x):
    lo, hi = np.percentile(x, [1, 99])
    return np.clip(x, lo, hi)
""",
    explanation="""
`np.percentile` takes **percents** (0-100) while `np.quantile` takes **fractions** (0-1); mixing them up (`np.percentile(x, [0.01, 0.99])`) clips almost everything to the minimum. `np.clip` is the vectorized `min(max(x, lo), hi)`.
""",
    docs=["https://numpy.org/doc/stable/reference/generated/numpy.percentile.html",
          "https://numpy.org/doc/stable/reference/generated/numpy.clip.html"],
    wrong_solutions=[
        dict(code="def solve(x):\n    lo, hi = np.percentile(x, [0.01, 0.99])\n    return np.clip(x, lo, hi)", why="fractions passed to percentile"),
        dict(code="def solve(x):\n    lo, hi = np.percentile(x, [1, 99])\n    return x[(x >= lo) & (x <= hi)]", why="drops instead of capping"),
    ],
),
dict(
    id="np-009",
    title="Signal from z-scores",
    difficulty="Easy",
    tags=["conditional logic"],
    signature="def solve(z: np.ndarray, t: float) -> np.ndarray:",
    statement="""
Turn z-scores into a trading signal: `+1` where `z > t`, `-1` where `z < -t`, and `0` otherwise, **including where `z` is NaN**.

Return an integer array of the same shape.
""",
    setup="""
def make(seed, n, nan_share=0.1):
    rng = np.random.default_rng(seed)
    z = np.round(rng.normal(0, 1.5, n), 2)
    z[rng.random(n) < nan_share] = np.nan
    return {"z": z, "t": 1.0}

EXAMPLE = lambda: {"z": np.array([2.3, -0.4, -1.7, np.nan, 1.0, 0.9]), "t": 1.0}
""",
    tests="""
TESTS = [
    lambda: make(1, 20),
    lambda: make(2, 500, nan_share=0.3),
    Test(lambda: {"z": np.array([1.0, -1.0, 1.0001]), "t": 1.0}, "values on the threshold"),
]
""",
    compare=dict(check_dtype=True),
    hint1="`np.select([cond1, cond2], [1, -1], default=0)`, or nested `np.where`.",
    hint2="np.select([z > t, z < -t], [1, -1], default=0)",
    solution="""
def solve(z, t):
    return np.select([z > t, z < -t], [1, -1], default=0)
""",
    explanation="""
Comparisons with NaN are always False, so NaN falls through to the default 0. `np.sign(z) * (abs(z) > t)` looks equivalent but keeps NaN (`sign(nan)` is nan) and returns floats. `np.select` evaluates conditions in order, like an if/elif chain.
""",
    docs=["https://numpy.org/doc/stable/reference/generated/numpy.select.html",
          "https://numpy.org/doc/stable/reference/generated/numpy.where.html"],
    wrong_solutions=[
        dict(code="def solve(z, t):\n    return np.sign(z) * (np.abs(z) > t)", why="NaN stays NaN, float dtype"),
        dict(code="def solve(z, t):\n    return np.where(z > t, 1, -1)", why="no neutral band"),
        dict(code="def solve(z, t):\n    return np.select([z >= t, z <= -t], [1, -1], default=0)", why="inclusive threshold"),
    ],
),
dict(
    id="np-010",
    title="Each customer's spend shares",
    difficulty="Medium",
    tags=["broadcasting", "reductions"],
    signature="def solve(X: np.ndarray) -> np.ndarray:",
    statement="""
`X` is a 2-D float array of non-negative spend: one row per customer, one column per product category.

Return an array of the same shape where each value is divided by its **row** total, so every row sums to 1 (the customer's share of spend per category). Rows whose total is 0 must stay all zeros: no NaN and no warning.
""",
    setup="""
def make(seed, n, k, zero_rows=0):
    rng = np.random.default_rng(seed)
    X = np.round(rng.gamma(2.0, 50.0, size=(n, k)), 2)
    X[rng.random((n, k)) < 0.2] = 0.0
    if zero_rows:
        X[rng.choice(n, zero_rows, replace=False)] = 0.0
    return {"X": X}

EXAMPLE = lambda: {"X": np.array([[10.0, 30.0, 60.0], [0.0, 0.0, 0.0], [5.0, 5.0, 0.0]])}
""",
    tests="""
TESTS = [
    lambda: make(1, 6, 4),
    lambda: make(2, 50, 7, zero_rows=3),
    Test(lambda: {"X": np.array([[0.0, 2.5]])}, "single row"),
    Test(lambda: make(4, 200, 1, zero_rows=5), "single column with zero rows"),
]
""",
    hint1="Divide by the row sums kept as a column: `X.sum(axis=1, keepdims=True)`. Guard zero totals with `np.divide(..., where=...)`.",
    hint2="totals = X.sum(axis=1, keepdims=True)\nnp.divide(X, totals, out=np.zeros_like(X, dtype=float), where=totals != 0)",
    solution="""
def solve(X):
    totals = X.sum(axis=1, keepdims=True)
    return np.divide(X, totals, out=np.zeros_like(X, dtype=float), where=totals != 0)
""",
    explanation="""
`keepdims=True` keeps the totals as an `(n, 1)` column, so they broadcast across each row. Without it, `X / X.sum(axis=1)` lines the totals up with the *columns* (wrong values on square inputs, an error otherwise). `np.divide(..., where=...)` skips the zero rows instead of producing NaN plus a RuntimeWarning.
""",
    docs=["https://numpy.org/doc/stable/reference/generated/numpy.sum.html",
          "https://numpy.org/doc/stable/reference/generated/numpy.divide.html",
          "https://numpy.org/doc/stable/user/basics.broadcasting.html"],
    wrong_solutions=[
        dict(code="def solve(X):\n    return X / X.sum(axis=1)", why="no keepdims: broadcasts along the wrong axis"),
        dict(code="def solve(X):\n    return X / X.sum(axis=1, keepdims=True)", why="zero rows become NaN"),
        dict(code="def solve(X):\n    return X / X.sum(axis=0, keepdims=True)", why="column shares instead of row shares"),
    ],
),
dict(
    id="np-011",
    title="Pairwise distances",
    difficulty="Medium",
    tags=["broadcasting"],
    signature="def solve(A: np.ndarray, B: np.ndarray) -> np.ndarray:",
    statement="""
`A` has shape `(n, d)` and `B` has shape `(m, d)`. Return the `(n, m)` matrix of Euclidean distances between every row of `A` and every row of `B`.

There is a large-input test: avoid Python-level loops.
""",
    setup="""
def make(seed, n, m, d):
    rng = np.random.default_rng(seed)
    return {"A": rng.normal(size=(n, d)), "B": rng.normal(size=(m, d))}

EXAMPLE = lambda: {"A": np.array([[0.0, 0.0], [1.0, 1.0]]), "B": np.array([[3.0, 4.0], [0.0, 1.0], [1.0, 1.0]])}
""",
    tests="""
TESTS = [
    lambda: make(1, 4, 3, 2),
    lambda: make(2, 50, 70, 8),
    Test(lambda: make(3, 1, 1, 5), "single points"),
    Test(lambda: make(4, 500, 500, 8), "large input", timed=True),
]
""",
    hint1="Insert axes so the shapes broadcast to `(n, m, d)`: `A[:, None, :] - B[None, :, :]`, then reduce over the last axis.",
    hint2="diff = A[:, None, :] - B[None, :, :]\nnp.sqrt((diff ** 2).sum(axis=-1))",
    solution="""
def solve(A, B):
    diff = A[:, None, :] - B[None, :, :]
    return np.sqrt((diff ** 2).sum(axis=-1))
""",
    explanation="""
`None` (or `np.newaxis`) inserts a length-1 axis; broadcasting then stretches `(n, 1, d)` against `(1, m, d)`. The intermediate is `n*m*d` floats; for big inputs use `||a||^2 + ||b||^2 - 2 a.b` with a matrix product, or `scipy.spatial.distance.cdist`.
""",
    docs=["https://numpy.org/doc/stable/user/basics.broadcasting.html",
          "https://numpy.org/doc/stable/reference/generated/numpy.linalg.norm.html"],
    wrong_solutions=[
        dict(code="""
def solve(A, B):
    out = np.empty((len(A), len(B)))
    for i in range(len(A)):
        for j in range(len(B)):
            out[i, j] = np.sqrt(((A[i] - B[j]) ** 2).sum())
    return out
""", why="Python double loop: too slow"),
        dict(code="def solve(A, B):\n    diff = A[:, None, :] - B[None, :, :]\n    return (diff ** 2).sum(axis=-1)", why="squared distances"),
    ],
),
dict(
    id="np-012",
    title="Top-k indices",
    difficulty="Easy",
    tags=["sorting & ranking"],
    signature="def solve(scores: np.ndarray, k: int) -> np.ndarray:",
    statement="""
Return the indices of the `k` largest values in `scores` (1-D, no NaN), ordered from the largest value to the smallest. **Ties are broken by the lower index first.**
""",
    setup="""
def make(seed, n, k, ties=False):
    rng = np.random.default_rng(seed)
    s = rng.integers(0, 6, n).astype(float) if ties else np.round(rng.normal(size=n), 4)
    return {"scores": s, "k": k}

EXAMPLE = lambda: {"scores": np.array([0.2, 0.9, 0.5, 0.9, 0.1]), "k": 3}
""",
    tests="""
TESTS = [
    lambda: make(1, 20, 5),
    Test(lambda: make(2, 50, 10, ties=True), "many ties"),
    Test(lambda: make(3, 7, 7, ties=True), "k equals n"),
    lambda: make(4, 1000, 1),
]
""",
    hint1="`np.argsort` sorts ascending: sort the negated scores with `kind='stable'` (keeps tied elements in index order), then take the first `k`.",
    hint2="np.argsort(-scores, kind='stable')[:k]",
    solution="""
def solve(scores, k):
    return np.argsort(-scores, kind="stable")[:k]
""",
    explanation="""
`np.argsort(x)[::-1][:k]` reverses the tie order too (higher index first). Negating and sorting with a stable sort keeps the tie rule. For huge arrays where order doesn't matter, `np.argpartition(-x, k)[:k]` is O(n).
""",
    docs=["https://numpy.org/doc/stable/reference/generated/numpy.argsort.html",
          "https://numpy.org/doc/stable/reference/generated/numpy.argpartition.html"],
    wrong_solutions=[
        dict(code="def solve(scores, k):\n    return np.argsort(scores)[::-1][:k]", why="ties come out highest index first"),
        dict(code="def solve(scores, k):\n    return np.argsort(scores)[-k:]", why="ascending order"),
    ],
),
dict(
    id="np-013",
    title="Which tax bracket?",
    difficulty="Medium",
    tags=["binning"],
    signature="def solve(x: np.ndarray, edges: np.ndarray) -> np.ndarray:",
    statement="""
`edges` holds sorted bracket boundaries `e0 < e1 < ... < em`. Bracket `j` covers the **left-closed** interval `[e_j, e_{j+1})`.

For each value in `x`, return its bracket index `0..m-1`; values below `e0` get `-1` and values `>= em` get `m`. Return an integer array.
""",
    setup="""
def make(seed, n, edges):
    rng = np.random.default_rng(seed)
    x = np.round(rng.uniform(edges[0] - 5000, edges[-1] + 5000, n), -2)
    x[: len(edges)] = edges        # exact boundary values
    return {"x": x, "edges": np.array(edges, dtype=float)}

EXAMPLE = lambda: {"x": np.array([5000.0, 10000.0, 39999.0, 40000.0, 250000.0]),
                   "edges": np.array([10000.0, 40000.0, 100000.0])}
""",
    tests="""
TESTS = [
    lambda: make(1, 30, [12570, 50270, 125140]),
    lambda: make(2, 1000, [0, 10000, 25000, 50000, 100000, 200000]),
    Test(lambda: {"x": np.array([1.0, 2.0, 3.0]), "edges": np.array([2.0])}, "single edge"),
]
""",
    hint1="`np.digitize(x, edges)` (or `np.searchsorted(edges, x, side='right')`) returns how many edges are <= x; subtract 1.",
    hint2="np.digitize(x, edges) - 1",
    solution="""
def solve(x, edges):
    return np.digitize(x, edges) - 1
""",
    explanation="""
`digitize(x, bins)` returns `i` with `bins[i-1] <= x < bins[i]` (left-closed by default; `right=True` flips it). `searchsorted(edges, x, side='right')` is the same thing from the other direction. Off-by-one on the boundaries is the classic bug, so test exact edge values.
""",
    docs=["https://numpy.org/doc/stable/reference/generated/numpy.digitize.html",
          "https://numpy.org/doc/stable/reference/generated/numpy.searchsorted.html"],
    wrong_solutions=[
        dict(code="def solve(x, edges):\n    return np.digitize(x, edges, right=True) - 1", why="right-closed brackets"),
        dict(code="def solve(x, edges):\n    return np.searchsorted(edges, x) - 1", why="side='left'"),
    ],
),
dict(
    id="np-014",
    title="Daily sign-ups from a cumulative counter",
    difficulty="Easy",
    tags=["cumulative ops"],
    signature="def solve(cum: np.ndarray) -> np.ndarray:",
    statement="""
A dashboard exports **cumulative** sign-ups per day (`cum`, non-decreasing integers). Return the number of new sign-ups each day: an array of the same length as `cum`, where day 0's value is `cum[0]`.
""",
    setup="""
def make(seed, n):
    rng = np.random.default_rng(seed)
    return {"cum": np.cumsum(rng.poisson(20, n))}

EXAMPLE = lambda: {"cum": np.array([5, 12, 12, 30])}
""",
    tests="""
TESTS = [
    lambda: make(1, 10),
    lambda: make(2, 365),
    Test(lambda: {"cum": np.array([7])}, "single day"),
]
""",
    hint1="`np.diff` with `prepend=0` keeps the original length.",
    hint2="np.diff(cum, prepend=0)",
    solution="""
def solve(cum):
    return np.diff(cum, prepend=0)
""",
    explanation="""
`np.diff` returns `n - 1` values; `prepend=0` (or `np.concatenate([[cum[0]], np.diff(cum)])`) restores the first day. `np.cumsum` is the inverse: `np.cumsum(np.diff(c, prepend=0))` gives back `c`.
""",
    docs=["https://numpy.org/doc/stable/reference/generated/numpy.diff.html",
          "https://numpy.org/doc/stable/reference/generated/numpy.cumsum.html"],
    wrong_solutions=[
        dict(code="def solve(cum):\n    return np.diff(cum)", why="one element short"),
        dict(code="def solve(cum):\n    return np.diff(cum, append=0)", why="appends instead of prepends"),
    ],
),
dict(
    id="np-015",
    title="Most frequent label",
    difficulty="Easy",
    tags=["set operations"],
    signature="def solve(labels: np.ndarray) -> tuple:",
    statement="""
Return the most frequent value in the integer array `labels` and how often it occurs, as a tuple `(value, count)`. If several values tie, return the **smallest** of them. Labels can be negative.
""",
    setup="""
def make(seed, n, lo, hi):
    rng = np.random.default_rng(seed)
    return {"labels": rng.integers(lo, hi, n)}

EXAMPLE = lambda: {"labels": np.array([3, 1, 3, 2, 1, 1, 3])}
""",
    tests="""
TESTS = [
    lambda: make(1, 50, 0, 5),
    Test(lambda: make(2, 300, -10, 10), "negative labels"),
    Test(lambda: {"labels": np.array([4, -2, 4, -2])}, "tie"),
    Test(lambda: {"labels": np.array([9])}, "single element"),
]
""",
    hint1="`np.unique(labels, return_counts=True)`, then `counts.argmax()` (the first maximum, i.e. the smallest value, because `unique` sorts).",
    hint2="vals, counts = np.unique(labels, return_counts=True)\ni = counts.argmax()\nvals[i], counts[i]",
    solution="""
def solve(labels):
    vals, counts = np.unique(labels, return_counts=True)
    i = counts.argmax()
    return int(vals[i]), int(counts[i])
""",
    explanation="""
`np.unique` returns sorted unique values, and `argmax` returns the first maximum, so ties resolve to the smallest value for free. `np.bincount` is faster but only works for non-negative ints. In pandas, `s.value_counts()` does the same, sorted by count.
""",
    docs=["https://numpy.org/doc/stable/reference/generated/numpy.unique.html"],
    wrong_solutions=[
        dict(code="def solve(labels):\n    c = np.bincount(labels)\n    return int(c.argmax()), int(c.max())", why="fails on negative labels"),
        dict(code="def solve(labels):\n    vals, counts = np.unique(labels, return_counts=True)\n    return int(counts.argmax()), int(counts.max())", why="returns the position, not the value"),
    ],
),
dict(
    id="np-016",
    title="Bootstrap the mean",
    difficulty="Medium",
    allow_in_statement=["default_rng"],
    tags=["random sampling", "statistics"],
    signature="def solve(x: np.ndarray, n_boot: int, seed: int) -> np.ndarray:",
    statement="""
Approximate the sampling distribution of the mean by bootstrap: using a generator created with `np.random.default_rng(seed)`, draw `n_boot` resamples of `x` **with replacement**, each the same size as `x`, and return the array of the `n_boot` resample means.

Vectorize: draw all resamples in one call (no Python loop over resamples).
""",
    setup="""
def make(seed, n, n_boot, data_seed):
    rng = np.random.default_rng(data_seed)
    return {"x": np.round(rng.lognormal(3, 0.8, n), 2), "n_boot": n_boot, "seed": seed}

EXAMPLE = lambda: {"x": np.array([12.0, 15.5, 9.0, 30.0, 11.0]), "n_boot": 2000, "seed": 0}
""",
    tests="""
TESTS = [
    lambda: make(1, 40, 2000, 11),
    lambda: make(2, 400, 3000, 12),
    Test(lambda: make(3, 15, 5000, 13), "small sample"),
]

def check(got, exp, inputs):
    x, B = inputs["x"], inputs["n_boot"]
    if not isinstance(got, np.ndarray) or got.shape != (B,):
        fail(f"expected an array of shape ({B},), got {type(got).__name__} {getattr(got, 'shape', '')}")
    if got.min() < x.min() - 1e-9 or got.max() > x.max() + 1e-9:
        fail("resample means fall outside [min(x), max(x)]")
    if B < 500:
        return None
    se = x.std() / np.sqrt(len(x))
    if abs(got.mean() - x.mean()) > 4 * se / np.sqrt(B) + 1e-9:
        fail(f"mean of the bootstrap means {got.mean():.4f} is far from mean(x) = {x.mean():.4f}")
    if not (0.85 * se < got.std() < 1.15 * se):
        fail(f"spread of the bootstrap means {got.std():.4f} should be close to std(x)/sqrt(n) = {se:.4f}: "
             "are you resampling with replacement, with the size of x?")
""",
    hint1="`rng = np.random.default_rng(seed)`; draw a `(n_boot, len(x))` matrix with `rng.choice(x, size=..., replace=True)` (or random indices with `rng.integers`) and average along axis 1.",
    hint2="rng = np.random.default_rng(seed)\nrng.choice(x, size=(n_boot, len(x)), replace=True).mean(axis=1)",
    solution="""
def solve(x, n_boot, seed):
    rng = np.random.default_rng(seed)
    return rng.choice(x, size=(n_boot, len(x)), replace=True).mean(axis=1)
""",
    explanation="""
Use a local `Generator` (`default_rng(seed)`), not the legacy global `np.random.seed`; it is reproducible and doesn't leak state between functions. Drawing an `(n_boot, n)` matrix in one call is much faster than looping. The std of the bootstrap means approximates the standard error `std(x)/sqrt(n)`. (Tests check these statistical properties, so any correct resampling scheme passes.)
""",
    docs=["https://numpy.org/doc/stable/reference/random/generator.html#numpy.random.default_rng",
          "https://numpy.org/doc/stable/reference/random/generated/numpy.random.Generator.choice.html"],
    wrong_solutions=[
        dict(code="def solve(x, n_boot, seed):\n    rng = np.random.default_rng(seed)\n    return np.array([rng.permutation(x).mean() for _ in range(n_boot)])", why="without replacement: no spread"),
        dict(code="def solve(x, n_boot, seed):\n    rng = np.random.default_rng(seed)\n    return rng.choice(x, size=(n_boot, 5), replace=True).mean(axis=1)", why="wrong resample size"),
    ],
),
dict(
    id="np-017",
    title="Shuffled train/test indices",
    difficulty="Easy",
    allow_in_statement=["default_rng", "round"],
    tags=["random sampling"],
    signature="def solve(n: int, test_frac: float, seed: int) -> tuple:",
    statement="""
Shuffle the row indices `0..n-1` with a generator created by `np.random.default_rng(seed)`, then split them: the first `round(n * test_frac)` shuffled indices form the **test** set and the rest the **training** set.

Return `(train_idx, test_idx)`, two integer arrays.
""",
    setup="""
EXAMPLE = lambda: {"n": 10, "test_frac": 0.3, "seed": 0}
""",
    tests="""
TESTS = [
    lambda: {"n": 100, "test_frac": 0.2, "seed": 1},
    Test(lambda: {"n": 9, "test_frac": 0.3, "seed": 2}, "round, not truncate"),
    lambda: {"n": 1000, "test_frac": 0.25, "seed": 3},
]

def check(got, exp, inputs):
    n, f = inputs["n"], inputs["test_frac"]
    if not isinstance(got, (tuple, list)) or len(got) != 2:
        fail("return a tuple (train_idx, test_idx)")
    tr, te = (np.asarray(a) for a in got)
    if te.dtype.kind not in "iu" or tr.dtype.kind not in "iu":
        fail("indices must be integer arrays")
    if len(te) != round(n * f):
        fail(f"test size should be round({n} * {f}) = {round(n * f)}, got {len(te)}")
    if len(tr) + len(te) != n or set(tr.tolist()) | set(te.tolist()) != set(range(n)):
        fail("train and test together must contain every index 0..n-1 exactly once")
    if set(tr.tolist()) & set(te.tolist()):
        fail("train and test overlap")
    if n >= 10 and np.array_equal(np.concatenate([te, tr]), np.arange(n)):
        fail("indices are not shuffled")
""",
    hint1="`rng = np.random.default_rng(seed)`, `idx = rng.permutation(n)`, then slice at `round(n * test_frac)`.",
    hint2="idx = np.random.default_rng(seed).permutation(n)\nk = round(n * test_frac)\nidx[k:], idx[:k]",
    solution="""
def solve(n, test_frac, seed):
    idx = np.random.default_rng(seed).permutation(n)
    k = round(n * test_frac)
    return idx[k:], idx[:k]
""",
    explanation="""
`rng.permutation(n)` returns a shuffled `arange(n)` (`rng.shuffle` shuffles in place and returns None). This is what `train_test_split` does under the hood. Pass the seed so the split is reproducible.
""",
    docs=["https://numpy.org/doc/stable/reference/random/generated/numpy.random.Generator.permutation.html"],
    wrong_solutions=[
        dict(code="def solve(n, test_frac, seed):\n    idx = np.arange(n)\n    k = round(n * test_frac)\n    return idx[k:], idx[:k]", why="not shuffled"),
        dict(code="def solve(n, test_frac, seed):\n    idx = np.random.default_rng(seed).permutation(n)\n    k = int(n * test_frac)\n    return idx[k:], idx[:k]", why="truncates instead of rounding"),
    ],
),
dict(
    id="np-018",
    title="Interquartile range with missing readings",
    difficulty="Medium",
    tags=["missing data", "statistics"],
    signature="def solve(X: np.ndarray) -> np.ndarray:",
    statement="""
`X` has shape `(n, k)`: sensor readings with NaN where a reading is missing (every column has at least one value).

Return the interquartile range (75th minus 25th percentile, NumPy's default linear method) of each **column**, ignoring NaNs: a float array of length `k`.
""",
    setup="""
def make(seed, n, k, nan_share):
    rng = np.random.default_rng(seed)
    X = np.round(rng.normal(20, 5, (n, k)), 2)
    X[rng.random((n, k)) < nan_share] = np.nan
    X[0] = np.round(rng.normal(20, 5, k), 2)       # every column keeps a value
    return {"X": X}

EXAMPLE = lambda: {"X": np.array([[1.0, 10.0], [2.0, np.nan], [3.0, 30.0], [np.nan, 20.0], [5.0, 50.0]])}
""",
    tests="""
TESTS = [
    lambda: make(1, 20, 3, 0.1),
    lambda: make(2, 500, 8, 0.4),
    Test(lambda: make(3, 1, 4, 0.0), "single row"),
]
""",
    hint1="`np.nanpercentile(X, [25, 75], axis=0)` returns a `(2, k)` array.",
    hint2="q25, q75 = np.nanpercentile(X, [25, 75], axis=0)\nq75 - q25",
    solution="""
def solve(X):
    q25, q75 = np.nanpercentile(X, [25, 75], axis=0)
    return q75 - q25
""",
    explanation="""
The `nan*` family (`nanmean`, `nanmedian`, `nanpercentile`, `nanstd`...) skips missing values; the plain versions propagate NaN. `axis=0` reduces down the rows, giving one value per column. A column that is entirely NaN gives NaN plus a RuntimeWarning.
""",
    docs=["https://numpy.org/doc/stable/reference/generated/numpy.nanpercentile.html"],
    wrong_solutions=[
        dict(code="def solve(X):\n    q25, q75 = np.percentile(X, [25, 75], axis=0)\n    return q75 - q25", why="NaN propagates"),
        dict(code="def solve(X):\n    q25, q75 = np.nanpercentile(X, [25, 75], axis=1)\n    return q75 - q25", why="per row"),
    ],
),
dict(
    id="np-019",
    title="One-hot encode labels",
    difficulty="Easy",
    tags=["encoding"],
    signature="def solve(y: np.ndarray, k: int) -> np.ndarray:",
    statement="""
Return the `(n, k)` one-hot encoding of the integer labels `y` (values in `0..k-1`) as a **float** array: row `i` has `1.0` in column `y[i]` and zeros elsewhere. Some classes may not appear in `y`, but the output still has `k` columns.
""",
    setup="""
def make(seed, n, k, hi=None):
    rng = np.random.default_rng(seed)
    return {"y": rng.integers(0, hi or k, n), "k": k}

EXAMPLE = lambda: {"y": np.array([2, 0, 1, 2]), "k": 3}
""",
    tests="""
TESTS = [
    lambda: make(1, 10, 4),
    Test(lambda: make(2, 50, 10, hi=6), "top classes absent"),
    Test(lambda: {"y": np.array([0]), "k": 1}, "single label"),
]
""",
    compare=dict(check_dtype=True),
    hint1="Index the rows of an identity matrix: `np.eye(k)[y]`.",
    hint2="np.eye(k)[y]",
    solution="""
def solve(y, k):
    return np.eye(k)[y]
""",
    explanation="""
Row `j` of `np.eye(k)` is the one-hot vector for class `j`, so fancy-indexing with `y` builds the whole matrix at once. Take `k` from the problem, not from `y.max() + 1`: classes missing from a batch would shrink the width. In ML code use `OneHotEncoder` or `pd.get_dummies` for categorical *features*.
""",
    docs=["https://numpy.org/doc/stable/reference/generated/numpy.eye.html"],
    wrong_solutions=[
        dict(code="def solve(y, k):\n    return np.eye(y.max() + 1)[y]", why="width from the data"),
        dict(code="def solve(y, k):\n    return (y[:, None] == np.arange(k))", why="bool, not float"),
    ],
),
dict(
    id="np-020",
    title="Moving average with sliding windows",
    difficulty="Medium",
    tags=["window functions"],
    signature="def solve(x: np.ndarray, w: int) -> np.ndarray:",
    statement="""
Return the moving average of the 1-D array `x` over windows of length `w`: element `i` is the mean of `x[i : i + w]`, so the result has length `len(x) - w + 1`. No Python loops.
""",
    setup="""
def make(seed, n, w):
    rng = np.random.default_rng(seed)
    return {"x": np.round(np.cumsum(rng.normal(0, 1, n)), 3), "w": w}

EXAMPLE = lambda: {"x": np.array([1.0, 2.0, 3.0, 4.0, 10.0]), "w": 3}
""",
    tests="""
TESTS = [
    lambda: make(1, 20, 4),
    lambda: make(2, 5000, 50),
    Test(lambda: make(3, 6, 6), "window = length"),
    Test(lambda: make(4, 8, 1), "window of 1"),
]
""",
    hint1="`np.lib.stride_tricks.sliding_window_view(x, w)` gives an `(n - w + 1, w)` view; average along axis 1.",
    hint2="from numpy.lib.stride_tricks import sliding_window_view\nsliding_window_view(x, w).mean(axis=1)",
    solution="""
from numpy.lib.stride_tricks import sliding_window_view

def solve(x, w):
    return sliding_window_view(x, w).mean(axis=1)
""",
    explanation="""
`sliding_window_view` builds the windows as a strided **view** (no copy), so any reduction (`mean`, `std`, `max`...) along axis 1 becomes a rolling statistic. For means, `np.convolve(x, np.ones(w) / w, mode='valid')` also works. In pandas you'd write `s.rolling(w).mean()`.
""",
    docs=["https://numpy.org/doc/stable/reference/generated/numpy.lib.stride_tricks.sliding_window_view.html",
          "https://numpy.org/doc/stable/reference/generated/numpy.convolve.html"],
    wrong_solutions=[
        dict(code="def solve(x, w):\n    return np.convolve(x, np.ones(w) / w, mode='same')", why="same length, edge windows wrong"),
        dict(code="def solve(x, w):\n    c = np.cumsum(x)\n    return (c[w:] - c[:-w]) / w", why="off by one"),
    ],
),
dict(
    id="np-021",
    title="Tangency portfolio weights",
    difficulty="Medium",
    tags=["linear algebra"],
    signature="def solve(mu: np.ndarray, cov: np.ndarray) -> np.ndarray:",
    statement="""
Given expected excess returns `mu` (length `k`) and their covariance matrix `cov` (`k x k`), the tangency (max-Sharpe) portfolio weights are proportional to `cov^-1 mu`.

Compute that vector by solving the linear system (rather than inverting the matrix), then rescale it so the weights sum to 1. Return a float array of length `k`.
""",
    setup="""
def make(seed, k):
    rng = np.random.default_rng(seed)
    A = rng.normal(size=(k, k)) * 0.05
    cov = A @ A.T + np.eye(k) * 0.01
    mu = np.abs(rng.normal(0.05, 0.03, k))
    return {"mu": mu, "cov": cov}

EXAMPLE = lambda: {"mu": np.array([0.05, 0.08]), "cov": np.array([[0.04, 0.006], [0.006, 0.09]])}
""",
    tests="""
TESTS = [
    lambda: make(1, 3),
    lambda: make(2, 30),
    Test(lambda: {"mu": np.array([0.07]), "cov": np.array([[0.02]])}, "single asset"),
]
""",
    hint1="`np.linalg.solve(cov, mu)` solves `cov @ w = mu`; divide by the sum.",
    hint2="w = np.linalg.solve(cov, mu)\nw / w.sum()",
    solution="""
def solve(mu, cov):
    w = np.linalg.solve(cov, mu)
    return w / w.sum()
""",
    explanation="""
`np.linalg.solve(A, b)` is faster and numerically more stable than `np.linalg.inv(A) @ b`: you almost never need the inverse itself. For an ill-conditioned covariance, shrink it (Ledoit-Wolf) or use `lstsq`/`pinv`.
""",
    docs=["https://numpy.org/doc/stable/reference/generated/numpy.linalg.solve.html"],
    wrong_solutions=[
        dict(code="def solve(mu, cov):\n    w = cov @ mu\n    return w / w.sum()", why="multiplies instead of solving"),
        dict(code="def solve(mu, cov):\n    return np.linalg.solve(cov, mu)", why="not normalized"),
    ],
),
dict(
    id="np-022",
    title="OLS coefficients with an intercept",
    difficulty="Medium",
    tags=["linear algebra"],
    signature="def solve(X: np.ndarray, y: np.ndarray) -> np.ndarray:",
    statement="""
`X` has shape `(n, k)` (features) and `y` length `n`. Fit ordinary least squares of `y` on the columns of `X` **plus an intercept**.

Return the coefficient vector of length `k + 1`, **intercept first**.
""",
    setup="""
def make(seed, n, k):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, k))
    beta = rng.normal(0, 2, k)
    y = 1.5 + X @ beta + rng.normal(0, 0.5, n)
    return {"X": X, "y": y}

EXAMPLE = lambda: {"X": np.array([[1.0], [2.0], [3.0], [4.0]]), "y": np.array([3.1, 4.9, 7.2, 8.8])}
""",
    tests="""
TESTS = [
    lambda: make(1, 30, 2),
    lambda: make(2, 1000, 6),
    Test(lambda: make(3, 5, 4), "barely more rows than columns"),
]
""",
    hint1="Prepend a column of ones with `np.column_stack`, then `np.linalg.lstsq(A, y, rcond=None)[0]`.",
    hint2="A = np.column_stack([np.ones(len(X)), X])\nnp.linalg.lstsq(A, y, rcond=None)[0]",
    solution="""
def solve(X, y):
    A = np.column_stack([np.ones(len(X)), X])
    return np.linalg.lstsq(A, y, rcond=None)[0]
""",
    explanation="""
`lstsq` solves the least-squares problem with an SVD, which is safer than the textbook normal equations `inv(X.T @ X) @ X.T @ y`. It returns a tuple `(coef, residuals, rank, singular_values)`, so take `[0]`. Without the column of ones the line is forced through the origin.
""",
    docs=["https://numpy.org/doc/stable/reference/generated/numpy.linalg.lstsq.html",
          "https://numpy.org/doc/stable/reference/generated/numpy.column_stack.html"],
    wrong_solutions=[
        dict(code="def solve(X, y):\n    return np.linalg.lstsq(X, y, rcond=None)[0]", why="no intercept"),
        dict(code="def solve(X, y):\n    A = np.column_stack([X, np.ones(len(X))])\n    return np.linalg.lstsq(A, y, rcond=None)[0]", why="intercept last"),
    ],
),
dict(
    id="np-023",
    title="Cosine similarity matrix",
    difficulty="Medium",
    tags=["linear algebra", "broadcasting"],
    signature="def solve(E: np.ndarray) -> np.ndarray:",
    statement="""
`E` has shape `(n, d)`: one embedding vector per row (no all-zero rows). Return the `(n, n)` matrix of cosine similarities between every pair of rows.
""",
    setup="""
def make(seed, n, d):
    rng = np.random.default_rng(seed)
    return {"E": rng.normal(size=(n, d)) * rng.uniform(0.5, 5, (n, 1))}

EXAMPLE = lambda: {"E": np.array([[1.0, 0.0], [1.0, 1.0], [0.0, 3.0]])}
""",
    tests="""
TESTS = [
    lambda: make(1, 5, 4),
    lambda: make(2, 300, 32),
    Test(lambda: make(3, 1, 8), "single vector"),
]
""",
    hint1="Scale rows to unit length with `np.linalg.norm(E, axis=1, keepdims=True)`, then take `U @ U.T`.",
    hint2="U = E / np.linalg.norm(E, axis=1, keepdims=True)\nU @ U.T",
    solution="""
def solve(E):
    U = E / np.linalg.norm(E, axis=1, keepdims=True)
    return U @ U.T
""",
    explanation="""
Cosine similarity is the dot product of unit vectors, so normalize once and use a single matrix product instead of `n^2` pairwise computations. `keepdims=True` makes the norms an `(n, 1)` column that divides each row.
""",
    docs=["https://numpy.org/doc/stable/reference/generated/numpy.linalg.norm.html",
          "https://numpy.org/doc/stable/reference/generated/numpy.matmul.html"],
    wrong_solutions=[
        dict(code="def solve(E):\n    return E @ E.T", why="dot products, not cosines"),
        dict(code="def solve(E):\n    U = E / np.linalg.norm(E, axis=0, keepdims=True)\n    return U @ U.T", why="normalizes columns"),
    ],
),
dict(
    id="np-024",
    title="Variance explained by the first factor",
    difficulty="Medium",
    tags=["linear algebra"],
    signature="def solve(cov: np.ndarray) -> float:",
    statement="""
`cov` is the covariance matrix of a set of asset returns (symmetric, positive semi-definite). Return the share of total variance explained by its **largest** eigenvalue (the largest eigenvalue divided by the sum of all eigenvalues), as a float.
""",
    setup="""
def make(seed, k, beta_scale=1.0):
    rng = np.random.default_rng(seed)
    beta = rng.uniform(0.5, 1.5, k) * beta_scale
    cov = np.outer(beta, beta) * 0.0002 + np.diag(rng.uniform(0.0001, 0.0006, k))
    return {"cov": cov}

EXAMPLE = lambda: {"cov": np.array([[2.0, 1.0], [1.0, 2.0]])}
""",
    tests="""
TESTS = [
    lambda: make(1, 5),
    lambda: make(2, 50),
    Test(lambda: make(3, 12, beta_scale=0.1), "weak common factor"),
]
""",
    hint1="`np.linalg.eigvalsh(cov)` (for symmetric matrices) returns eigenvalues in **ascending** order.",
    hint2="w = np.linalg.eigvalsh(cov)\nw[-1] / w.sum()",
    solution="""
def solve(cov):
    w = np.linalg.eigvalsh(cov)
    return float(w[-1] / w.sum())
""",
    explanation="""
For symmetric matrices, use `eigh`/`eigvalsh`: real eigenvalues, sorted ascending, faster and more stable than the general `eig` (whose output order is unspecified). The sum of the eigenvalues equals the trace, i.e. the total variance. This is PCA's explained-variance ratio for the first component.
""",
    docs=["https://numpy.org/doc/stable/reference/generated/numpy.linalg.eigvalsh.html",
          "https://numpy.org/doc/stable/reference/generated/numpy.linalg.eigh.html"],
    wrong_solutions=[
        dict(code="def solve(cov):\n    w = np.linalg.eigvalsh(cov)\n    return float(w[0] / w.sum())", why="eigvalsh is ascending"),
        dict(code="def solve(cov):\n    return float(np.diag(cov).max() / np.trace(cov))", why="largest variance, not eigenvalue"),
    ],
),
dict(
    id="np-025",
    title="Many portfolio variances at once",
    difficulty="Hard",
    tags=["linear algebra"],
    signature="def solve(W: np.ndarray, cov: np.ndarray) -> np.ndarray:",
    statement="""
`W` has shape `(p, k)`: `p` candidate portfolios, one weight vector per row. `cov` is the `k x k` covariance matrix. Return the length-`p` array of portfolio variances `w . cov . w`, one per row.

`p` can be large: avoid Python loops, and don't build the `p x p` matrix `W cov W^T` just to keep its diagonal.
""",
    setup="""
def make(seed, p, k):
    rng = np.random.default_rng(seed)
    A = rng.normal(size=(k, k)) * 0.1
    W = rng.dirichlet(np.ones(k), size=p)
    return {"W": W, "cov": A @ A.T}

EXAMPLE = lambda: {"W": np.array([[0.5, 0.5], [1.0, 0.0], [0.2, 0.8]]),
                   "cov": np.array([[0.04, 0.01], [0.01, 0.09]])}
""",
    tests="""
TESTS = [
    lambda: make(1, 10, 4),
    lambda: make(2, 200, 25),
    Test(lambda: make(3, 1, 3), "single portfolio"),
    Test(lambda: make(4, 4000, 10), "many portfolios"),
]
""",
    hint1="`np.einsum('pi,ij,pj->p', W, cov, W)`, or row-wise `((W @ cov) * W).sum(axis=1)`.",
    hint2="np.einsum('pi,ij,pj->p', W, cov, W)",
    solution="""
def solve(W, cov):
    return np.einsum("pi,ij,pj->p", W, cov, W)
""",
    explanation="""
`einsum` spells out the index contraction: repeated letters are summed, and the output keeps `p`. The `np.diag(W @ cov @ W.T)` version computes `p^2` numbers to keep `p` of them (O(p^2) memory). `((W @ cov) * W).sum(1)` is the same contraction in plain operators.
""",
    docs=["https://numpy.org/doc/stable/reference/generated/numpy.einsum.html"],
    wrong_solutions=[
        dict(code="def solve(W, cov):\n    return (W @ cov @ W.T).sum(axis=1)", why="sums rows of the p x p matrix instead of taking its diagonal"),
        dict(code="def solve(W, cov):\n    return np.einsum('pi,ij,pj->p', W, cov, W) ** 0.5", why="volatility, not variance"),
    ],
),
dict(
    id="np-026",
    title="Correlation matrix from scratch",
    difficulty="Medium",
    tags=["statistics", "broadcasting"],
    signature="def solve(X: np.ndarray) -> np.ndarray:",
    statement="""
`X` has shape `(n, k)`: `n` observations of `k` variables (no NaN, no constant column). Compute the `k x k` Pearson correlation matrix using only array arithmetic (no library correlation function): standardize every column, then average the products.
""",
    setup="""
def make(seed, n, k):
    rng = np.random.default_rng(seed)
    L = rng.normal(size=(k, k))
    return {"X": rng.normal(size=(n, k)) @ L + rng.uniform(-5, 5, k)}

EXAMPLE = lambda: {"X": np.array([[1.0, 2.0, 0.5], [2.0, 4.1, 0.1], [3.0, 6.2, 0.9], [4.0, 7.9, 0.3]])}
""",
    tests="""
TESTS = [
    lambda: make(1, 20, 3),
    lambda: make(2, 2000, 12),
    Test(lambda: make(3, 3, 2), "three observations"),
]
""",
    hint1="Standardize columns with `X.mean(axis=0)` and `X.std(axis=0)` (ddof=0), then `Z.T @ Z / n`.",
    hint2="Z = (X - X.mean(axis=0)) / X.std(axis=0)\nZ.T @ Z / len(X)",
    solution="""
def solve(X):
    Z = (X - X.mean(axis=0)) / X.std(axis=0)
    return Z.T @ Z / len(X)
""",
    explanation="""
Correlation is the covariance of standardized variables. Keep `ddof` consistent: population std (ddof=0) pairs with dividing by `n`, sample std (ddof=1) with `n - 1`; mixing them scales the result by `n/(n-1)`. Check against `np.corrcoef(X, rowvar=False)`, where `rowvar=False` means the variables are columns.
""",
    docs=["https://numpy.org/doc/stable/reference/generated/numpy.std.html",
          "https://numpy.org/doc/stable/reference/generated/numpy.corrcoef.html"],
    wrong_solutions=[
        dict(code="def solve(X):\n    Z = (X - X.mean(axis=0)) / X.std(axis=0, ddof=1)\n    return Z.T @ Z / len(X)", why="mixes ddof=1 with /n"),
        dict(code="def solve(X):\n    Z = (X - X.mean(axis=0)) / X.std(axis=0)\n    return Z @ Z.T / len(X)", why="n x n instead of k x k"),
    ],
),
dict(
    id="np-027",
    title="Numerically stable softmax",
    difficulty="Medium",
    tags=["ML from scratch"],
    signature="def solve(logits: np.ndarray) -> np.ndarray:",
    statement="""
`logits` has shape `(n, k)`. Return the row-wise softmax probabilities (each row sums to 1).

Logits can be huge in either direction (e.g. `1000` or `-1000`): the result must contain no NaN or inf.
""",
    setup="""
def make(seed, n, k, scale=3.0):
    rng = np.random.default_rng(seed)
    return {"logits": rng.normal(0, scale, (n, k))}

EXAMPLE = lambda: {"logits": np.array([[1.0, 2.0, 3.0], [1000.0, 1001.0, 1002.0]])}
""",
    tests="""
TESTS = [
    lambda: make(1, 5, 4),
    Test(lambda: {"logits": np.vstack([make(2, 3, 6)["logits"] + 900, make(3, 3, 6)["logits"] - 900])}, "huge positive and negative rows"),
    lambda: make(4, 1000, 10, scale=50.0),
]
""",
    hint1="Subtract each row's max (`logits.max(axis=1, keepdims=True)`) before `np.exp`; softmax is unchanged by that shift.",
    hint2="z = logits - logits.max(axis=1, keepdims=True)\ne = np.exp(z)\ne / e.sum(axis=1, keepdims=True)",
    solution="""
def solve(logits):
    z = logits - logits.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)
""",
    explanation="""
`exp(1000)` overflows to inf and inf/inf is NaN. Since softmax(x) = softmax(x - c), subtracting the **per-row** max makes the largest exponent `exp(0) = 1`. Subtracting a single global max is not enough when rows differ wildly: whole rows underflow to 0/0.
""",
    docs=["https://numpy.org/doc/stable/reference/generated/numpy.exp.html",
          "https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.softmax.html"],
    wrong_solutions=[
        dict(code="def solve(logits):\n    e = np.exp(logits)\n    return e / e.sum(axis=1, keepdims=True)", why="overflows"),
        dict(code="def solve(logits):\n    e = np.exp(logits - logits.max())\n    return e / e.sum(axis=1, keepdims=True)", why="global max: rows underflow"),
        dict(code="def solve(logits):\n    z = logits - logits.max(axis=1, keepdims=True)\n    e = np.exp(z)\n    return e / e.sum(axis=0, keepdims=True)", why="normalizes columns"),
    ],
),
dict(
    id="np-028",
    title="Cross-entropy from logits",
    difficulty="Hard",
    tags=["ML from scratch"],
    signature="def solve(logits: np.ndarray, y: np.ndarray) -> float:",
    statement="""
`logits` has shape `(n, k)` and `y` holds the integer class labels (length `n`). Return the mean cross-entropy loss of the softmax model: the average over samples of `-log p[i, y[i]]`, where `p = softmax(logits)` row-wise.

Logits can be `+-1000`: compute the loss stably from the logits (log-sum-exp), not by taking the log of rounded probabilities. Return a float.
""",
    setup="""
def make(seed, n, k, scale=2.0, shift=0.0):
    rng = np.random.default_rng(seed)
    return {"logits": rng.normal(shift, scale, (n, k)), "y": rng.integers(0, k, n)}

EXAMPLE = lambda: {"logits": np.array([[2.0, 0.5, -1.0], [0.0, 3.0, 0.0]]), "y": np.array([0, 2])}
""",
    tests="""
TESTS = [
    lambda: make(1, 10, 3),
    Test(lambda: make(2, 200, 5, scale=400.0), "extreme logits"),
    Test(lambda: make(3, 1, 4, shift=1000.0), "single sample, large offset"),
]
""",
    compare=dict(rtol=1e-7),
    hint1="`log p[i, y_i] = logits[i, y_i] - logsumexp(logits[i])` with `logsumexp(x) = m + log(sum(exp(x - m)))`, `m = max(x)` (or `scipy.special.logsumexp`).",
    hint2="m = logits.max(axis=1)\nlse = m + np.log(np.exp(logits - m[:, None]).sum(axis=1))\nnp.mean(lse - logits[np.arange(len(y)), y])",
    solution="""
def solve(logits, y):
    m = logits.max(axis=1)
    lse = m + np.log(np.exp(logits - m[:, None]).sum(axis=1))
    return float(np.mean(lse - logits[np.arange(len(y)), y]))
""",
    explanation="""
Working in log space avoids `log(0) = -inf` when a probability underflows: the loss for a confidently wrong prediction is large but finite. Deep-learning libraries fuse softmax and cross-entropy for exactly this reason (`CrossEntropyLoss` takes logits, not probabilities).
""",
    docs=["https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.logsumexp.html",
          "https://numpy.org/doc/stable/user/basics.indexing.html#integer-array-indexing"],
    wrong_solutions=[
        dict(code="""
def solve(logits, y):
    e = np.exp(logits - logits.max(axis=1, keepdims=True))
    p = e / e.sum(axis=1, keepdims=True)
    return float(-np.mean(np.log(p[np.arange(len(y)), y])))
""", why="log of underflowed probabilities: inf"),
        dict(code="""
def solve(logits, y):
    m = logits.max(axis=1)
    lse = m + np.log(np.exp(logits - m[:, None]).sum(axis=1))
    return float(np.mean(lse - logits[:, y]))
""", why="wrong indexing"),
    ],
),
dict(
    id="np-029",
    title="One gradient step: linear regression",
    difficulty="Medium",
    tags=["ML from scratch"],
    signature="def solve(X: np.ndarray, y: np.ndarray, w: np.ndarray, lr: float) -> np.ndarray:",
    statement="""
Take one step of batch gradient descent on the mean squared error

`L(w) = mean((X @ w - y) ** 2)`

(no intercept term). Return the updated weights `w - lr * grad L(w)`. Don't modify `w` in place.
""",
    setup="""
def make(seed, n, k):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, k))
    y = X @ rng.normal(size=k) + rng.normal(0, 0.1, n)
    return {"X": X, "y": y, "w": rng.normal(size=k), "lr": 0.05}

EXAMPLE = lambda: {"X": np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]), "y": np.array([1.0, 2.0, 3.0]),
                   "w": np.array([0.1, -0.1]), "lr": 0.01}
""",
    tests="""
TESTS = [
    lambda: make(1, 20, 3),
    lambda: make(2, 1000, 10),
    Test(lambda: make(3, 1, 1), "one sample"),
]
""",
    mutation_check=True,
    hint1="The gradient of the MSE is `(2 / n) * X.T @ (X @ w - y)`.",
    hint2="grad = 2 / len(y) * X.T @ (X @ w - y)\nw - lr * grad",
    solution="""
def solve(X, y, w, lr):
    grad = 2 / len(y) * X.T @ (X @ w - y)
    return w - lr * grad
""",
    explanation="""
Write the residual `r = Xw - y` first, then `grad = (2/n) X^T r`: shape `(k,)` like `w`. The factor 2 is often folded into the learning rate (losses written as `1/(2n) ||r||^2`), so read the loss definition carefully. Use `w - lr * grad`, not `w -= ...`, to avoid mutating the caller's array.
""",
    docs=["https://numpy.org/doc/stable/reference/generated/numpy.matmul.html"],
    wrong_solutions=[
        dict(code="def solve(X, y, w, lr):\n    grad = X.T @ (X @ w - y) / len(y)\n    return w - lr * grad", why="missing factor 2"),
        dict(code="def solve(X, y, w, lr):\n    grad = 2 / len(y) * X.T @ (X @ w - y)\n    return w + lr * grad", why="gradient ascent"),
        dict(code="def solve(X, y, w, lr):\n    w -= lr * 2 / len(y) * X.T @ (X @ w - y)\n    return w", why="mutates w"),
    ],
),
dict(
    id="np-030",
    title="One gradient step: logistic regression",
    difficulty="Medium",
    allow_in_statement=["sigmoid"],
    tags=["ML from scratch"],
    signature="def solve(X: np.ndarray, y: np.ndarray, w: np.ndarray, lr: float) -> np.ndarray:",
    statement="""
Logistic regression without intercept or regularization: `p = sigmoid(X @ w)` and the loss is the mean log-loss

`L(w) = -mean(y * log(p) + (1 - y) * log(1 - p))`, with `y` in {0, 1}.

Return the weights after one step of batch gradient descent, `w - lr * grad L(w)`.
""",
    setup="""
def make(seed, n, k):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, k))
    y = (rng.random(n) < 1 / (1 + np.exp(-X @ rng.normal(size=k)))).astype(float)
    return {"X": X, "y": y, "w": rng.normal(0, 0.5, k), "lr": 0.1}

EXAMPLE = lambda: {"X": np.array([[1.0, 0.5], [-1.0, 2.0], [0.5, -0.5]]), "y": np.array([1.0, 0.0, 1.0]),
                   "w": np.array([0.2, -0.3]), "lr": 0.1}
""",
    tests="""
TESTS = [
    lambda: make(1, 30, 3),
    lambda: make(2, 2000, 8),
    Test(lambda: make(3, 1, 2), "one sample"),
]
""",
    hint1="The gradient is `X.T @ (sigmoid(X @ w) - y) / n`, with `sigmoid(z) = 1 / (1 + np.exp(-z))`.",
    hint2="p = 1 / (1 + np.exp(-(X @ w)))\nw - lr * X.T @ (p - y) / len(y)",
    solution="""
def solve(X, y, w, lr):
    p = 1 / (1 + np.exp(-(X @ w)))
    return w - lr * X.T @ (p - y) / len(y)
""",
    explanation="""
The log-loss gradient has the same form as least squares, `X^T (prediction - y) / n`, because the sigmoid's derivative cancels the log. For very negative `z`, `np.exp(-z)` can overflow (a harmless warning, result 0); `scipy.special.expit` is the stable sigmoid.
""",
    docs=["https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.expit.html",
          "https://scikit-learn.org/stable/modules/linear_model.html#logistic-regression"],
    wrong_solutions=[
        dict(code="def solve(X, y, w, lr):\n    p = 1 / (1 + np.exp(-(X @ w)))\n    return w - lr * X.T @ (y - p) / len(y)", why="sign flipped"),
        dict(code="def solve(X, y, w, lr):\n    return w - lr * 2 * X.T @ (X @ w - y) / len(y)", why="MSE gradient"),
    ],
),
dict(
    id="np-031",
    title="k-means step 1: assign to the nearest centroid",
    difficulty="Medium",
    tags=["ML from scratch", "broadcasting"],
    signature="def solve(X: np.ndarray, C: np.ndarray) -> np.ndarray:",
    statement="""
Assign each row of `X` (`n x d`) to its nearest centroid in `C` (`k x d`) by Euclidean distance. Return the length-`n` integer array of centroid indices (ties go to the lower index).
""",
    setup="""
def make(seed, n, k, d):
    rng = np.random.default_rng(seed)
    C = rng.normal(0, 3, (k, d))
    X = C[rng.integers(0, k, n)] + rng.normal(0, 2.0, (n, d))
    return {"X": X, "C": C}

EXAMPLE = lambda: {"X": np.array([[0.0, 0.0], [5.0, 5.0], [4.0, 0.0], [1.0, 1.0]]),
                   "C": np.array([[0.0, 0.0], [5.0, 4.0]])}
""",
    tests="""
TESTS = [
    lambda: make(1, 20, 3, 2),
    lambda: make(2, 2000, 8, 5),
    Test(lambda: make(3, 10, 1, 3), "single centroid"),
]
""",
    hint1="Broadcast to an `(n, k)` matrix of squared distances, then `argmin(axis=1)`.",
    hint2="d2 = ((X[:, None, :] - C[None, :, :]) ** 2).sum(axis=-1)\nd2.argmin(axis=1)",
    solution="""
def solve(X, C):
    d2 = ((X[:, None, :] - C[None, :, :]) ** 2).sum(axis=-1)
    return d2.argmin(axis=1)
""",
    explanation="""
Comparing **squared** distances gives the same argmin without the square root. `argmin(axis=1)` picks, for each point (row), the closest centroid (column), returning the first index on ties. This is the E-step of Lloyd's algorithm.
""",
    docs=["https://numpy.org/doc/stable/reference/generated/numpy.argmin.html"],
    wrong_solutions=[
        dict(code="def solve(X, C):\n    d2 = ((X[:, None, :] - C[None, :, :]) ** 2).sum(axis=-1)\n    return d2.argmax(axis=1)", why="farthest centroid"),
        dict(code="def solve(X, C):\n    d1 = np.abs(X[:, None, :] - C[None, :, :]).sum(axis=-1)\n    return d1.argmin(axis=1)", why="Manhattan distance"),
    ],
),
dict(
    id="np-032",
    title="k-means step 2: update the centroids",
    difficulty="Hard",
    tags=["ML from scratch"],
    signature="def solve(X: np.ndarray, labels: np.ndarray, C: np.ndarray) -> np.ndarray:",
    statement="""
Given points `X` (`n x d`), their current cluster `labels` (ints in `0..k-1`) and the previous centroids `C` (`k x d`), return the new `k x d` centroids: the mean of the points assigned to each cluster.

A cluster with **no** points keeps its previous centroid (no NaN, no warning).
""",
    setup="""
def make(seed, n, k, d, empty=()):
    rng = np.random.default_rng(seed)
    labels = rng.integers(0, k, n)
    for j in empty:
        labels[labels == j] = (j + 1) % k
    return {"X": rng.normal(0, 2, (n, d)), "labels": labels, "C": rng.normal(0, 1, (k, d))}

EXAMPLE = lambda: {"X": np.array([[0.0, 0.0], [2.0, 2.0], [10.0, 10.0]]), "labels": np.array([0, 0, 2]),
                   "C": np.array([[1.0, 0.0], [5.0, 5.0], [9.0, 9.0]])}
""",
    tests="""
TESTS = [
    lambda: make(1, 30, 3, 2),
    Test(lambda: make(2, 500, 6, 4, empty=(2, 4)), "empty clusters"),
    Test(lambda: make(3, 1, 3, 2), "one point"),
]
""",
    hint1="For each cluster `j`, average `X[labels == j]` along axis 0, falling back to `C[j]` when the mask is empty (vectorized: `np.add.at` + `np.bincount`).",
    hint2="np.array([X[labels == j].mean(axis=0) if np.any(labels == j) else C[j]\n          for j in range(len(C))])",
    solution="""
def solve(X, labels, C):
    return np.array([X[labels == j].mean(axis=0) if np.any(labels == j) else C[j]
                     for j in range(len(C))])
""",
    explanation="""
Looping over `k` clusters (not `n` points) is fine because `k` is small. The empty-cluster guard matters: `mean` of an empty selection is NaN with a warning, and NaN centroids then swallow nothing forever. Fully vectorized: `sums = np.zeros_like(C); np.add.at(sums, labels, X); counts = np.bincount(labels, minlength=k)`.
""",
    docs=["https://numpy.org/doc/stable/reference/generated/numpy.ufunc.at.html",
          "https://numpy.org/doc/stable/reference/generated/numpy.bincount.html"],
    wrong_solutions=[
        dict(code="def solve(X, labels, C):\n    return np.array([X[labels == j].mean(axis=0) for j in range(len(C))])", why="empty clusters become NaN"),
        dict(code="def solve(X, labels, C):\n    return np.array([X[labels == j].mean(axis=0) if np.any(labels == j) else np.zeros(X.shape[1]) for j in range(len(C))])", why="resets empty clusters to the origin"),
    ],
),
dict(
    id="np-033",
    title="PCA via SVD",
    difficulty="Hard",
    tags=["ML from scratch", "linear algebra"],
    signature="def solve(X: np.ndarray, k: int) -> tuple:",
    statement="""
Run PCA on `X` (`n x d`) with an SVD and keep the first `k` components. Return a tuple `(scores, components, explained_ratio)`:

* `components`: `k x d`, the top-`k` principal directions (unit vectors, one per row);
* `scores`: `n x k`, the **centered** data projected onto those components;
* `explained_ratio`: length `k`, each component's share of the total variance.

Component signs are arbitrary: each component may be flipped, as long as its scores flip with it.
""",
    setup="""
def make(seed, n, d):
    rng = np.random.default_rng(seed)
    L = rng.normal(size=(d, d)) * rng.uniform(0.2, 3, d)
    return {"X": rng.normal(size=(n, d)) @ L + rng.uniform(-10, 10, d)}

def iris():
    from sklearn.datasets import load_iris
    return load_iris().data

EXAMPLE = lambda: {"X": np.array([[2.5, 2.4], [0.5, 0.7], [2.2, 2.9], [1.9, 2.2], [3.1, 3.0], [2.3, 2.7]]), "k": 1}
""",
    tests="""
TESTS = [
    lambda: {**make(1, 30, 4), "k": 2},
    lambda: {**make(2, 500, 10), "k": 5},
    Test(lambda: {**make(3, 20, 3), "k": 3}, "all components"),
    Test(lambda: {"X": iris(), "k": 2}, "sklearn's iris"),
]

def check(got, exp, inputs):
    if not isinstance(got, (tuple, list)) or len(got) != 3:
        fail("return a tuple (scores, components, explained_ratio)")
    s, c, r = (np.asarray(a, dtype=float) for a in got)
    es, ec, er = exp
    for name, g, e in [("scores", s, es), ("components", c, ec), ("explained_ratio", r, er)]:
        if g.shape != e.shape:
            fail(f"{name}: expected shape {e.shape}, got {g.shape}")
    msg = compare(r, er, path="explained_ratio")
    if msg:
        return msg
    for j in range(len(ec)):
        sign = 1.0 if np.dot(c[j], ec[j]) >= 0 else -1.0
        if not np.allclose(c[j], sign * ec[j], atol=1e-6):
            fail(f"components[{j}] is not the expected principal direction (up to sign)")
        if not np.allclose(s[:, j], sign * es[:, j], atol=1e-6):
            fail(f"scores[:, {j}] do not match the projection on components[{j}] (did you center X?)")
""",
    hint1="Center with `X - X.mean(axis=0)`, then `U, S, Vt = np.linalg.svd(Xc, full_matrices=False)`: components are `Vt[:k]`, scores `Xc @ Vt[:k].T`, and variance shares `S**2 / (S**2).sum()`.",
    hint2="Xc = X - X.mean(axis=0)\nU, S, Vt = np.linalg.svd(Xc, full_matrices=False)\nXc @ Vt[:k].T, Vt[:k], (S**2 / (S**2).sum())[:k]",
    solution="""
def solve(X, k):
    Xc = X - X.mean(axis=0)
    U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
    var = S ** 2
    return Xc @ Vt[:k].T, Vt[:k], (var / var.sum())[:k]
""",
    explanation="""
The right singular vectors (rows of `Vt`) of the centered data are the principal directions, and squared singular values are proportional to the variance along them. Forgetting to center is the classic bug: the first component then points at the mean. `sklearn.decomposition.PCA` does exactly this (and flips signs deterministically).
""",
    docs=["https://numpy.org/doc/stable/reference/generated/numpy.linalg.svd.html",
          "https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.PCA.html"],
    wrong_solutions=[
        dict(code="""
def solve(X, k):
    U, S, Vt = np.linalg.svd(X, full_matrices=False)
    var = S ** 2
    return X @ Vt[:k].T, Vt[:k], (var / var.sum())[:k]
""", why="not centered"),
        dict(code="""
def solve(X, k):
    Xc = X - X.mean(axis=0)
    U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
    return Xc @ Vt[:k].T, Vt[:k], (S / S.sum())[:k]
""", why="ratio of singular values, not variances"),
    ],
),
dict(
    id="np-034",
    title="Scaled dot-product attention",
    difficulty="Hard",
    allow_in_statement=["sqrt", "softmax"],
    tags=["ML from scratch"],
    signature="def solve(Q: np.ndarray, K: np.ndarray, V: np.ndarray, mask: np.ndarray) -> np.ndarray:",
    statement="""
Implement single-head attention. `Q` is `n x d`, `K` is `m x d`, `V` is `m x dv`, and `mask` is an `n x m` boolean array where `True` means "query i may attend to key j" (every row has at least one `True`).

Return `softmax(S) @ V` (shape `n x dv`), where `S = Q K^T / sqrt(d)` with masked-out positions set to `-inf`, and the softmax runs over each row.
""",
    setup="""
def make(seed, n, m, d, dv, causal=False):
    rng = np.random.default_rng(seed)
    mask = np.tril(np.ones((n, m), dtype=bool)) if causal else rng.random((n, m)) < 0.7
    mask[:, 0] = True
    return {"Q": rng.normal(size=(n, d)), "K": rng.normal(size=(m, d)), "V": rng.normal(size=(m, dv)), "mask": mask}

EXAMPLE = lambda: make(0, 3, 3, 2, 2, causal=True)
""",
    tests="""
TESTS = [
    lambda: make(1, 4, 6, 8, 3),
    Test(lambda: make(2, 64, 64, 16, 16, causal=True), "causal mask"),
    Test(lambda: {**make(3, 5, 5, 4, 2), "mask": np.ones((5, 5), dtype=bool)}, "no mask"),
]
""",
    hint1="Scale `Q @ K.T` by `1 / np.sqrt(d)`, apply the mask with `np.where(mask, S, -np.inf)`, then a stable row-wise softmax and `@ V`.",
    hint2="S = np.where(mask, Q @ K.T / np.sqrt(Q.shape[1]), -np.inf)\nP = np.exp(S - S.max(axis=1, keepdims=True))\n(P / P.sum(axis=1, keepdims=True)) @ V",
    solution="""
def solve(Q, K, V, mask):
    S = np.where(mask, Q @ K.T / np.sqrt(Q.shape[1]), -np.inf)
    P = np.exp(S - S.max(axis=1, keepdims=True))
    return (P / P.sum(axis=1, keepdims=True)) @ V
""",
    explanation="""
Dividing by `sqrt(d)` keeps the logits' variance near 1 so the softmax doesn't saturate as `d` grows. `-inf` logits become exactly 0 after `exp`; subtracting the row max keeps it stable (finite because every row has an allowed key). A causal mask is `np.tril(...)`: each token sees itself and the past.
""",
    docs=["https://numpy.org/doc/stable/reference/generated/numpy.where.html",
          "https://numpy.org/doc/stable/reference/generated/numpy.tril.html"],
    wrong_solutions=[
        dict(code="""
def solve(Q, K, V, mask):
    S = np.where(mask, Q @ K.T, -np.inf)
    P = np.exp(S - S.max(axis=1, keepdims=True))
    return (P / P.sum(axis=1, keepdims=True)) @ V
""", why="no scaling"),
        dict(code="""
def solve(Q, K, V, mask):
    S = np.where(mask, Q @ K.T / np.sqrt(Q.shape[1]), -np.inf)
    P = np.exp(S - S.max(axis=0, keepdims=True))
    return (P / P.sum(axis=0, keepdims=True)) @ V
""", why="softmax over the wrong axis"),
        dict(code="""
def solve(Q, K, V, mask):
    S = Q @ K.T / np.sqrt(Q.shape[1])
    P = np.exp(S - S.max(axis=1, keepdims=True))
    return (P / P.sum(axis=1, keepdims=True)) @ V
""", why="mask ignored"),
    ],
),
]
