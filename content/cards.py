"""Flashcard content.

RECALL_EXTRA: recall cards for common syntax not covered by a problem
(front = one-line task, back = the idiomatic one-liner). One recall card per
problem is generated automatically from its title (or `recall`) and Hint 2.

PREDICT: predict-the-output cards. `code` runs at build time (like a REPL
cell: the repr of a final expression is shown, after anything printed) and
the captured output becomes the answer, so answers are never written by hand.
Keep snippets tiny and focused on one gotcha. `note` explains the answer.
"""

RECALL_EXTRA = [
    dict(id="rx-001", section="pandas", front="Read only the first 1,000 rows of a big CSV", back="pd.read_csv(path, nrows=1000)"),
    dict(id="rx-002", section="pandas", front="Process a huge CSV in chunks of 100k rows", back="for chunk in pd.read_csv(path, chunksize=100_000):\n    process(chunk)"),
    dict(id="rx-003", section="pandas", front="Write a DataFrame to CSV without the index", back="df.to_csv('out.csv', index=False)"),
    dict(id="rx-004", section="pandas", front="Rename some columns", back="df.rename(columns={'old': 'new'})"),
    dict(id="rx-005", section="pandas", front="Normalize all column names to snake_case", back="df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')"),
    dict(id="rx-006", section="pandas", front="Drop two columns", back="df.drop(columns=['a', 'b'])"),
    dict(id="rx-007", section="pandas", front="Keep only the numeric columns", back="df.select_dtypes(include='number')"),
    dict(id="rx-008", section="pandas", front="Move a column into the index, and back", back="df.set_index('id')\ndf.reset_index()"),
    dict(id="rx-009", section="pandas", front="Memory usage including string contents", back="df.info(memory_usage='deep')"),
    dict(id="rx-010", section="pandas", front="Apply a function element-wise to a whole DataFrame (pandas >= 2.1)", back="df.map(f)   # formerly applymap"),
    dict(id="rx-011", section="pandas", front="Correlation of every column with the target", back="df.corrwith(df['y'])"),
    dict(id="rx-012", section="pandas", front="Reproducible 10% sample of the rows", back="df.sample(frac=0.1, random_state=0)"),
    dict(id="rx-013", section="pandas", front="Shuffle all rows", back="df.sample(frac=1, random_state=0).reset_index(drop=True)"),
    dict(id="rx-014", section="pandas", front="Lag a column by one row within each group", back="df.groupby('id')['x'].shift(1)"),
    dict(id="rx-015", section="pandas", front="ISO week number of a datetime column", back="df['ts'].dt.isocalendar().week"),
    dict(id="rx-016", section="pandas", front="Floor timestamps to the hour", back="df['ts'].dt.floor('h')"),
    dict(id="rx-017", section="pandas", front="Make naive timestamps UTC, then show them in Paris time", back="s.dt.tz_localize('UTC').dt.tz_convert('Europe/Paris')"),
    dict(id="rx-018", section="pandas", front="Glue two frames side by side on the index", back="pd.concat([a, b], axis=1)"),
    dict(id="rx-019", section="pandas", front="Join another frame on the index", back="left.join(right, how='left')"),
    dict(id="rx-020", section="pandas", front="All combinations of two tables (cross join)", back="left.merge(right, how='cross')"),
    dict(id="rx-021", section="pandas", front="Flatten MultiIndex columns after an aggregation", back="df.columns = ['_'.join(map(str, c)) for c in df.columns]"),
    dict(id="rx-022", section="pandas", front="Replace +/-inf with NaN everywhere", back="df.replace([np.inf, -np.inf], np.nan)"),
    dict(id="rx-023", section="pandas", front="Rows that have at least one missing value", back="df[df.isna().any(axis=1)]"),
    dict(id="rx-024", section="pandas", front="Forward-fill within each group", back="df.groupby('id')['x'].ffill()"),
    dict(id="rx-025", section="pandas", front="60-day rolling correlation between two series", back="s1.rolling(60).corr(s2)"),
    dict(id="rx-026", section="pandas", front="Several aggregations of one column, as columns", back="df.groupby('g')['x'].agg(['mean', 'std', 'count'])"),
    dict(id="rx-027", section="pandas", front="Percentage of the column total per row", back="df['x'] / df['x'].sum()"),
    dict(id="rx-028", section="numpy", front="Indices where a condition holds", back="np.flatnonzero(x > 0)"),
    dict(id="rx-029", section="numpy", front="Repeat each element 3 times / the whole array 3 times", back="np.repeat(a, 3)\nnp.tile(a, 3)"),
    dict(id="rx-030", section="numpy", front="Column index of each row's maximum", back="X.argmax(axis=1)"),
    dict(id="rx-031", section="numpy", front="Save and reload an array", back="np.save('x.npy', x)\nx = np.load('x.npy')"),
    dict(id="rx-032", section="numpy", front="Reproducible random normals without global state", back="rng = np.random.default_rng(42)\nrng.normal(size=5)"),
    dict(id="rx-033", section="numpy", front="Check two float arrays are equal within tolerance", back="np.allclose(a, b, rtol=1e-5, atol=1e-8)"),
    dict(id="rx-034", section="numpy", front="Concatenate along rows / columns", back="np.concatenate([a, b], axis=0)\nnp.hstack([a, b])"),
    dict(id="rx-035", section="sklearn", front="Save a fitted model and load it back", back="joblib.dump(model, 'model.joblib')\nmodel = joblib.load('model.joblib')"),
    dict(id="rx-036", section="sklearn", front="List every tunable parameter name of a pipeline", back="pipe.get_params().keys()"),
    dict(id="rx-037", section="sklearn", front="Macro-averaged F1 for multiclass", back="f1_score(y_true, y_pred, average='macro')"),
    dict(id="rx-038", section="sklearn", front="Accuracy that isn't fooled by class imbalance", back="balanced_accuracy_score(y_true, y_pred)"),
    dict(id="rx-039", section="sklearn", front="Calibrate a classifier's probabilities", back="CalibratedClassifierCV(model, method='isotonic', cv=5)"),
    dict(id="rx-040", section="sklearn", front="Model a skewed target on the log scale (and predict back in original units)", back="TransformedTargetRegressor(regressor=Ridge(), func=np.log1p, inverse_func=np.expm1)"),
    dict(id="rx-041", section="sklearn", front="Area under the precision-recall curve", back="average_precision_score(y_true, scores)"),
    dict(id="rx-042", section="plotting", front="Save a figure for a report", back="fig.savefig('plot.png', dpi=150, bbox_inches='tight')"),
    dict(id="rx-043", section="plotting", front="Rotate the x tick labels by 45 degrees", back="ax.tick_params(axis='x', labelrotation=45)"),
    dict(id="rx-044", section="plotting", front="Set both axis limits at once", back="ax.set(xlim=(0, 10), ylim=(0, 1))"),
    dict(id="rx-045", section="plotting", front="Pairwise scatter matrix coloured by a class", back="sns.pairplot(df, hue='target')"),
    dict(id="rx-046", section="plotting", front="Avoid overlapping labels in a multi-panel figure", back="fig, axes = plt.subplots(2, 2, layout='constrained')"),
    dict(id="rx-047", section="stats", front="OLS with a categorical regressor via a formula", back="smf.ols('y ~ x + C(group)', data=df).fit()"),
    dict(id="rx-048", section="stats", front="One-sample t-test that the mean is 0", back="stats.ttest_1samp(x, popmean=0)"),
    dict(id="rx-049", section="stats", front="Non-parametric test that two samples differ", back="stats.mannwhitneyu(a, b)"),
    dict(id="rx-050", section="stats", front="Two-proportion z-test for conversion rates", back="from statsmodels.stats.proportion import proportions_ztest\nproportions_ztest(count=[x1, x2], nobs=[n1, n2])"),
]

PREDICT = [
    # ---------------------------------------------------------------- pandas: groupby
    dict(id="po-001", section="pandas", topic="transform vs agg", code="""
df = pd.DataFrame({"g": ["a", "a", "b"], "x": [1, 2, 3]})
print(df.groupby("g")["x"].agg("sum").shape)
print(df.groupby("g")["x"].transform("sum").shape)
""", note="`agg` returns one row per group; `transform` returns one value per original row, aligned to the input index."),
    dict(id="po-002", section="pandas", topic="transform vs agg", code="""
df = pd.DataFrame({"g": ["a", "a", "b"], "x": [1, 2, 3]})
df["share"] = df["x"] / df.groupby("g")["x"].sum()
df
""", note="Dividing by the aggregated Series aligns on the **index** (0, 1, 2 vs 'a', 'b'): nothing matches, so every value is NaN. Use `transform('sum')`."),
    dict(id="po-003", section="pandas", topic="NaN group keys", code="""
df = pd.DataFrame({"k": ["x", None, "x", None], "v": [1, 2, 3, 4]})
df.groupby("k")["v"].sum()
""", note="Rows whose key is missing are dropped by default. Pass `dropna=False` to keep a NaN group."),
    dict(id="po-004", section="pandas", topic="size vs count", code="""
df = pd.DataFrame({"g": ["a", "a", "b"], "x": [1.0, None, 3.0]})
g = df.groupby("g")["x"]
print(g.size().tolist(), g.count().tolist())
""", note="`size` counts rows; `count` counts non-missing values."),
    dict(id="po-005", section="pandas", topic="as_index", code="""
df = pd.DataFrame({"g": ["b", "a", "b"], "x": [1, 2, 3]})
df.groupby("g", as_index=False)["x"].sum()
""", note="`as_index=False` keeps the key as a column, and groups come out **sorted** by key (`sort=False` keeps first-seen order)."),
    dict(id="po-006", section="pandas", topic="categorical groupby", code="""
s = pd.Series(pd.Categorical(["a", "a"], categories=["a", "b"]))
pd.DataFrame({"c": s, "v": [1, 2]}).groupby("c")["v"].sum()
""", note="pandas 3 changed the default to `observed=True`: categories with no rows are no longer listed (pandas 2 showed `b` with 0, plus a FutureWarning)."),
    dict(id="po-007", section="pandas", topic="cumcount", code="""
df = pd.DataFrame({"user": ["u1", "u2", "u1", "u1"]})
df.groupby("user").cumcount().tolist()
""", note="`cumcount` numbers rows within each group from 0, in the current row order."),
    # ---------------------------------------------------------------- pandas: merge
    dict(id="po-008", section="pandas", topic="merge with duplicate keys", code="""
left = pd.DataFrame({"k": [1, 1, 2], "a": ["x", "y", "z"]})
right = pd.DataFrame({"k": [1, 1, 3], "b": ["p", "q", "r"]})
len(left.merge(right, on="k"))
""", note="Each left row with key 1 matches each right row with key 1: 2 x 2 = 4 rows; key 2 and 3 don't match (inner join)."),
    dict(id="po-009", section="pandas", topic="merge with duplicate keys", code="""
left = pd.DataFrame({"k": [1, 2], "a": [10, 20]})
right = pd.DataFrame({"k": [1, 1], "b": [7, 8]})
len(left.merge(right, on="k", how="left"))
""", note="A **left** join can still return more rows than the left table when right keys repeat. `validate='many_to_one'` would raise."),
    dict(id="po-010", section="pandas", topic="merge suffixes", code="""
a = pd.DataFrame({"id": [1], "v": [10]})
b = pd.DataFrame({"id": [1], "v": [20]})
a.merge(b, on="id").columns.tolist()
""", note="Overlapping non-key columns get `_x` / `_y` suffixes; change them with `suffixes=('_left', '_right')`."),
    dict(id="po-011", section="pandas", topic="merge on NaN keys", code="""
a = pd.DataFrame({"k": [1.0, np.nan], "a": [1, 2]})
b = pd.DataFrame({"k": [np.nan], "b": [9]})
a.merge(b, on="k")
""", note="Unlike SQL, pandas **matches NaN keys with each other** in merges. Drop or fill missing keys first."),
    dict(id="po-012", section="pandas", topic="concat index", code="""
a = pd.DataFrame({"x": [1, 2]})
b = pd.DataFrame({"x": [3]})
pd.concat([a, b]).index.tolist()
""", note="`concat` keeps the original labels, so the index has duplicates; pass `ignore_index=True` for 0..n-1."),
    # ---------------------------------------------------------------- pandas: shift / time
    dict(id="po-013", section="pandas", topic="shift direction", code="""
s = pd.Series([10, 20, 30])
print(s.shift(1).tolist())
print(s.shift(-1).tolist())
""", note="`shift(1)` moves values **down**: each row sees the previous one (the past). `shift(-1)` brings the next row up (the future)."),
    dict(id="po-014", section="pandas", topic="pct_change", code="""
s = pd.Series([100.0, 110.0, 99.0])
s.pct_change().round(4).tolist()
""", note="`pct_change` = x / x.shift(1) - 1, NaN on the first row."),
    dict(id="po-015", section="pandas", topic="rolling warm-up", code="""
s = pd.Series([1.0, 2.0, 3.0, 4.0])
print(s.rolling(3).mean().tolist())
print(s.rolling(3, min_periods=1).mean().tolist())
""", note="By default a window needs all of its observations, so the first `window - 1` results are NaN."),
    dict(id="po-016", section="pandas", topic="diff", code="""
s = pd.Series([5, 8, 6])
s.diff().tolist()
""", note="`diff()` is x - x.shift(1); the result is float because of the leading NaN."),
    dict(id="po-017", section="pandas", topic="resample labels", code="""
s = pd.Series(1, index=pd.date_range("2024-01-30", periods=4, freq="D"))
s.resample("ME").sum()
""", note="`'ME'` buckets by calendar month and labels each bucket by its **month end**."),
    dict(id="po-018", section="pandas", topic="date_range", code="""
pd.date_range("2024-01-31", periods=3, freq="ME").strftime("%Y-%m-%d").tolist()
""", note="Month-end frequency handles different month lengths (and leap years) for you."),
    dict(id="po-019", section="pandas", topic="cumsum and NaN", code="""
pd.Series([1, np.nan, 2]).cumsum().tolist()
""", note="Cumulative functions skip NaN (the position stays NaN) and keep accumulating afterwards."),
    # ---------------------------------------------------------------- pandas: binning
    dict(id="po-020", section="pandas", topic="cut edges", code="""
pd.cut([0, 5, 10], bins=[0, 5, 10]).astype(str).tolist()
""", note="Bins are right-closed `(a, b]` by default, so the left edge 0 falls outside every bin (NaN)."),
    dict(id="po-021", section="pandas", topic="cut edges", code="""
pd.cut([0, 5, 10], bins=[0, 5, 10], right=False).astype(str).tolist()
""", note="With `right=False` bins are `[a, b)`: now 0 is in, but the top edge 10 falls out."),
    dict(id="po-022", section="pandas", topic="cut include_lowest", code="""
pd.cut([0, 5, 10], bins=[0, 5, 10], include_lowest=True).astype(str).tolist()
""", note="`include_lowest=True` makes the first interval closed on the left too."),
    dict(id="po-023", section="pandas", topic="qcut vs cut", code="""
x = pd.Series([1, 2, 3, 4, 100])
print(pd.cut(x, 2, labels=False).tolist())
print(pd.qcut(x, 2, labels=False).tolist())
""", note="`cut` splits the **range** into equal widths (the outlier gets a bin to itself); `qcut` splits by **quantiles** (equal counts)."),
    # ---------------------------------------------------------------- pandas: counting/sorting
    dict(id="po-024", section="pandas", topic="value_counts sorting", code="""
pd.Series(["b", "a", "b", "c", "a", "b"]).value_counts()
""", note="`value_counts` sorts by count, descending; use `.sort_index()` for label order."),
    dict(id="po-025", section="pandas", topic="value_counts and NaN", code="""
s = pd.Series(["x", None, "x"])
print(s.value_counts().to_dict())
print(s.value_counts(dropna=False).to_dict())
""", note="Missing values are excluded unless `dropna=False`."),
    dict(id="po-026", section="pandas", topic="nunique and NaN", code="""
pd.Series([1, 1, np.nan, 2]).nunique()
""", note="`nunique` ignores NaN by default (`dropna=False` counts it)."),
    dict(id="po-027", section="pandas", topic="rank methods", code="""
s = pd.Series([10, 20, 20, 30])
print(s.rank().tolist())
print(s.rank(method="min").tolist())
print(s.rank(method="first").tolist())
""", note="Default `average` shares tied ranks; `min` is competition ranking; `first` breaks ties by position."),
    dict(id="po-028", section="pandas", topic="sort and NaN", code="""
pd.Series([3, np.nan, 1]).sort_values().tolist()
""", note="NaN goes last whatever the direction (`na_position='first'` to change it)."),
    dict(id="po-029", section="pandas", topic="drop_duplicates keep", code="""
df = pd.DataFrame({"id": [1, 1, 2], "v": ["old", "new", "x"]})
df.drop_duplicates("id", keep="last")["v"].tolist()
""", note="`subset` defines duplicates; `keep` decides which copy survives (by row position)."),
    # ---------------------------------------------------------------- pandas: indexing
    dict(id="po-030", section="pandas", topic="loc vs iloc", code="""
s = pd.Series([10, 20, 30], index=[2, 0, 1])
print(s.loc[0], s.iloc[0])
""", note="`loc` uses **labels** (label 0 is the second element); `iloc` uses **positions**."),
    dict(id="po-031", section="pandas", topic="slice ends", code="""
s = pd.Series([1, 2, 3, 4], index=["a", "b", "c", "d"])
print(s.loc["a":"c"].tolist())
print(s.iloc[0:2].tolist())
""", note="Label slices **include** the end label; positional slices exclude the end, like Python lists."),
    dict(id="po-032", section="pandas", topic="integer index []", code="""
s = pd.Series([10, 20, 30], index=[1, 2, 3])
s[1]
""", note="With an integer index, `s[1]` is a **label** lookup. Write `.loc` or `.iloc` to be explicit."),
    dict(id="po-033", section="pandas", topic="boolean logic", code="""
s = pd.Series([1, 5, 9])
try:
    s[s > 2 and s < 8]
except ValueError as e:
    print("ValueError:", str(e)[:45])
s[(s > 2) & (s < 8)].tolist()
""", note="`and`/`or` need a single True/False; element-wise logic needs `&`, `|`, `~`, with parentheses."),
    dict(id="po-034", section="pandas", topic="isin and NaN", code="""
pd.Series([1.0, np.nan]).isin([np.nan]).tolist()
""", note="`isin` treats NaN as matching NaN, unlike `==`."),
    dict(id="po-035", section="pandas", topic="NaN comparisons", code="""
s = pd.Series([1.0, np.nan])
print((s == np.nan).tolist())
print(s.isna().tolist())
""", note="NaN is never equal to anything, itself included: always use `isna()`."),
    # ---------------------------------------------------------------- pandas: copies & dtypes
    dict(id="po-036", section="pandas", topic="copy-on-write", code="""
df = pd.DataFrame({"a": [1, 2, 3]})
sub = df[df["a"] > 1]
sub["a"] = 0
df["a"].tolist()
""", note="Since Copy-on-Write (pandas 3), a selection behaves like a copy: modifying `sub` never changes `df`. Use `df.loc[mask, 'a'] = 0`."),
    dict(id="po-037", section="pandas", topic="chained assignment", code="""
import warnings
df = pd.DataFrame({"a": [1, 2, 3], "b": [0, 0, 0]})
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    df[df["a"] > 1]["b"] = 9
df["b"].tolist()
""", note="Chained assignment `df[mask]['b'] = ...` writes into a temporary and never reaches `df` (pandas 3 warns with `ChainedAssignmentError`)."),
    dict(id="po-038", section="pandas", topic="int + NaN", code="""
pd.Series([1, 2, None]).dtype
""", note="NumPy int columns can't hold NaN, so a missing value upcasts to float64. The nullable `Int64` dtype keeps integers."),
    dict(id="po-039", section="pandas", topic="string dtype", code="""
pd.Series(["a", "b"]).dtype
""", note="pandas 3 infers its new string dtype (`str`, NaN as missing value) for text; pandas 2 used `object`."),
    dict(id="po-040", section="pandas", topic="str.contains and NaN", code="""
print(pd.Series(["pro", None]).str.contains("pro").tolist())
print(pd.Series(["pro", None], dtype=object).str.contains("pro").tolist())
""", note="With pandas 3's `str` dtype, string predicates return False for missing values; on object columns they return a missing value (None here), which breaks boolean indexing. `na=False` makes both explicit."),
    dict(id="po-041", section="pandas", topic="astype(int) truncation", code="""
pd.Series([1.7, -1.7]).astype(int).tolist()
""", note="`astype(int)` truncates toward zero; round first if that's what you mean."),
    dict(id="po-042", section="pandas", topic="mean of booleans", code="""
pd.Series([True, False, True, True]).mean()
""", note="True counts as 1, so the mean of a boolean column is the share of True (a rate)."),
    dict(id="po-043", section="pandas", topic="map vs replace", code="""
s = pd.Series(["a", "b", "z"])
print(s.map({"a": 1, "b": 2}).tolist())
print(s.replace({"a": "A"}).tolist())
""", note="`map(dict)` turns unmapped values into NaN; `replace(dict)` leaves them alone."),
    dict(id="po-044", section="pandas", topic="where vs mask", code="""
s = pd.Series([-1.0, np.nan, 2.0])
print(s.where(s > 0, 0).tolist())
print(s.mask(s < 0, 0).tolist())
""", note="`where` keeps values where the condition is True. NaN > 0 is False, so `where` replaces NaN too; `mask` replaces only where its condition is True."),
    dict(id="po-045", section="pandas", topic="pivot_table default", code="""
df = pd.DataFrame({"r": ["N", "N", "S"], "v": [10, 20, 5]})
df.pivot_table(index="r", values="v")
""", note="`pivot_table` aggregates with **mean** unless you pass `aggfunc`."),
    dict(id="po-046", section="pandas", topic="stack keeps NaN", code="""
df = pd.DataFrame({"a": [1.0, np.nan]})
len(df.stack())
""", note="Since pandas 3, `stack()` keeps missing values (the old `dropna=True` default is gone); call `.dropna()` yourself."),
    dict(id="po-047", section="pandas", topic="idxmax returns a label", code="""
s = pd.Series([3, 9, 9], index=["x", "y", "z"])
print(s.idxmax(), s.max())
""", note="`idxmax` returns the **label** of the first maximum; `max` the value."),
    # ---------------------------------------------------------------- numpy
    dict(id="po-048", section="numpy", topic="views vs copies", code="""
a = np.arange(5)
b = a[1:3]
b[0] = 99
a
""", note="Basic slices are **views**: writing through `b` changes `a`."),
    dict(id="po-049", section="numpy", topic="views vs copies", code="""
a = np.arange(5)
b = a[[1, 2]]
b[0] = 99
a
""", note="Fancy (integer-array) indexing returns a **copy**, so `a` is untouched."),
    dict(id="po-050", section="numpy", topic="broadcasting", code="""
(np.ones((3, 1)) + np.ones(4)).shape
""", note="Shapes align from the right: (3, 1) and (4,) broadcast to (3, 4)."),
    dict(id="po-051", section="numpy", topic="keepdims", code="""
X = np.ones((2, 3))
print(X.sum(axis=1).shape, X.sum(axis=1, keepdims=True).shape)
""", note="`keepdims=True` keeps a length-1 axis so the result broadcasts back against `X`."),
    dict(id="po-052", section="numpy", topic="arange with floats", code="""
len(np.arange(0.1, 0.4, 0.1))
""", note="Float steps accumulate rounding error, so the stop value can sneak in (here 4 values, not 3). Use `np.linspace` for float grids."),
    dict(id="po-053", section="numpy", topic="integer overflow", code="""
np.array([200], dtype=np.uint8) + np.uint8(100)
""", note="Fixed-width integers wrap around silently: 300 mod 256 = 44."),
    dict(id="po-054", section="numpy", topic="round half to even", code="""
np.round([0.5, 1.5, 2.5])
""", note="NumPy (and Python's `round`) use banker's rounding: halves go to the nearest **even** number."),
    dict(id="po-055", section="numpy", topic="reshape order", code="""
np.arange(6).reshape(2, 3).T.ravel()
""", note="`reshape` fills row by row; `.T.ravel()` reads the transposed array row by row, i.e. the original column by column."),
    dict(id="po-056", section="numpy", topic="argsort", code="""
np.argsort([30, 10, 20])
""", note="`argsort` returns the **indices** that would sort the array, not the ranks."),
    dict(id="po-057", section="numpy", topic="nan propagation", code="""
x = np.array([1.0, np.nan, 3.0])
print(x.mean(), np.nanmean(x))
""", note="Any NaN poisons the plain reduction; the `nan*` functions skip missing values."),
    # ---------------------------------------------------------------- sklearn / stats
    dict(id="po-058", section="sklearn", topic="std ddof", code="""
x = np.array([1.0, 2.0, 3.0, 4.0])
print(np.std(x), pd.Series(x).std())
""", note="NumPy defaults to the population std (`ddof=0`), pandas to the sample std (`ddof=1`). `StandardScaler` uses ddof=0."),
    dict(id="po-059", section="sklearn", topic="classes_ order", code="""
from sklearn.linear_model import LogisticRegression
m = LogisticRegression().fit([[0], [1], [2], [3]], ["yes", "no", "yes", "no"])
m.classes_
""", note="Columns of `predict_proba` follow `classes_`, the **sorted** labels, so here column 1 is 'yes'."),
    dict(id="po-060", section="sklearn", topic="train_test_split sizes", code="""
from sklearn.model_selection import train_test_split
a, b = train_test_split(np.arange(10), test_size=0.25, random_state=0)
print(len(a), len(b))
""", note="The test size is rounded **up**: ceil(0.25 x 10) = 3."),
    dict(id="po-061", section="sklearn", topic="predict vs predict_proba", code="""
from sklearn.linear_model import LogisticRegression
X, y = np.array([[0], [1], [2], [3]]), np.array([0, 0, 1, 1])
m = LogisticRegression().fit(X, y)
print(m.predict([[2.2]]), m.predict_proba([[2.2]]).round(3))
""", note="`predict` thresholds the class-1 probability at 0.5; ranking metrics like ROC AUC need `predict_proba`."),
    dict(id="po-062", section="stats", topic="Pearson vs Spearman", code="""
x = np.arange(1, 8)
y = np.exp(x)
print(round(np.corrcoef(x, y)[0, 1], 3), pd.Series(x).corr(pd.Series(y), method="spearman"))
""", note="A perfectly monotonic but curved relationship has Spearman 1.0 and a lower Pearson."),
]
