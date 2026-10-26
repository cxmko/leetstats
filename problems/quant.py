SECTION = "quant"

PROBLEMS = [
dict(
    id="qt-001",
    title="Simple and log returns",
    difficulty="Easy",
    tags=["returns"],
    signature="def solve(close: pd.Series) -> pd.DataFrame:",
    statement="""
From the daily closing prices `close` (indexed by date), return a DataFrame with the same index and columns `simple` (`P_t / P_{t-1} - 1`) and `log` (`ln(P_t / P_{t-1})`). The first day is NaN in both.
""",
    setup="""
def make(seed, n):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2024-01-01", periods=n, name="date")
    return {"close": pd.Series(np.round(50 * np.cumprod(1 + rng.normal(0, 0.02, n)), 2), index=idx, name="close")}

EXAMPLE = lambda: make(0, 5)
""",
    tests="""
TESTS = [
    lambda: make(1, 40),
    lambda: make(2, 2500),
    Test(lambda: make(3, 1), "single day"),
]
""",
    hint1="`close.pct_change()` for simple returns, `np.log(close).diff()` for log returns.",
    hint2="pd.DataFrame({'simple': close.pct_change(), 'log': np.log(close).diff()})",
    solution="""
def solve(close):
    return pd.DataFrame({"simple": close.pct_change(), "log": np.log(close).diff()})
""",
    explanation="""
Log returns add over time (`sum(log r) = log(P_T / P_0)`), which makes them convenient for aggregation and modelling; simple returns aggregate across **assets** (portfolio return = weighted sum). They're close for small moves and diverge for large ones. Convert with `log = np.log1p(simple)`.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.Series.pct_change.html",
          "https://numpy.org/doc/stable/reference/generated/numpy.log1p.html"],
    wrong_solutions=[
        dict(code="def solve(close):\n    return pd.DataFrame({'simple': close.pct_change(), 'log': np.log(close.pct_change())})", why="log of the simple return"),
        dict(code="def solve(close):\n    return pd.DataFrame({'simple': close.diff(), 'log': np.log(close).diff()})", why="price change, not return"),
    ],
),
dict(
    id="qt-002",
    title="Compound daily returns into monthly returns",
    difficulty="Medium",
    tags=["returns"],
    signature="def solve(returns: pd.Series) -> pd.Series:",
    statement="""
`returns` holds daily **simple** returns of one asset (e.g. `0.01` = +1%), indexed by trading date (a `DatetimeIndex`). Some days may be missing.

Return the monthly simple returns obtained by compounding the daily returns within each calendar month, indexed by **month-end** dates (one entry per calendar month from the first to the last month in the data).
""",
    setup="""
def make(seed, n_days, start="2023-01-02", drop=0.0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(start, periods=n_days, name="date")
    r = pd.Series(rng.normal(0.0005, 0.02, n_days), index=idx, name="ret")
    if drop:
        r = r[rng.random(n_days) >= drop]
    return {"returns": r}

EXAMPLE = lambda: make(0, 45)
""",
    tests="""
TESTS = [
    lambda: make(1, 130),
    lambda: make(2, 520, start="2020-03-16", drop=0.05),
    Test(lambda: make(3, 3, start="2024-02-28"), "spans a month boundary"),
]
""",
    hint1="`(1 + returns).resample('ME').prod() - 1`.",
    hint2="(1 + returns).resample('ME').prod() - 1",
    solution="""
def solve(returns):
    return (1 + returns).resample("ME").prod() - 1
""",
    explanation="""
Simple returns compound multiplicatively: (1 + r1)(1 + r2)... - 1. Summing them is only an approximation, and it gets worse with volatility. (Log returns are the ones you can sum.) `'ME'` is the month-end alias in pandas >= 2.2; older code used `'M'`, which is deprecated.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.Series.resample.html",
          "https://pandas.pydata.org/docs/user_guide/timeseries.html#offset-aliases"],
    wrong_solutions=[
        dict(code="def solve(returns):\n    return returns.resample('ME').sum()", why="summing simple returns"),
        dict(code="def solve(returns):\n    return returns.resample('ME').mean() * 21", why="mean times 21"),
        dict(code="def solve(returns):\n    return (1 + returns).resample('MS').prod() - 1", why="month-start labels"),
    ],
),
dict(
    id="qt-003",
    title="Annualized rolling volatility",
    difficulty="Medium",
    tags=["risk"],
    signature="def solve(prices_wide: pd.DataFrame, window: int) -> pd.DataFrame:",
    statement="""
`prices_wide` holds daily closes, one column per ticker, indexed by date. For every ticker, compute daily simple returns, then their rolling standard deviation over `window` days (a full window of returns is required), **annualized** assuming 252 trading days. Return a DataFrame of the same shape.
""",
    setup="""
EXAMPLE = lambda: {"prices_wide": D.prices_wide(seed=0, n_days=30, n_tickers=3), "window": 20}
""",
    tests="""
TESTS = [
    lambda: {"prices_wide": D.prices_wide(seed=1, n_days=100, n_tickers=5), "window": 21},
    lambda: {"prices_wide": D.prices_wide(seed=2, n_days=750, n_tickers=20), "window": 63},
    Test(lambda: {"prices_wide": D.prices_wide(seed=3, n_days=10, n_tickers=2), "window": 20}, "shorter than the window"),
]
""",
    hint1="`prices_wide.pct_change().rolling(window).std() * np.sqrt(252)`: volatility scales with the square root of time.",
    hint2="prices_wide.pct_change().rolling(window).std() * np.sqrt(252)",
    solution="""
def solve(prices_wide, window):
    return prices_wide.pct_change().rolling(window).std() * np.sqrt(252)
""",
    explanation="""
For roughly independent daily returns, variance grows linearly with time, so volatility grows with the **square root**: annualized vol = daily std x sqrt(252), while annualized mean = daily mean x 252. Rolling operations on a wide frame run per column, so tickers don't mix. The std of *prices* is meaningless as risk.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.rolling.html"],
    wrong_solutions=[
        dict(code="def solve(prices_wide, window):\n    return prices_wide.pct_change().rolling(window).std() * 252", why="annualized with 252, not sqrt(252)"),
        dict(code="def solve(prices_wide, window):\n    return prices_wide.rolling(window).std() * np.sqrt(252)", why="std of prices"),
    ],
),
dict(
    id="qt-004",
    title="Annualized Sharpe ratio",
    difficulty="Easy",
    allow_in_statement=["mean", "std", "sqrt"],
    tags=["performance"],
    signature="def solve(daily: pd.Series, rf_annual: float) -> float:",
    statement="""
`daily` holds a strategy's daily simple returns and `rf_annual` the annual risk-free rate (e.g. `0.03`). With 252 trading days, compute daily excess returns `daily - rf_annual / 252` and return the annualized Sharpe ratio `mean(excess) / std(excess) * sqrt(252)`, using the sample standard deviation (`ddof=1`).
""",
    setup="""
def make(seed, n, mu=0.0006, sigma=0.01):
    rng = np.random.default_rng(seed)
    return {"daily": pd.Series(rng.normal(mu, sigma, n), index=pd.bdate_range("2022-01-03", periods=n)), "rf_annual": 0.03}

EXAMPLE = lambda: make(0, 60)
""",
    tests="""
TESTS = [
    lambda: make(1, 252),
    lambda: make(2, 2520, mu=0.0002),
    Test(lambda: {**make(3, 100), "rf_annual": 0.0}, "zero risk-free rate"),
]
""",
    hint1="Subtract `rf_annual / 252`, then `excess.mean() / excess.std() * np.sqrt(252)` (pandas `std` is ddof=1).",
    hint2="excess = daily - rf_annual / 252\nexcess.mean() / excess.std() * np.sqrt(252)",
    solution="""
def solve(daily, rf_annual):
    excess = daily - rf_annual / 252
    return float(excess.mean() / excess.std() * np.sqrt(252))
""",
    explanation="""
Mean scales with time and volatility with its square root, so the Sharpe ratio scales with **sqrt(periods per year)**: sqrt(252) for daily, sqrt(12) for monthly data. Mixing up 252 and sqrt(252), or forgetting the risk-free rate, are the classic errors. A single Sharpe estimate is noisy (standard error about sqrt(1/years)).
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.Series.std.html"],
    wrong_solutions=[
        dict(code="def solve(daily, rf_annual):\n    return float(daily.mean() / daily.std() * np.sqrt(252))", why="risk-free rate ignored"),
        dict(code="def solve(daily, rf_annual):\n    excess = daily - rf_annual / 252\n    return float(excess.mean() / excess.std() * 252)", why="times 252"),
    ],
),
dict(
    id="qt-005",
    title="Maximum drawdown with its peak and trough dates",
    difficulty="Medium",
    tags=["risk", "performance"],
    signature="def solve(returns: pd.Series) -> tuple:",
    statement="""
From daily simple `returns` (indexed by date), build the wealth curve W (W on day t is the product of `1 + r` over days 1..t) and the drawdown: W divided by the highest W reached so far (from the first day up to t), minus 1.

Return `(max_drawdown, peak_date, trough_date)`: the most negative drawdown (a float <= 0), the date of the peak it falls from, and the date it bottoms out.
""",
    setup="""
def make(seed, n, mu=0.0003):
    rng = np.random.default_rng(seed)
    return {"returns": pd.Series(rng.normal(mu, 0.015, n), index=pd.bdate_range("2021-01-04", periods=n, name="date"))}

EXAMPLE = lambda: make(0, 120)
""",
    tests="""
TESTS = [
    lambda: make(1, 500),
    lambda: make(2, 2500, mu=0.0006),
    Test(lambda: {"returns": pd.Series([0.1, -0.05, -0.05, 0.2], index=pd.bdate_range("2024-01-01", periods=4))}, "hand-checkable"),
]
""",
    hint1="`wealth = (1 + r).cumprod()`, `dd = wealth / wealth.cummax() - 1`; the trough is `dd.idxmin()` and the peak is `wealth[:trough].idxmax()`.",
    hint2="wealth = (1 + returns).cumprod()\ndd = wealth / wealth.cummax() - 1\ntrough = dd.idxmin()\ndd.min(), wealth[:trough].idxmax(), trough",
    solution="""
def solve(returns):
    wealth = (1 + returns).cumprod()
    dd = wealth / wealth.cummax() - 1
    trough = dd.idxmin()
    return float(dd.min()), wealth[:trough].idxmax(), trough
""",
    explanation="""
Drawdown is measured from the **running** maximum (the best level seen so far), never from the overall maximum, which lies in the future. Compound with `cumprod`, not `cumsum`, for simple returns. Max drawdown and its duration (trough to recovery) are the risk numbers investors ask about first.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.Series.cummax.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.Series.idxmin.html"],
    wrong_solutions=[
        dict(code="""
def solve(returns):
    wealth = 1 + returns.cumsum()
    dd = wealth / wealth.cummax() - 1
    trough = dd.idxmin()
    return float(dd.min()), wealth[:trough].idxmax(), trough
""", why="summed returns"),
        dict(code="""
def solve(returns):
    wealth = (1 + returns).cumprod()
    dd = wealth / wealth.max() - 1
    trough = dd.idxmin()
    return float(dd.min()), wealth.idxmax(), trough
""", why="global maximum (lookahead)"),
    ],
),
dict(
    id="qt-006",
    title="Alpha and beta to the market",
    difficulty="Medium",
    tags=["risk", "performance"],
    signature="def solve(stock: pd.Series, market: pd.Series) -> tuple:",
    statement="""
`stock` and `market` are daily simple returns on the same dates. Estimate the regression `stock = alpha + beta * market + noise` by ordinary least squares and return `(alpha, beta)` (alpha in daily units).
""",
    setup="""
def make(seed, n, beta=1.2):
    s, m = D.market_returns(seed=seed, n_days=n, beta=beta)
    return {"stock": s, "market": m}

EXAMPLE = lambda: make(0, 60)
""",
    tests="""
TESTS = [
    lambda: make(1, 250, beta=0.6),
    lambda: make(2, 2500, beta=1.5),
    Test(lambda: make(3, 10, beta=1.0), "ten days"),
]
""",
    compare=dict(rtol=1e-7, atol=1e-10),
    hint1="Beta is `cov(stock, market) / var(market)` (same ddof on both!), alpha is `mean(stock) - beta * mean(market)`; or `np.polyfit(market, stock, 1)` returns `[beta, alpha]`.",
    hint2="beta, alpha = np.polyfit(market, stock, 1)",
    solution="""
def solve(stock, market):
    beta, alpha = np.polyfit(market, stock, 1)
    return float(alpha), float(beta)
""",
    explanation="""
The OLS slope equals `cov(s, m) / var(m)`. A classic bug is `np.cov` (ddof=1) divided by `np.var` (ddof=0), which inflates beta by n/(n-1). Beta is not correlation: `beta = corr * sd(stock) / sd(market)`. For inference (t-stats, HAC errors) use statsmodels.
""",
    docs=["https://numpy.org/doc/stable/reference/generated/numpy.polyfit.html",
          "https://numpy.org/doc/stable/reference/generated/numpy.cov.html"],
    wrong_solutions=[
        dict(code="def solve(stock, market):\n    beta = np.cov(stock, market)[0, 1] / np.var(market)\n    return float(stock.mean() - beta * market.mean()), float(beta)", why="ddof mismatch"),
        dict(code="def solve(stock, market):\n    beta = stock.corr(market)\n    return float(stock.mean() - beta * market.mean()), float(beta)", why="correlation is not beta"),
    ],
),
dict(
    id="qt-007",
    title="Cross-sectional z-score per date",
    difficulty="Medium",
    tags=["cross-sectional"],
    signature="def solve(panel: pd.DataFrame) -> pd.Series:",
    statement="""
`panel` is a monthly cross-section (`date, ticker, momentum, value, size, fwd_ret`). For each **date**, standardize `momentum` across tickers: `(x - mean) / std` with the date's mean and sample std (`ddof=1`), ignoring NaNs (which stay NaN). Return a Series aligned to `panel`.
""",
    setup="""
EXAMPLE = lambda: {"panel": D.factor_panel(seed=0, n_dates=2, n_tickers=6)}
""",
    tests="""
TESTS = [
    lambda: {"panel": D.factor_panel(seed=1, n_dates=12, n_tickers=40)},
    lambda: {"panel": D.factor_panel(seed=2, n_dates=60, n_tickers=200)},
    Test(lambda: {"panel": D.factor_panel(seed=3, n_dates=1, n_tickers=5)}, "one date"),
]
""",
    hint1="`groupby('date')['momentum'].transform(lambda s: (s - s.mean()) / s.std())`.",
    hint2="g = panel.groupby('date')['momentum']\n(panel['momentum'] - g.transform('mean')) / g.transform('std')",
    solution="""
def solve(panel):
    g = panel.groupby("date")["momentum"]
    return (panel["momentum"] - g.transform("mean")) / g.transform("std")
""",
    explanation="""
Cross-sectional normalization compares stocks **with each other on the same date**, removing market-wide shifts in the signal's level and scale over time. A z-score over the whole panel mixes dates and leaks future information into early dates. Built-in `transform('mean')` / `('std')` are faster than a Python lambda.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.api.typing.SeriesGroupBy.transform.html"],
    wrong_solutions=[
        dict(code="def solve(panel):\n    m = panel['momentum']\n    return (m - m.mean()) / m.std()", why="pooled over all dates"),
        dict(code="def solve(panel):\n    g = panel.groupby('ticker')['momentum']\n    return (panel['momentum'] - g.transform('mean')) / g.transform('std')", why="per ticker (time series)"),
    ],
),
dict(
    id="qt-008",
    title="Winsorize a signal per date",
    difficulty="Hard",
    tags=["cross-sectional"],
    signature="def solve(panel: pd.DataFrame) -> pd.Series:",
    statement="""
`momentum` has fat-tailed outliers. For each **date**, clip `momentum` to that date's 5th and 95th percentiles (pandas' default linear interpolation, NaNs ignored and kept). Return a Series aligned to `panel`.
""",
    setup="""
EXAMPLE = lambda: {"panel": D.factor_panel(seed=0, n_dates=2, n_tickers=10)}
""",
    tests="""
TESTS = [
    lambda: {"panel": D.factor_panel(seed=1, n_dates=12, n_tickers=50)},
    lambda: {"panel": D.factor_panel(seed=2, n_dates=60, n_tickers=200)},
    Test(lambda: {"panel": D.factor_panel(seed=3, n_dates=1, n_tickers=4)}, "one date"),
]
""",
    hint1="Per-row bounds with `groupby('date')['momentum'].transform('quantile', 0.05)` (and 0.95), then `Series.clip(lower=lo, upper=hi)`.",
    hint2="g = panel.groupby('date')['momentum']\npanel['momentum'].clip(g.transform('quantile', 0.05), g.transform('quantile', 0.95))",
    solution="""
def solve(panel):
    g = panel.groupby("date")["momentum"]
    return panel["momentum"].clip(g.transform("quantile", 0.05), g.transform("quantile", 0.95))
""",
    explanation="""
Winsorizing caps extremes instead of dropping rows, which keeps the cross-section complete. Do it **per date**: a global cutoff would clip calm months too little and volatile months too much, and it uses future data. `clip` accepts Series bounds aligned on the index.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.Series.clip.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.api.typing.SeriesGroupBy.quantile.html"],
    wrong_solutions=[
        dict(code="def solve(panel):\n    m = panel['momentum']\n    return m.clip(m.quantile(0.05), m.quantile(0.95))", why="global cutoffs"),
        dict(code="def solve(panel):\n    g = panel.groupby('date')['momentum']\n    return panel['momentum'].clip(g.transform('quantile', 0.01), g.transform('quantile', 0.99))", why="1st/99th percentiles"),
    ],
),
dict(
    id="qt-009",
    title="Forward-return labels and a lagged feature, no lookahead",
    difficulty="Hard",
    tags=["labels & lookahead"],
    signature="def solve(prices: pd.DataFrame, h: int) -> pd.DataFrame:",
    statement="""
`prices` is a long daily panel (`date, ticker, close, volume`) sorted by (`date`, `ticker`). Return a DataFrame aligned to `prices` with two columns, computed **within each ticker**:

* `fwd_ret`: the label, `close` `h` trading days **ahead** divided by today's close, minus 1 (NaN for each ticker's last `h` dates);
* `mom_20`: a feature, today's close divided by the close **20** trading days earlier, minus 1 (NaN for the first 20 dates). It may only use past data.
""",
    setup="""
EXAMPLE = lambda: {"prices": D.prices(seed=0, n_days=25, n_tickers=2), "h": 5}
""",
    tests="""
TESTS = [
    lambda: {"prices": D.prices(seed=1, n_days=60, n_tickers=4), "h": 1},
    lambda: {"prices": D.prices(seed=2, n_days=500, n_tickers=20), "h": 20},
    Test(lambda: {"prices": D.prices(seed=3, n_days=15, n_tickers=3), "h": 5}, "short history"),
]
""",
    hint1="Group by ticker and shift: `g.shift(-h)` looks ahead (labels only), `g.shift(20)` looks back (features).",
    hint2="g = prices.groupby('ticker')['close']\npd.DataFrame({'fwd_ret': g.shift(-h) / prices['close'] - 1, 'mom_20': prices['close'] / g.shift(20) - 1})",
    solution="""
def solve(prices, h):
    g = prices.groupby("ticker")["close"]
    return pd.DataFrame({"fwd_ret": g.shift(-h) / prices["close"] - 1,
                         "mom_20": prices["close"] / g.shift(20) - 1})
""",
    explanation="""
Negative shifts are fine for the **label**, which is what you want to predict, and fatal in a **feature**. Shifting without `groupby` in a long panel pulls in another ticker's price. When labels span `h` days, consecutive labels overlap: leave a gap of `h` periods between train and test (purging/embargo).
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.api.typing.DataFrameGroupBy.shift.html"],
    wrong_solutions=[
        dict(code="""
def solve(prices, h):
    c = prices["close"]
    return pd.DataFrame({"fwd_ret": c.shift(-h) / c - 1, "mom_20": c / c.shift(20) - 1})
""", why="shifts across tickers"),
        dict(code="""
def solve(prices, h):
    g = prices.groupby("ticker")["close"]
    return pd.DataFrame({"fwd_ret": g.shift(-h) / prices["close"] - 1, "mom_20": g.shift(-20) / prices["close"] - 1})
""", why="feature uses the future"),
    ],
),
dict(
    id="qt-010",
    title="Rank IC per date",
    difficulty="Medium",
    tags=["signal evaluation"],
    signature="def solve(panel: pd.DataFrame) -> pd.Series:",
    statement="""
For each date, compute the **Spearman rank correlation** between `momentum` and `fwd_ret` across tickers (pairs with a NaN are ignored). Return the Series of these information coefficients (ICs) indexed by date.
""",
    setup="""
EXAMPLE = lambda: {"panel": D.factor_panel(seed=0, n_dates=4, n_tickers=20)}
""",
    tests="""
TESTS = [
    lambda: {"panel": D.factor_panel(seed=1, n_dates=12, n_tickers=60)},
    lambda: {"panel": D.factor_panel(seed=2, n_dates=60, n_tickers=200, ic=0.15)},
    Test(lambda: {"panel": D.factor_panel(seed=3, n_dates=2, n_tickers=8)}, "few tickers"),
]
""",
    compare=dict(rtol=1e-7, atol=1e-10),
    hint1="`panel.groupby('date')[['momentum', 'fwd_ret']].apply(lambda g: g['momentum'].corr(g['fwd_ret'], method='spearman'))`.",
    hint2="panel.groupby('date')[['momentum', 'fwd_ret']].apply(\n    lambda g: g['momentum'].corr(g['fwd_ret'], method='spearman'))",
    solution="""
def solve(panel):
    return panel.groupby("date")[["momentum", "fwd_ret"]].apply(
        lambda g: g["momentum"].corr(g["fwd_ret"], method="spearman"))
""",
    explanation="""
The rank IC measures whether the signal **orders** next period's returns correctly, robust to outliers and to the signal's scale. Summarize with the mean IC, its t-stat (`mean / std * sqrt(n_dates)`) and the hit rate. Select the columns before `apply` so pandas doesn't pass the grouping column into your function.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.Series.corr.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.api.typing.DataFrameGroupBy.apply.html"],
    wrong_solutions=[
        dict(code="def solve(panel):\n    return panel.groupby('date')[['momentum', 'fwd_ret']].apply(lambda g: g['momentum'].corr(g['fwd_ret']))", why="Pearson"),
        dict(code="def solve(panel):\n    ic = panel['momentum'].corr(panel['fwd_ret'], method='spearman')\n    return pd.Series(ic, index=panel['date'].unique())", why="pooled correlation"),
    ],
),
dict(
    id="qt-011",
    title="Decile long-short spread",
    difficulty="Hard",
    tags=["signal evaluation", "portfolio construction"],
    signature="def solve(panel: pd.DataFrame) -> pd.Series:",
    statement="""
Each date, sort tickers into **deciles** of `momentum` (1 = lowest, 10 = highest; use sample quantiles of that date, ignoring NaN momentum), compute the equal-weighted mean `fwd_ret` of each decile, and return the per-date **long-short spread** `decile 10 - decile 1` as a Series indexed by date.
""",
    setup="""
EXAMPLE = lambda: {"panel": D.factor_panel(seed=0, n_dates=3, n_tickers=40)}
""",
    tests="""
TESTS = [
    lambda: {"panel": D.factor_panel(seed=1, n_dates=12, n_tickers=60)},
    lambda: {"panel": D.factor_panel(seed=2, n_dates=60, n_tickers=300, ic=0.2)},
    Test(lambda: {"panel": D.factor_panel(seed=3, n_dates=1, n_tickers=30)}, "one date"),
]
""",
    hint1="Per-date deciles with `groupby('date')['momentum'].transform(lambda s: pd.qcut(s, 10, labels=False)) + 1`; then mean `fwd_ret` by (date, decile), `unstack()`, and subtract column 1 from column 10.",
    hint2="dec = panel.groupby('date')['momentum'].transform(lambda s: pd.qcut(s, 10, labels=False)) + 1\nm = panel.groupby(['date', dec])['fwd_ret'].mean().unstack()\nm[10] - m[1]",
    solution="""
def solve(panel):
    dec = panel.groupby("date")["momentum"].transform(lambda s: pd.qcut(s, 10, labels=False)) + 1
    m = panel.groupby([panel["date"], dec.rename("decile")])["fwd_ret"].mean().unstack()
    return m[10] - m[1]
""",
    explanation="""
Quantile portfolios are formed **within each date**: deciles over the whole panel would put entire volatile months into the extreme buckets. The top-minus-bottom spread is a rough, market-neutral portfolio return; its mean, t-stat and monotonicity across deciles tell you whether the signal works. Costs and turnover come next.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.qcut.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.api.typing.SeriesGroupBy.transform.html"],
    wrong_solutions=[
        dict(code="""
def solve(panel):
    dec = pd.qcut(panel["momentum"], 10, labels=False) + 1
    m = panel.groupby([panel["date"], dec.rename("decile")])["fwd_ret"].mean().unstack()
    return m[10] - m[1]
""", why="pooled deciles"),
        dict(code="""
def solve(panel):
    dec = panel.groupby("date")["momentum"].transform(lambda s: pd.qcut(s, 10, labels=False)) + 1
    m = panel.groupby([panel["date"], dec.rename("decile")])["fwd_ret"].mean().unstack()
    return m[1] - m[10]
""", why="short-long"),
    ],
),
dict(
    id="qt-012",
    title="Walk-forward splits with an embargo",
    difficulty="Medium",
    tags=["validation"],
    signature="def solve(dates: pd.DatetimeIndex, window: int, gap: int) -> list:",
    statement="""
`dates` are sorted monthly rebalancing dates. Build **rolling** walk-forward splits: for each test date `dates[i]`, train on the `window` dates that end `gap` dates **before** it, i.e. `dates[i - gap - window : i - gap]` (the `gap` dates in between are an embargo, because labels look ahead). Use every test date for which a full window exists, in order.

Return a list of `(train_dates, test_date)` pairs, where `train_dates` is a `DatetimeIndex`.
""",
    setup="""
def make(n, window, gap, start="2015-01-31"):
    return {"dates": pd.date_range(start, periods=n, freq="ME"), "window": window, "gap": gap}

EXAMPLE = lambda: make(8, 3, 1)
""",
    tests="""
TESTS = [
    lambda: make(24, 12, 1),
    lambda: make(120, 36, 3),
    Test(lambda: make(5, 4, 1), "too short: no split"),
    Test(lambda: make(10, 2, 0), "no embargo"),
]
""",
    hint1="Loop `for i in range(window + gap, len(dates))` and slice `dates[i - gap - window : i - gap]`.",
    hint2="[(dates[i - gap - window:i - gap], dates[i]) for i in range(window + gap, len(dates))]",
    solution="""
def solve(dates, window, gap):
    return [(dates[i - gap - window:i - gap], dates[i]) for i in range(window + gap, len(dates))]
""",
    explanation="""
Walk-forward validation retrains as time moves on and only ever tests on the future, mimicking live trading. A **rolling** window adapts to regime changes; an expanding one uses more data. The embargo stops overlapping labels (a 1-month forward return straddles the boundary) from leaking test information into training.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.date_range.html",
          "https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html"],
    wrong_solutions=[
        dict(code="def solve(dates, window, gap):\n    return [(dates[:i - gap], dates[i]) for i in range(window + gap, len(dates))]", why="expanding window"),
        dict(code="def solve(dates, window, gap):\n    return [(dates[i - window:i], dates[i]) for i in range(window, len(dates))]", why="no embargo"),
    ],
),
]
