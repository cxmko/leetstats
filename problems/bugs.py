SECTION = "bugs"

# Fix-the-bug problems: `starter` is the buggy code shown in the editor; the
# statement describes the intended behaviour; tests are the usual hidden tests.

PROBLEMS = [
dict(
    id="bug-001",
    title="Fix the bug: the scaler saw the test set",
    difficulty="Easy",
    tags=["leakage"],
    signature="def solve(X: np.ndarray, y: np.ndarray) -> np.ndarray:",
    statement="""
The function should hold out 25% of the rows as a test set (stratified on `y`, `random_state=0`), standardize the features **using the training rows only**, fit `LogisticRegression(max_iter=1000)` on the training rows, and return the predicted probabilities of class 1 for the test rows (in the order the split returns them).

The code in the editor has one leakage bug. Fix it.
""",
    starter="""
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

def solve(X, y):
    Xs = StandardScaler().fit_transform(X)
    X_tr, X_te, y_tr, y_te = train_test_split(Xs, y, test_size=0.25, stratify=y, random_state=0)
    model = LogisticRegression(max_iter=1000).fit(X_tr, y_tr)
    return model.predict_proba(X_te)[:, 1]
""",
    setup="""
def make(seed, n, k=5):
    from sklearn.datasets import make_classification
    X, y = make_classification(n_samples=n, n_features=k, n_informative=3, n_redundant=0, random_state=seed)
    return {"X": X * np.arange(1, k + 1) * 10 + 50, "y": y}

EXAMPLE = lambda: make(0, 40)
""",
    tests="""
TESTS = [
    lambda: make(1, 200),
    lambda: make(2, 1000, k=8),
    Test(lambda: make(3, 24, k=3), "small"),
]
""",
    compare=dict(rtol=1e-7, atol=1e-9),
    hint1="Split **first**, then `fit` the scaler on `X_tr` only and `transform` both parts (or put the scaler in a pipeline).",
    hint2="X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, stratify=y, random_state=0)\nscaler = StandardScaler().fit(X_tr)\nmodel.fit(scaler.transform(X_tr), y_tr).predict_proba(scaler.transform(X_te))[:, 1]",
    solution="""
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

def solve(X, y):
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, stratify=y, random_state=0)
    scaler = StandardScaler().fit(X_tr)
    model = LogisticRegression(max_iter=1000).fit(scaler.transform(X_tr), y_tr)
    return model.predict_proba(scaler.transform(X_te))[:, 1]
""",
    explanation="""
Fitting the scaler before splitting lets test-set means and variances shape the training features. It's a small leak here but the same bug pattern (impute, select, encode, resample before splitting) can be huge. `make_pipeline(StandardScaler(), LogisticRegression())` makes it impossible to get wrong.
""",
    docs=["https://scikit-learn.org/stable/common_pitfalls.html#data-leakage"],
    wrong_solutions=[
        dict(code="""
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

def solve(X, y):
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, stratify=y, random_state=0)
    model = LogisticRegression(max_iter=1000).fit(StandardScaler().fit_transform(X_tr), y_tr)
    return model.predict_proba(StandardScaler().fit_transform(X_te))[:, 1]
""", why="refits the scaler on the test set"),
    ],
),
dict(
    id="bug-002",
    title="Fix the bug: centering the wrong way",
    difficulty="Easy",
    tags=["axes & shapes"],
    signature="def solve(X: np.ndarray) -> np.ndarray:",
    statement="""
`X` has one row per sample and one column per feature. The function should **center every feature (column)** to zero mean. The code in the editor has one bug. Fix it.
""",
    starter="""
def solve(X):
    return X - X.mean(axis=1, keepdims=True)
""",
    setup="""
def make(seed, n, k):
    rng = np.random.default_rng(seed)
    return {"X": rng.normal(rng.uniform(-10, 10, k), 2, (n, k))}

EXAMPLE = lambda: {"X": np.array([[1.0, 10.0], [3.0, 30.0], [5.0, 20.0]])}
""",
    tests="""
TESTS = [
    lambda: make(1, 20, 3),
    lambda: make(2, 500, 10),
    Test(lambda: make(3, 4, 4), "square"),
]
""",
    hint1="`axis=0` reduces down the rows (one value per column); `axis=1` reduces across a row.",
    hint2="X - X.mean(axis=0)",
    solution="""
def solve(X):
    return X - X.mean(axis=0)
""",
    explanation="""
`axis` names the dimension that is **collapsed**: `axis=0` collapses rows and gives per-column statistics. A `(k,)` vector broadcasts against `(n, k)` row by row, so no `keepdims` is needed here. Check by asserting `out.mean(axis=0)` is about 0.
""",
    docs=["https://numpy.org/doc/stable/reference/generated/numpy.mean.html",
          "https://numpy.org/doc/stable/user/basics.broadcasting.html"],
    wrong_solutions=[
        dict(code="def solve(X):\n    return X - X.mean()", why="global mean"),
    ],
),
dict(
    id="bug-003",
    title="Fix the bug: yesterday's return",
    difficulty="Easy",
    tags=["lookahead"],
    signature="def solve(close: pd.Series) -> pd.DataFrame:",
    statement="""
`close` is a daily closing-price series indexed by date. The function should return a DataFrame with the same index and two columns:

* `ret`: the daily simple return (NaN on the first day);
* `ret_lag1`: **yesterday's** return, a feature known before today's close (NaN on the first two days).

The code in the editor has one bug that leaks future information into the feature. Find it and fix it.
""",
    starter="""
def solve(close):
    ret = close.pct_change()
    return pd.DataFrame({"ret": ret, "ret_lag1": ret.shift(-1)})
""",
    setup="""
def make(seed, n):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2024-01-01", periods=n, name="date")
    return {"close": pd.Series(100 * np.cumprod(1 + rng.normal(0, 0.01, n)), index=idx, name="close")}

EXAMPLE = lambda: make(0, 6)
""",
    tests="""
TESTS = [
    lambda: make(1, 30),
    lambda: make(2, 300),
    Test(lambda: make(3, 2), "two days"),
]
""",
    hint1="`shift(k)` with positive `k` moves values **down** (later in time): row t gets the value from t-k.",
    hint2="ret.shift(1)",
    solution="""
def solve(close):
    ret = close.pct_change()
    return pd.DataFrame({"ret": ret, "ret_lag1": ret.shift(1)})
""",
    explanation="""
`shift(-1)` pulls *tomorrow's* value into today's row: a feature built that way would not exist yet at prediction time, and a backtest would look brilliant. Positive shifts look back; negative shifts are for building **labels** (forward returns), never features.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.Series.shift.html"],
    wrong_solutions=[
        dict(code="""
def solve(close):
    ret = close.pct_change()
    return pd.DataFrame({"ret": ret, "ret_lag1": ret.diff()})
""", why="diff of returns"),
        dict(code="""
def solve(close):
    ret = close.pct_change()
    return pd.DataFrame({"ret": ret, "ret_lag1": ret.shift(1).fillna(0)})
""", why="fills the warm-up NaNs with 0"),
    ],
),
dict(
    id="bug-004",
    title="Fix the bug: an assignment that does nothing",
    difficulty="Medium",
    tags=["pandas semantics"],
    signature="def solve(orders: pd.DataFrame) -> pd.DataFrame:",
    statement="""
Return a copy of `orders` with a new last column `discount`: `0.1` for orders with a `quantity` of **5 or more**, `0.0` otherwise. `orders` itself must not change.

The code in the editor runs without an error but the discount never appears. Fix it.
""",
    starter="""
def solve(orders):
    out = orders.copy()
    out["discount"] = 0.0
    out[out["quantity"] >= 5]["discount"] = 0.1
    return out
""",
    setup="""
EXAMPLE = lambda: {"orders": D.orders(seed=5, n=30)}
""",
    tests="""
TESTS = [
    lambda: {"orders": D.orders(seed=1, n=100)},
    lambda: {"orders": D.orders(seed=2, n=2000)},
    Test(lambda: {"orders": D.orders(seed=3, n=200).assign(quantity=5)}, "every order qualifies"),
]
""",
    mutation_check=True,
    hint1="Assign in **one** indexing step: `df.loc[row_mask, 'column'] = value`.",
    hint2="out.loc[out['quantity'] >= 5, 'discount'] = 0.1",
    solution="""
def solve(orders):
    out = orders.copy()
    out["discount"] = 0.0
    out.loc[out["quantity"] >= 5, "discount"] = 0.1
    return out
""",
    explanation="""
`out[mask]['discount'] = ...` is chained assignment: `out[mask]` builds a new object and the assignment lands on that temporary. Under pandas 3's Copy-on-Write it **never** updates `out` (you get a `ChainedAssignmentError` warning); in pandas 2 it sometimes did, with a `SettingWithCopyWarning`. `.loc[mask, col] = v` always works. So does `np.where`.
""",
    docs=["https://pandas.pydata.org/docs/user_guide/copy_on_write.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.loc.html"],
    wrong_solutions=[
        dict(code="""
def solve(orders):
    out = orders.copy()
    out["discount"] = 0.0
    out.loc[out["quantity"] > 5, "discount"] = 0.1
    return out
""", why="strictly more than 5"),
        dict(code="""
def solve(orders):
    orders["discount"] = np.where(orders["quantity"] >= 5, 0.1, 0.0)
    return orders
""", why="modifies the input"),
    ],
),
dict(
    id="bug-005",
    title="Fix the bug: orders without a region disappear",
    difficulty="Medium",
    tags=["missing data", "aggregation"],
    signature="def solve(orders: pd.DataFrame) -> pd.Series:",
    statement="""
Return the number of orders per region, sorted by region, **including** one entry (with a missing-value label) counting the orders whose region is missing; that entry comes last. The counts must add up to the number of orders.

The code in the editor silently loses some orders. Fix it.
""",
    starter="""
def solve(orders):
    return orders.groupby("region").size()
""",
    setup="""
def make(seed, n, share=0.1):
    o = D.orders(seed=seed, n=n)
    rng = np.random.default_rng(seed)
    o.loc[rng.random(n) < share, "region"] = np.nan
    return {"orders": o}

EXAMPLE = lambda: make(0, 20, 0.2)
""",
    tests="""
TESTS = [
    lambda: make(1, 100),
    lambda: make(2, 3000, 0.02),
    Test(lambda: make(3, 10, 0.0), "no missing region"),
]
""",
    hint1="`groupby(..., dropna=False)` keeps a group for missing keys.",
    hint2="orders.groupby('region', dropna=False).size()",
    solution="""
def solve(orders):
    return orders.groupby("region", dropna=False).size()
""",
    explanation="""
`groupby` drops rows whose key is NaN by default, so totals silently stop adding up. `value_counts()` drops NaN too (`dropna=False` again). Always reconcile: `result.sum() == len(df)`. Filling with a label such as `'Unknown'` is often clearer for reports.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.groupby.html",
          "https://pandas.pydata.org/docs/user_guide/groupby.html#na-group-handling"],
    wrong_solutions=[
        dict(code="def solve(orders):\n    return orders['region'].value_counts(dropna=False)", why="sorted by count"),
        dict(code="def solve(orders):\n    return orders.groupby(orders['region'].fillna('Unknown')).size()", why="different label for the missing group"),
    ],
),
dict(
    id="bug-006",
    title="Fix the bug: annualized volatility",
    difficulty="Easy",
    tags=["annualization"],
    signature="def solve(daily: pd.Series) -> float:",
    statement="""
Return the **annualized volatility** of the daily returns `daily`, using the sample standard deviation and 252 trading days per year. The code in the editor has one bug. Fix it.
""",
    starter="""
def solve(daily):
    return float(daily.std() * 252)
""",
    setup="""
def make(seed, n, sigma=0.012):
    rng = np.random.default_rng(seed)
    return {"daily": pd.Series(rng.normal(0.0004, sigma, n), index=pd.bdate_range("2023-01-02", periods=n))}

EXAMPLE = lambda: make(0, 60)
""",
    tests="""
TESTS = [
    lambda: make(1, 252),
    lambda: make(2, 2500, sigma=0.02),
    Test(lambda: make(3, 10), "two weeks"),
]
""",
    hint1="Volatility scales with the **square root** of time.",
    hint2="daily.std() * np.sqrt(252)",
    solution="""
def solve(daily):
    return float(daily.std() * np.sqrt(252))
""",
    explanation="""
Variances of independent returns add up, so variance scales with time and the standard deviation with sqrt(time): annual vol = daily vol x sqrt(252) (about 15.9x), while the annual mean return is the daily mean x 252. Multiplying the std by 252 overstates risk about 16-fold.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.Series.std.html"],
    wrong_solutions=[
        dict(code="def solve(daily):\n    return float(np.std(daily) * np.sqrt(252))", why="population std (ddof=0)"),
        dict(code="def solve(daily):\n    return float(daily.std() * np.sqrt(12))", why="monthly factor"),
    ],
),
dict(
    id="bug-007",
    title="Fix the bug: returns that jump between tickers",
    difficulty="Medium",
    tags=["lookahead", "aggregation"],
    signature="def solve(prices: pd.DataFrame) -> pd.Series:",
    statement="""
`prices` is a long daily panel (`date, ticker, close, volume`) sorted by (`date`, `ticker`). Return each row's daily simple return **within its ticker** (NaN on each ticker's first date), aligned to `prices`. The code in the editor has one bug. Fix it.
""",
    starter="""
def solve(prices):
    return prices["close"].pct_change()
""",
    setup="""
EXAMPLE = lambda: {"prices": D.prices(seed=0, n_days=3, n_tickers=3)}
""",
    tests="""
TESTS = [
    lambda: {"prices": D.prices(seed=1, n_days=40, n_tickers=5)},
    lambda: {"prices": D.prices(seed=2, n_days=500, n_tickers=20)},
    Test(lambda: {"prices": D.prices(seed=3, n_days=2, n_tickers=2)}, "two dates"),
]
""",
    hint1="Make the operation per ticker with `groupby('ticker')`.",
    hint2="prices.groupby('ticker')['close'].pct_change()",
    solution="""
def solve(prices):
    return prices.groupby("ticker")["close"].pct_change()
""",
    explanation="""
In a long panel, the previous row belongs to a different ticker, so the "return" is a ratio of two unrelated prices. Every lag-based operation (`shift`, `diff`, `pct_change`, `rolling`) needs a `groupby` on a long panel, or a wide (date x ticker) layout.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.api.typing.DataFrameGroupBy.pct_change.html"],
    wrong_solutions=[
        dict(code="def solve(prices):\n    return prices.groupby('date')['close'].pct_change()", why="grouped by date"),
    ],
),
dict(
    id="bug-008",
    title="Fix the bug: a join that multiplies rows",
    difficulty="Medium",
    tags=["joins"],
    signature="def solve(orders: pd.DataFrame, rates: pd.DataFrame) -> pd.DataFrame:",
    statement="""
`orders` has `order_id, currency, amount`; `rates` has `currency, date, rate` with **several historical rows per currency**. Convert each amount to EUR with the **most recent** rate of its currency. Return `order_id, currency, amount, amount_eur` with exactly one row per order, in the original order (default index).

The code in the editor returns too many rows. Fix it.
""",
    starter="""
def solve(orders, rates):
    out = orders.merge(rates, on="currency")
    out["amount_eur"] = out["amount"] * out["rate"]
    return out[["order_id", "currency", "amount", "amount_eur"]]
""",
    setup="""
def make(seed, n, n_hist=3):
    rng = np.random.default_rng(seed)
    cur = ["USD", "GBP", "JPY", "CHF"]
    rows = []
    for c, base in zip(cur, [0.92, 1.17, 0.0062, 1.04]):
        for d in pd.date_range("2024-09-02", periods=n_hist, freq="7D"):
            rows.append((c, d, round(base * rng.uniform(0.97, 1.03), 5)))
    rates = pd.DataFrame(rows, columns=["currency", "date", "rate"]).sample(frac=1, random_state=seed).reset_index(drop=True)
    orders = pd.DataFrame({"order_id": np.arange(1, n + 1), "currency": rng.choice(cur, n),
                           "amount": np.round(rng.gamma(2, 80, n), 2)})
    return {"orders": orders, "rates": rates}

EXAMPLE = lambda: make(0, 5)
""",
    tests="""
TESTS = [
    lambda: make(1, 50),
    lambda: make(2, 2000, n_hist=10),
    Test(lambda: make(3, 6, n_hist=1), "one rate per currency"),
]
""",
    hint1="Reduce `rates` to one row per currency first (`sort_values('date').drop_duplicates('currency', keep='last')`), and merge with `validate='many_to_one'`.",
    hint2="latest = rates.sort_values('date').drop_duplicates('currency', keep='last')\nout = orders.merge(latest, on='currency', how='left', validate='many_to_one')",
    solution="""
def solve(orders, rates):
    latest = rates.sort_values("date").drop_duplicates("currency", keep="last")
    out = orders.merge(latest, on="currency", how="left", validate="many_to_one")
    out["amount_eur"] = out["amount"] * out["rate"]
    return out[["order_id", "currency", "amount", "amount_eur"]]
""",
    explanation="""
Merging on a key that repeats on the right creates one output row per match: each order appears once per historical rate, and any total computed afterwards is inflated. Decide which right-hand row is valid, deduplicate, and let `validate=` assert the relationship. For "rate as of the order date", use `merge_asof`.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.merge.html"],
    wrong_solutions=[
        dict(code="""
def solve(orders, rates):
    first = rates.drop_duplicates("currency")
    out = orders.merge(first, on="currency", how="left")
    out["amount_eur"] = out["amount"] * out["rate"]
    return out[["order_id", "currency", "amount", "amount_eur"]]
""", why="keeps an arbitrary (unsorted) rate"),
        dict(code="""
def solve(orders, rates):
    avg = rates.groupby("currency", as_index=False)["rate"].mean()
    out = orders.merge(avg, on="currency", how="left")
    out["amount_eur"] = out["amount"] * out["rate"]
    return out[["order_id", "currency", "amount", "amount_eur"]]
""", why="average rate, not the latest"),
    ],
),
dict(
    id="bug-009",
    title="Fix the bug: the average of ratios",
    difficulty="Medium",
    tags=["aggregation"],
    signature="def solve(daily: pd.DataFrame) -> pd.Series:",
    statement="""
`daily` has one row per (date, device) with `visits` and `conversions`. Return the **overall conversion rate per device** (all conversions divided by all visits for that device), as a Series indexed by device (sorted).

Traffic varies a lot from day to day, and the code in the editor weights a 3-visit day like a 3,000-visit day. Fix it.
""",
    starter="""
def solve(daily):
    rate = daily["conversions"] / daily["visits"]
    return daily.assign(rate=rate).groupby("device")["rate"].mean()
""",
    setup="""
def make(seed, n_days):
    rng = np.random.default_rng(seed)
    rows = []
    for d in pd.date_range("2024-05-01", periods=n_days):
        for dev, p in [("desktop", 0.04), ("mobile", 0.02), ("tablet", 0.03)]:
            v = int(rng.choice([3, 30, 3000]) * rng.uniform(0.8, 1.2)) + 1
            rows.append((d, dev, v, int(rng.binomial(v, p * (2.5 if v < 10 else 1)))))
    return {"daily": pd.DataFrame(rows, columns=["date", "device", "visits", "conversions"])}

EXAMPLE = lambda: make(0, 4)
""",
    tests="""
TESTS = [
    lambda: make(1, 30),
    lambda: make(2, 365),
    Test(lambda: make(3, 1), "one day"),
]
""",
    hint1="Sum numerators and denominators per group, **then** divide.",
    hint2="g = daily.groupby('device')[['conversions', 'visits']].sum()\ng['conversions'] / g['visits']",
    solution="""
def solve(daily):
    g = daily.groupby("device")[["conversions", "visits"]].sum()
    return g["conversions"] / g["visits"]
""",
    explanation="""
The mean of daily rates gives every day equal weight, so tiny days with noisy rates swing the result. The ratio of sums weights by traffic, which is the actual overall rate (a cousin of Simpson's paradox). Same trap with average order value, CTR or per-store margins.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.api.typing.DataFrameGroupBy.sum.html"],
    wrong_solutions=[
        dict(code="""
def solve(daily):
    rate = daily["conversions"] / daily["visits"]
    return daily.assign(rate=rate).groupby("device")["rate"].median()
""", why="median of daily rates"),
    ],
),
dict(
    id="bug-010",
    title="Fix the bug: a moving average that peeks ahead",
    difficulty="Medium",
    tags=["lookahead"],
    signature="def solve(s: pd.Series) -> pd.Series:",
    statement="""
Return the **trailing** 5-day moving average of `s`: each value is the mean of the window that **ends** on that day (NaN for the first 4 days). It is used as a trading signal, so it must not use future data. The code in the editor has one bug. Fix it.
""",
    starter="""
def solve(s):
    return s.rolling(5, center=True).mean()
""",
    setup="""
def make(seed, n):
    rng = np.random.default_rng(seed)
    return {"s": pd.Series(np.cumsum(rng.normal(0, 1, n)), index=pd.bdate_range("2024-01-01", periods=n), name="price")}

EXAMPLE = lambda: make(0, 8)
""",
    tests="""
TESTS = [
    lambda: make(1, 50),
    lambda: make(2, 2000),
    Test(lambda: make(3, 5), "exactly one full window"),
]
""",
    hint1="`rolling` windows are trailing by default: drop `center=True`.",
    hint2="s.rolling(5).mean()",
    solution="""
def solve(s):
    return s.rolling(5).mean()
""",
    explanation="""
A centered window uses 2 future observations at every point: perfect for smoothing a chart, a leak for a signal or a feature. Default rolling windows end at the current row. If the signal is traded at today's close, consider `.shift(1)` too.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.Series.rolling.html"],
    wrong_solutions=[
        dict(code="def solve(s):\n    return s.rolling(5, min_periods=1).mean()", why="no warm-up NaNs"),
        dict(code="def solve(s):\n    return s.shift(-4).rolling(5).mean()", why="still uses the future"),
    ],
),
dict(
    id="bug-011",
    title="Fix the bug: the top order is not row 0",
    difficulty="Easy",
    tags=["indexing"],
    signature="def solve(orders: pd.DataFrame) -> int:",
    statement="""
Return the `order_id` (an int) of the order with the highest `revenue`. The code in the editor sorts correctly but then picks the wrong row. Fix it.
""",
    starter="""
def solve(orders):
    top = orders.sort_values("revenue", ascending=False)
    return int(top.loc[0, "order_id"])
""",
    setup="""
EXAMPLE = lambda: {"orders": D.orders(seed=0, n=8)}
""",
    tests="""
TESTS = [
    lambda: {"orders": D.orders(seed=1, n=100)},
    lambda: {"orders": D.orders(seed=2, n=2000)},
    Test(lambda: {"orders": D.orders(seed=3, n=50).iloc[10:]}, "label 0 not present"),
]
""",
    hint1="After sorting, the first row is at **position** 0 (`.iloc`), not at label 0 (`.loc`). Or skip the sort: `idxmax()` returns the label of the maximum.",
    hint2="orders.loc[orders['revenue'].idxmax(), 'order_id']",
    solution="""
def solve(orders):
    return int(orders.loc[orders["revenue"].idxmax(), "order_id"])
""",
    explanation="""
Sorting keeps the original index labels, so `.loc[0]` still means "the row that used to be first", or raises a KeyError when label 0 is gone. Use `.iloc[0]` for "first by position", or `idxmax`/`nlargest` to avoid sorting at all.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.Series.idxmax.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.iloc.html"],
    wrong_solutions=[
        dict(code="def solve(orders):\n    return int(orders['revenue'].idxmax())", why="returns the index label, not the order id"),
        dict(code="def solve(orders):\n    return int(orders.sort_values('revenue').iloc[0]['order_id'])", why="lowest revenue"),
    ],
),
dict(
    id="bug-012",
    title="Fix the bug: shuffled folds on a time series",
    difficulty="Medium",
    tags=["validation", "lookahead"],
    signature="def solve(X: np.ndarray, y: np.ndarray) -> float:",
    statement="""
The rows of `X` (lagged features) and `y` are in **time order**. Estimate the out-of-sample R² of `Ridge(alpha=1.0)` with 5 forward-chaining splits (scikit-learn's time-series splitter with its defaults: always train on the past, test on the following block) and return the mean R² across splits.

The code in the editor validates in a way that trains on the future. Fix it.
""",
    starter="""
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold, cross_val_score

def solve(X, y):
    cv = KFold(n_splits=5, shuffle=True, random_state=0)
    return float(cross_val_score(Ridge(alpha=1.0), X, y, cv=cv, scoring="r2").mean())
""",
    setup="""
def make(seed, n, phi=0.6):
    rng = np.random.default_rng(seed)
    x = np.zeros(n + 3)
    trend = np.linspace(0, 3, n + 3)
    for t in range(1, n + 3):
        x[t] = phi * x[t - 1] + rng.normal()
    x = x + trend
    X = np.column_stack([x[2:-1], x[1:-2], x[:-3]])
    return {"X": X, "y": x[3:]}

EXAMPLE = lambda: make(0, 60)
""",
    tests="""
TESTS = [
    lambda: make(1, 200),
    lambda: make(2, 2000, phi=0.9),
    Test(lambda: make(3, 30), "short"),
]
""",
    hint1="Use `TimeSeriesSplit(n_splits=5)` as `cv`.",
    hint2="cv = TimeSeriesSplit(n_splits=5)",
    solution="""
from sklearn.linear_model import Ridge
from sklearn.model_selection import TimeSeriesSplit, cross_val_score

def solve(X, y):
    cv = TimeSeriesSplit(n_splits=5)
    return float(cross_val_score(Ridge(alpha=1.0), X, y, cv=cv, scoring="r2").mean())
""",
    explanation="""
Shuffled folds put future observations in the training set, and with trends or autocorrelation that leaks the answer: the shuffled R² looks much better than anything you'd get live. Forward-chaining validation reproduces the real setting. Add `gap=` when features or labels span several periods.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html",
          "https://scikit-learn.org/stable/modules/cross_validation.html#time-series-split"],
    wrong_solutions=[
        dict(code="""
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold, cross_val_score

def solve(X, y):
    return float(cross_val_score(Ridge(alpha=1.0), X, y, cv=KFold(n_splits=5), scoring="r2").mean())
""", why="unshuffled K-fold still trains on the future"),
    ],
),
]
