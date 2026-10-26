SECTION = "stats"

PROBLEMS = [
dict(
    id="st-001",
    title="Did variant B lift revenue per user?",
    difficulty="Medium",
    tags=["hypothesis testing"],
    signature="def solve(ab: pd.DataFrame) -> tuple:",
    statement="""
`ab` has one row per user: `user_id, group ('A' or 'B'), device, converted, revenue, time_on_site`.

Test whether mean `revenue` per user differs between the groups with a two-sided two-sample t-test that does **not** assume equal variances (Welch). Orient it so the statistic is positive when B's mean is higher.

Return `(t_statistic, p_value)` as a tuple of two floats.
""",
    setup="""
EXAMPLE = lambda: {"ab": D.ab_test(seed=0, n=400)}
""",
    tests="""
TESTS = [
    lambda: {"ab": D.ab_test(seed=1, n=1000)},
    lambda: {"ab": D.ab_test(seed=2, n=3000, lift=0.0)},
    Test(lambda: {"ab": D.ab_test(seed=3, n=60, lift=0.08)}, "small sample"),
]
""",
    compare=dict(rtol=1e-6),
    hint1="`scipy.stats.ttest_ind` with `equal_var=False`; pass B first.",
    hint2="from scipy import stats\nres = stats.ttest_ind(b, a, equal_var=False)\nres.statistic, res.pvalue",
    solution="""
from scipy import stats

def solve(ab):
    a = ab.loc[ab["group"] == "A", "revenue"]
    b = ab.loc[ab["group"] == "B", "revenue"]
    res = stats.ttest_ind(b, a, equal_var=False)
    return float(res.statistic), float(res.pvalue)
""",
    explanation="""
Welch's test (`equal_var=False`) is the safer default: revenue is zero-inflated and group variances rarely match, and it loses little power when they do. The sign follows the argument order (`ttest_ind(b, a)` tests mean(b) - mean(a)). With heavy-tailed revenue, a bootstrap or permutation test is a good cross-check.
""",
    docs=["https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ttest_ind.html"],
    wrong_solutions=[
        dict(code="""
from scipy import stats

def solve(ab):
    a = ab.loc[ab["group"] == "A", "revenue"]
    b = ab.loc[ab["group"] == "B", "revenue"]
    res = stats.ttest_ind(b, a)
    return float(res.statistic), float(res.pvalue)
""", why="Student's t-test (equal variances)"),
        dict(code="""
from scipy import stats

def solve(ab):
    a = ab.loc[ab["group"] == "A", "revenue"]
    b = ab.loc[ab["group"] == "B", "revenue"]
    res = stats.ttest_ind(a, b, equal_var=False)
    return float(res.statistic), float(res.pvalue)
""", why="wrong orientation (A - B)"),
    ],
),
dict(
    id="st-002",
    title="Pearson vs Spearman correlation",
    difficulty="Easy",
    tags=["correlation"],
    signature="def solve(x: np.ndarray, y: np.ndarray) -> tuple:",
    statement="""
`y` is a monotonic but non-linear function of `x`, plus noise and a couple of outliers. Return `(pearson_r, spearman_rho)`: the linear (Pearson) correlation and the rank (Spearman) correlation between `x` and `y`, as floats.
""",
    setup="""
def make(seed, n, outliers=2):
    rng = np.random.default_rng(seed)
    x = rng.uniform(0, 5, n)
    y = np.exp(x) + rng.normal(0, 5, n)
    y[rng.choice(n, min(outliers, n), replace=False)] = -200
    return {"x": x, "y": y}

EXAMPLE = lambda: make(0, 30)
""",
    tests="""
TESTS = [
    lambda: make(1, 100),
    lambda: make(2, 3000, outliers=20),
    Test(lambda: make(3, 10, outliers=0), "no outliers"),
]
""",
    hint1="`scipy.stats.pearsonr(x, y)` and `scipy.stats.spearmanr(x, y)` (both return result objects with `.statistic`); or `pd.Series(x).corr(pd.Series(y), method='spearman')`.",
    hint2="stats.pearsonr(x, y).statistic, stats.spearmanr(x, y).statistic",
    solution="""
from scipy import stats

def solve(x, y):
    return float(stats.pearsonr(x, y).statistic), float(stats.spearmanr(x, y).statistic)
""",
    explanation="""
Pearson measures **linear** association and is dragged around by outliers; Spearman is Pearson on ranks, so it captures any monotonic relationship and is robust to outliers. A big gap between them is a hint to transform the variables (log) or look at the scatter plot. Kendall's tau is the other rank-based option.
""",
    docs=["https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.spearmanr.html",
          "https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.pearsonr.html"],
    wrong_solutions=[
        dict(code="from scipy import stats\n\ndef solve(x, y):\n    r = stats.pearsonr(x, y).statistic\n    return float(r), float(r)", why="Pearson twice"),
        dict(code="from scipy import stats\n\ndef solve(x, y):\n    return float(stats.pearsonr(x, y).statistic), float(stats.kendalltau(x, y).statistic)", why="Kendall, not Spearman"),
    ],
),
dict(
    id="st-003",
    title="Chi-square test of independence",
    difficulty="Medium",
    tags=["hypothesis testing"],
    signature="def solve(churn: pd.DataFrame, col: str) -> tuple:",
    statement="""
Is churning independent of the categorical column `col`? Build the contingency table of `col` (rows) by `churned` (columns) from the raw counts and run a chi-square test of independence with scipy's defaults (which apply Yates' continuity correction to 2 x 2 tables). Return `(chi2, p_value, dof)`.
""",
    setup="""
EXAMPLE = lambda: {"churn": D.churn(seed=0, n=300), "col": "contract"}
""",
    tests="""
TESTS = [
    lambda: {"churn": D.churn(seed=1, n=1000), "col": "internet"},
    lambda: {"churn": D.churn(seed=2, n=3000), "col": "payment_method"},
    Test(lambda: {"churn": D.churn(seed=3, n=400), "col": "senior"}, "2 x 2 table"),
]
""",
    hint1="`scipy.stats.chi2_contingency(pd.crosstab(df[col], df['churned']))` returns the statistic, p-value, dof and expected counts.",
    hint2="res = stats.chi2_contingency(pd.crosstab(churn[col], churn['churned']))\nres.statistic, res.pvalue, res.dof",
    solution="""
from scipy import stats

def solve(churn, col):
    res = stats.chi2_contingency(pd.crosstab(churn[col], churn["churned"]))
    return float(res.statistic), float(res.pvalue), int(res.dof)
""",
    explanation="""
The test compares observed counts to those expected under independence. It needs **counts**, not proportions (a normalized crosstab gives a meaningless statistic), and expected counts of roughly 5 or more per cell. `res.expected_freq` shows them. A significant result says *that* the variables are related, not how strongly: report Cramer's V or the churn rate per level too.
""",
    docs=["https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.chi2_contingency.html"],
    wrong_solutions=[
        dict(code="from scipy import stats\n\ndef solve(churn, col):\n    res = stats.chi2_contingency(pd.crosstab(churn[col], churn['churned'], normalize=True))\n    return float(res.statistic), float(res.pvalue), int(res.dof)", why="proportions instead of counts"),
        dict(code="from scipy import stats\n\ndef solve(churn, col):\n    res = stats.chi2_contingency(pd.crosstab(churn[col], churn['churned']), correction=False)\n    return float(res.statistic), float(res.pvalue), int(res.dof)", why="no continuity correction on 2 x 2"),
    ],
),
dict(
    id="st-004",
    title="Bootstrap confidence interval for the median",
    difficulty="Medium",
    tags=["resampling"],
    allow_in_statement=["default_rng"],
    signature="def solve(x: np.ndarray, n_boot: int, seed: int) -> tuple:",
    statement="""
Compute a 95% **percentile bootstrap** confidence interval for the **median** of `x`: draw `n_boot` resamples of `x` with replacement (each the size of `x`) using `np.random.default_rng(seed)`, take the median of each, and return the 2.5th and 97.5th percentiles of those medians as `(lo, hi)`.

Any correct resampling scheme passes: the test checks the interval against the reference with a Monte Carlo tolerance.
""",
    setup="""
def make(seed, n, n_boot=2000):
    rng = np.random.default_rng(seed + 100)
    return {"x": np.round(rng.lognormal(4, 0.9, n), 2), "n_boot": n_boot, "seed": seed}

EXAMPLE = lambda: make(0, 40)
""",
    tests="""
TESTS = [
    lambda: make(1, 100),
    lambda: make(2, 1000, n_boot=3000),
    Test(lambda: make(3, 25), "small sample"),
]

def check(got, exp, inputs):
    if not isinstance(got, (tuple, list)) or len(got) != 2:
        fail("return a tuple (lo, hi)")
    lo, hi = (float(v) for v in got)
    elo, ehi = exp
    width = ehi - elo
    if not lo <= np.median(inputs["x"]) <= hi:
        fail(f"the interval ({lo:.3f}, {hi:.3f}) does not contain the sample median")
    if abs(lo - elo) > 0.25 * width or abs(hi - ehi) > 0.25 * width:
        fail(f"interval ({lo:.3f}, {hi:.3f}) is far from the expected ({elo:.3f}, {ehi:.3f}): "
             "median of resamples with replacement, 2.5th/97.5th percentiles?")
""",
    hint1="Draw an `(n_boot, n)` matrix with `rng.choice(x, size=..., replace=True)`, take `np.median(..., axis=1)`, then `np.percentile(meds, [2.5, 97.5])`.",
    hint2="rng = np.random.default_rng(seed)\nmeds = np.median(rng.choice(x, size=(n_boot, len(x)), replace=True), axis=1)\nnp.percentile(meds, [2.5, 97.5])",
    solution="""
def solve(x, n_boot, seed):
    rng = np.random.default_rng(seed)
    meds = np.median(rng.choice(x, size=(n_boot, len(x)), replace=True), axis=1)
    lo, hi = np.percentile(meds, [2.5, 97.5])
    return float(lo), float(hi)
""",
    explanation="""
The bootstrap treats the sample as the population: resampling with replacement approximates the sampling distribution of any statistic, including ones without a formula (median, ratios, Sharpe ratios). The percentile interval is the simplest; BCa intervals (`scipy.stats.bootstrap`) correct for bias and skew.
""",
    docs=["https://numpy.org/doc/stable/reference/random/generated/numpy.random.Generator.choice.html",
          "https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html"],
    wrong_solutions=[
        dict(code="def solve(x, n_boot, seed):\n    rng = np.random.default_rng(seed)\n    m = rng.choice(x, size=(n_boot, len(x)), replace=True).mean(axis=1)\n    lo, hi = np.percentile(m, [2.5, 97.5])\n    return float(lo), float(hi)", why="interval for the mean"),
        dict(code="def solve(x, n_boot, seed):\n    rng = np.random.default_rng(seed)\n    meds = np.median(rng.choice(x, size=(n_boot, len(x)), replace=True), axis=1)\n    lo, hi = np.percentile(meds, [25, 75])\n    return float(lo), float(hi)", why="50% interval"),
    ],
),
dict(
    id="st-005",
    title="Permutation test for a difference in means",
    difficulty="Hard",
    tags=["resampling", "hypothesis testing"],
    allow_in_statement=["default_rng"],
    signature="def solve(a: np.ndarray, b: np.ndarray, n_perm: int, seed: int) -> float:",
    statement="""
Test whether two groups have different means without distributional assumptions. The observed statistic is `|mean(b) - mean(a)|`. Using `np.random.default_rng(seed)`, shuffle the pooled values `n_perm` times, splitting each shuffle into groups of the original sizes, and return the two-sided p-value

`p = (1 + number of permutations with |diff| >= observed) / (1 + n_perm)`.

The test checks the p-value against the reference with a Monte Carlo tolerance (±0.03).
""",
    setup="""
def make(seed, na, nb, shift, n_perm=2000):
    rng = np.random.default_rng(seed + 7)
    return {"a": rng.exponential(10, na), "b": rng.exponential(10, nb) + shift, "n_perm": n_perm, "seed": seed}

EXAMPLE = lambda: make(0, 30, 35, 3.0)
""",
    tests="""
TESTS = [
    lambda: make(1, 50, 40, 3.5),
    lambda: make(2, 200, 220, 1.2, n_perm=3000),
    Test(lambda: make(3, 15, 12, 0.0), "no true difference"),
]

def check(got, exp, inputs):
    try:
        p = float(got)
    except Exception:
        fail(f"return the p-value as a float, got {type(got).__name__}")
    if not 0 < p <= 1:
        fail(f"a p-value must be in (0, 1], got {p}")
    if abs(p - exp) > 0.03:
        fail(f"p = {p:.4f} is far from the expected {exp:.4f}: two-sided |diff|? shuffled the pooled sample?")
""",
    hint1="Concatenate, then in a loop (or vectorized) `rng.permutation(pooled)`, split at `len(a)`, and compare `abs(diff)` with the observed `abs(diff)`.",
    hint2="pooled = np.concatenate([a, b])\nobs = abs(b.mean() - a.mean())\nfor _ in range(n_perm):\n    p = rng.permutation(pooled)\n    hits += abs(p[len(a):].mean() - p[:len(a)].mean()) >= obs\n(1 + hits) / (1 + n_perm)",
    solution="""
def solve(a, b, n_perm, seed):
    rng = np.random.default_rng(seed)
    pooled, k = np.concatenate([a, b]), len(a)
    obs = abs(b.mean() - a.mean())
    perms = np.array([rng.permutation(pooled) for _ in range(n_perm)])
    diffs = np.abs(perms[:, k:].mean(axis=1) - perms[:, :k].mean(axis=1))
    return float((1 + (diffs >= obs).sum()) / (1 + n_perm))
""",
    explanation="""
Under the null hypothesis the group labels are exchangeable, so shuffling them generates the null distribution of the statistic directly. The `+1` in numerator and denominator counts the observed split itself and avoids a p-value of exactly 0. `scipy.stats.permutation_test` implements this, including exact enumeration for tiny samples.
""",
    docs=["https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.permutation_test.html",
          "https://numpy.org/doc/stable/reference/random/generated/numpy.random.Generator.permutation.html"],
    wrong_solutions=[
        dict(code="""
def solve(a, b, n_perm, seed):
    rng = np.random.default_rng(seed)
    pooled, k = np.concatenate([a, b]), len(a)
    obs = b.mean() - a.mean()
    perms = np.array([rng.permutation(pooled) for _ in range(n_perm)])
    diffs = perms[:, k:].mean(axis=1) - perms[:, :k].mean(axis=1)
    return float((1 + (diffs >= obs).sum()) / (1 + n_perm))
""", why="one-sided"),
        dict(code="""
def solve(a, b, n_perm, seed):
    rng = np.random.default_rng(seed)
    obs = abs(b.mean() - a.mean())
    diffs = np.array([abs(rng.permutation(b).mean() - rng.permutation(a).mean()) for _ in range(n_perm)])
    return float((1 + (diffs >= obs).sum()) / (1 + n_perm))
""", why="shuffles within groups: no null distribution"),
    ],
),
dict(
    id="st-006",
    title="OLS with statsmodels: coefficients, t-stats, R²",
    difficulty="Medium",
    tags=["regression"],
    signature="def solve(hr: pd.DataFrame) -> tuple:",
    statement="""
Regress `salary` on `years_experience` and `performance` **with an intercept** using statsmodels OLS (drop rows with a missing salary first). Return `(params, tvalues, rsquared)`, where `params` and `tvalues` are Series indexed `['const', 'years_experience', 'performance']`.
""",
    setup="""
EXAMPLE = lambda: {"hr": D.hr(seed=0, n=40)}
""",
    tests="""
TESTS = [
    lambda: {"hr": D.hr(seed=1, n=200)},
    lambda: {"hr": D.hr(seed=2, n=3000)},
    Test(lambda: {"hr": D.hr(seed=3, n=12, missing_share=0.2)}, "few rows"),
]
""",
    compare=dict(rtol=1e-6, atol=1e-8),
    hint1="`sm.OLS(y, sm.add_constant(X)).fit()` (statsmodels does **not** add an intercept for you); the result has `.params`, `.tvalues`, `.rsquared`.",
    hint2="import statsmodels.api as sm\nres = sm.OLS(d['salary'], sm.add_constant(d[['years_experience', 'performance']])).fit()\nres.params, res.tvalues, res.rsquared",
    solution="""
import statsmodels.api as sm

def solve(hr):
    d = hr.dropna(subset=["salary"])
    res = sm.OLS(d["salary"], sm.add_constant(d[["years_experience", "performance"]])).fit()
    return res.params, res.tvalues, float(res.rsquared)
""",
    explanation="""
Unlike scikit-learn, `sm.OLS` fits exactly the columns you give it, so forget `add_constant` and the line is forced through the origin (and R² is computed uncentered). The formula API adds the intercept automatically: `smf.ols('salary ~ years_experience + performance', d).fit()`. `res.summary()` prints the full table.
""",
    docs=["https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.OLS.html",
          "https://www.statsmodels.org/stable/generated/statsmodels.tools.tools.add_constant.html"],
    wrong_solutions=[
        dict(code="""
import statsmodels.api as sm

def solve(hr):
    d = hr.dropna(subset=["salary"])
    res = sm.OLS(d["salary"], d[["years_experience", "performance"]]).fit()
    return res.params, res.tvalues, float(res.rsquared)
""", why="no intercept"),
        dict(code="""
import statsmodels.api as sm

def solve(hr):
    d = hr.dropna(subset=["salary"])
    res = sm.OLS(d["salary"], sm.add_constant(d[["years_experience", "performance"]])).fit()
    return res.params, res.bse, float(res.rsquared_adj)
""", why="standard errors and adjusted R²"),
    ],
),
dict(
    id="st-007",
    title="Newey-West standard errors",
    difficulty="Hard",
    tags=["regression", "time series"],
    signature="def solve(y: pd.Series, x: pd.Series, lags: int) -> pd.Series:",
    statement="""
`y` and `x` are daily series whose regression errors are **autocorrelated** (e.g. overlapping returns), so plain OLS standard errors are too small. Regress `y` on `x` with an intercept and return the **HAC (Newey-West)** standard errors with `maxlags=lags`, as a Series indexed `['const', x.name]`.
""",
    setup="""
def make(seed, n, phi=0.7, lags=5):
    rng = np.random.default_rng(seed)
    e = np.zeros(n)
    for t in range(1, n):
        e[t] = phi * e[t - 1] + rng.normal()
    xv = np.convolve(rng.normal(size=n + 9), np.ones(10) / 10, mode="valid")[:n]
    idx = pd.bdate_range("2020-01-01", periods=n)
    return {"y": pd.Series(0.1 + 0.5 * xv + e, index=idx, name="y"), "x": pd.Series(xv, index=idx, name="signal"), "lags": lags}

EXAMPLE = lambda: make(0, 120)
""",
    tests="""
TESTS = [
    lambda: make(1, 500, lags=10),
    lambda: make(2, 2000, phi=0.9, lags=20),
    Test(lambda: make(3, 60, phi=0.0, lags=2), "no autocorrelation"),
]
""",
    compare=dict(rtol=1e-6, atol=1e-10),
    hint1="`.fit(cov_type='HAC', cov_kwds={'maxlags': lags})`, then `.bse`.",
    hint2="sm.OLS(y, sm.add_constant(x)).fit(cov_type='HAC', cov_kwds={'maxlags': lags}).bse",
    solution="""
import statsmodels.api as sm

def solve(y, x, lags):
    return sm.OLS(y, sm.add_constant(x)).fit(cov_type="HAC", cov_kwds={"maxlags": lags}).bse
""",
    explanation="""
HAC (heteroskedasticity- and autocorrelation-consistent) errors keep the OLS point estimates but widen the uncertainty to account for serially correlated residuals: the standard fix for overlapping-horizon return regressions. Choose `maxlags` at least the overlap length (e.g. h - 1 for h-day returns).
""",
    docs=["https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.OLS.fit.html",
          "https://www.statsmodels.org/stable/generated/statsmodels.stats.sandwich_covariance.cov_hac.html"],
    wrong_solutions=[
        dict(code="import statsmodels.api as sm\n\ndef solve(y, x, lags):\n    return sm.OLS(y, sm.add_constant(x)).fit().bse", why="plain OLS errors"),
        dict(code="import statsmodels.api as sm\n\ndef solve(y, x, lags):\n    return sm.OLS(y, sm.add_constant(x)).fit(cov_type='HC1').bse", why="heteroskedasticity-robust only"),
    ],
),
dict(
    id="st-008",
    title="Autocorrelation of returns",
    difficulty="Medium",
    tags=["time series", "correlation"],
    signature="def solve(r: pd.Series, max_lag: int) -> pd.Series:",
    statement="""
Return the autocorrelation of the return series `r` at lags `1..max_lag`, defined as the **Pearson correlation between r(t) and r(t-k) over the overlapping observations**, as a Series indexed by the lag (1..max_lag).
""",
    setup="""
def make(seed, n, phi):
    rng = np.random.default_rng(seed)
    e = rng.normal(0, 0.01, n)
    r = np.zeros(n)
    for t in range(n):
        r[t] = (phi * r[t - 1] if t else 0) + e[t]
    return pd.Series(r, index=pd.bdate_range("2021-01-01", periods=n), name="ret")

EXAMPLE = lambda: {"r": make(0, 100, 0.3), "max_lag": 3}
""",
    tests="""
TESTS = [
    lambda: {"r": make(1, 500, -0.2), "max_lag": 5},
    lambda: {"r": make(2, 3000, 0.05), "max_lag": 10},
    Test(lambda: {"r": make(3, 30, 0.6), "max_lag": 2}, "short series"),
]
""",
    compare=dict(rtol=1e-8, atol=1e-12),
    hint1="`Series.autocorr(lag=k)` is exactly this definition; loop over the lags.",
    hint2="pd.Series({k: r.autocorr(lag=k) for k in range(1, max_lag + 1)})",
    solution="""
def solve(r, max_lag):
    return pd.Series({k: r.autocorr(lag=k) for k in range(1, max_lag + 1)})
""",
    explanation="""
`autocorr(k)` correlates the series with `shift(k)` over overlapping points. `statsmodels.tsa.stattools.acf` uses the full-sample mean and variance instead (the textbook estimator), so its values differ slightly, especially for short series. Know which one a question means. `plot_acf` adds confidence bands.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.Series.autocorr.html",
          "https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.acf.html"],
    wrong_solutions=[
        dict(code="""
from statsmodels.tsa.stattools import acf

def solve(r, max_lag):
    return pd.Series(acf(r, nlags=max_lag)[1:], index=range(1, max_lag + 1))
""", why="statsmodels' full-sample estimator"),
        dict(code="def solve(r, max_lag):\n    return pd.Series({k: r.corr(r.shift(-k + 1)) for k in range(1, max_lag + 1)})", why="off-by-one lag"),
    ],
),
]
