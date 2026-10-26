SECTION = "pandas"

PROBLEMS = [
# ------------------------------------------------------------------ io
dict(
    id="pd-001",
    title="Load selected columns from a semicolon CSV",
    difficulty="Easy",
    tags=["io & parsing"],
    signature="def solve(text: str) -> pd.DataFrame:",
    statement="""
`text` is the content of a CSV export that uses `;` as the field separator. The file has many columns; load only `order_id`, `region` and `revenue` (in that order) into a DataFrame with the default index.
""",
    setup="""
def make(seed, n):
    return {"text": D.orders(seed=seed, n=n).to_csv(sep=";", index=False)}

EXAMPLE = lambda: make(0, 5)
""",
    tests="""
TESTS = [
    lambda: make(1, 40),
    lambda: make(2, 800),
    Test(lambda: make(3, 1), "single row"),
]
""",
    hint1="`pd.read_csv` reads from any file-like object: wrap the string in `io.StringIO`, and pass `sep=';'` and `usecols=[...]`.",
    hint2="import io\npd.read_csv(io.StringIO(text), sep=';', usecols=['order_id', 'region', 'revenue'])",
    solution="""
import io

def solve(text):
    return pd.read_csv(io.StringIO(text), sep=";", usecols=["order_id", "region", "revenue"])
""",
    explanation="""
`usecols` avoids parsing columns you don't need (faster, less memory on big files). Note that `usecols` keeps the **file's** column order, not the order of your list; select `df[[...]]` afterwards if the order matters. `io.StringIO` turns a string into a file-like object.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html"],
    wrong_solutions=[
        dict(code="import io\n\ndef solve(text):\n    return pd.read_csv(io.StringIO(text), usecols=['order_id', 'region', 'revenue'])", why="default comma separator"),
        dict(code="import io\n\ndef solve(text):\n    return pd.read_csv(io.StringIO(text), sep=';')", why="all columns"),
    ],
),
dict(
    id="pd-002",
    title="Parse a messy export: missing markers, ZIP codes, dates",
    difficulty="Medium",
    tags=["io & parsing", "type conversion"],
    signature="def solve(text: str) -> pd.DataFrame:",
    statement="""
`text` is a CSV export with columns `order_id, zip, order_date, amount`. Load it so that:

* `zip` stays **text** (codes like `02139` keep their leading zero);
* the placeholders `n/a` and `-` become missing values (so `amount` is numeric);
* `order_date` (format `YYYY-MM-DD`) is parsed as a datetime.

Keep all columns and the default index. Dtypes are checked.
""",
    setup="""
def make(seed, n):
    rng = np.random.default_rng(seed)
    zips = np.array([f"{z:05d}" for z in rng.integers(1000, 99999, n)], dtype=object)
    zips[rng.random(n) < 0.1] = "n/a"
    amount = np.array([f"{a:.2f}" for a in rng.gamma(2, 40, n)], dtype=object)
    amount[rng.random(n) < 0.15] = rng.choice(["n/a", "-"], 1)[0]
    dates = (pd.Timestamp("2024-01-01") + pd.to_timedelta(rng.integers(0, 365, n), unit="D")).strftime("%Y-%m-%d")
    df = pd.DataFrame({"order_id": np.arange(1, n + 1), "zip": zips, "order_date": dates, "amount": amount})
    df.loc[0, "zip"] = "02139"
    return {"text": df.to_csv(index=False)}

EXAMPLE = lambda: make(0, 6)
""",
    tests="""
TESTS = [
    lambda: make(1, 30),
    lambda: make(2, 500),
    Test(lambda: make(3, 1), "single row"),
]
""",
    compare=dict(check_dtype=True),
    hint1="`pd.read_csv(..., dtype={'zip': str}, na_values=[...], parse_dates=['order_date'])`.",
    hint2="pd.read_csv(io.StringIO(text), dtype={'zip': str}, na_values=['n/a', '-'], parse_dates=['order_date'])",
    solution="""
import io

def solve(text):
    return pd.read_csv(io.StringIO(text), dtype={"zip": str}, na_values=["n/a", "-"],
                       parse_dates=["order_date"])
""",
    explanation="""
Declare identifier-like columns (ZIP codes, phone numbers, account ids) as `str` at read time: once parsed as numbers the leading zeros are gone. `na_values` *adds* to pandas' default markers (`''`, `'NA'`, `'NaN'`, `'null'`, `'n/a'`...). Here `'-'` is the one that matters. In pandas 3 text columns get the new `str` dtype (object in pandas 2).
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html",
          "https://pandas.pydata.org/docs/user_guide/io.html#na-and-missing-data-handling"],
    wrong_solutions=[
        dict(code="import io\n\ndef solve(text):\n    return pd.read_csv(io.StringIO(text), na_values=['n/a', '-'], parse_dates=['order_date'])", why="zip parsed as numbers"),
        dict(code="import io\n\ndef solve(text):\n    return pd.read_csv(io.StringIO(text), dtype={'zip': str}, parse_dates=['order_date'])", why="'-' not treated as missing"),
        dict(code="import io\n\ndef solve(text):\n    return pd.read_csv(io.StringIO(text), dtype={'zip': str}, na_values=['n/a', '-'])", why="dates left as text"),
    ],
),
dict(
    id="pd-003",
    title="European CSV: decimal commas",
    difficulty="Medium",
    tags=["io & parsing"],
    signature="def solve(text: str) -> pd.DataFrame:",
    statement="""
An export from a French accounting system uses `;` between fields, `,` as the **decimal** mark and `.` as the **thousands** separator (`1.234,50` means 1234.5). Load `text` so that the numeric columns `price` and `amount` are floats. Dtypes are checked.
""",
    setup="""
def fr(x):
    return f"{x:,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".")

def make(seed, n):
    rng = np.random.default_rng(seed)
    price = np.round(rng.lognormal(4, 1.2, n), 2)
    qty = rng.integers(1, 20, n)
    lines = ["sku;price;qty;amount"] + [f"SKU{i:03d};{fr(p)};{q};{fr(p * q)}" for i, (p, q) in enumerate(zip(price, qty))]
    return {"text": "\\n".join(lines) + "\\n"}

EXAMPLE = lambda: {"text": "sku;price;qty;amount\\nA1;1.234,50;2;2.469,00\\nB2;9,99;10;99,90\\n"}
""",
    tests="""
TESTS = [
    lambda: make(1, 20),
    lambda: make(2, 400),
    Test(lambda: {"text": "sku;price;qty;amount\\nZ9;0,50;1;0,50\\n"}, "single row, no thousands"),
]
""",
    compare=dict(check_dtype=True),
    hint1="`pd.read_csv(..., sep=';', decimal=',', thousands='.')`.",
    hint2="pd.read_csv(io.StringIO(text), sep=';', decimal=',', thousands='.')",
    solution="""
import io

def solve(text):
    return pd.read_csv(io.StringIO(text), sep=";", decimal=",", thousands=".")
""",
    explanation="""
`decimal` and `thousands` make the parser understand locale-formatted numbers. Without `thousands='.'` any value of 1,000 or more stays text, so the whole column silently becomes `str`/object. Always check `df.dtypes` right after loading.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html"],
    wrong_solutions=[
        dict(code="import io\n\ndef solve(text):\n    return pd.read_csv(io.StringIO(text), sep=';', decimal=',')", why="thousands separator ignored"),
        dict(code="import io\n\ndef solve(text):\n    return pd.read_csv(io.StringIO(text), sep=';')", why="decimal comma ignored"),
    ],
),
# ------------------------------------------------------------------ EDA
dict(
    id="pd-004",
    title="Share of missing values per column",
    difficulty="Easy",
    tags=["EDA", "missing data"],
    signature="def solve(df: pd.DataFrame) -> pd.Series:",
    statement="""
Return the share (between 0 and 1) of missing values in each column of `df`, as a Series indexed by column name, sorted from the most to the least missing. Columns with equal shares may appear in any order.
""",
    setup="""
def make(seed, n, extra_nan=0.0):
    df = D.hr(seed=seed, n=n)
    if extra_nan:
        rng = np.random.default_rng(seed)
        df.loc[rng.random(n) < extra_nan, "city"] = np.nan
    return {"df": df}

EXAMPLE = lambda: make(0, 10, extra_nan=0.2)
""",
    tests="""
TESTS = [
    lambda: make(1, 50),
    lambda: make(2, 500, extra_nan=0.1),
    Test(lambda: {"df": D.orders(seed=3, n=20)}, "no missing values"),
]

def check(got, exp, inputs):
    if not isinstance(got, pd.Series):
        fail(f"expected a Series, got {type(got).__name__}")
    msg = compare(got.sort_index(), exp.sort_index())
    if msg:
        return msg
    if not got.is_monotonic_decreasing:
        fail("values are not sorted from most to least missing")
""",
    hint1="`df.isna()` is a boolean frame; its `.mean()` per column is the share of True. Then `sort_values(ascending=False)`.",
    hint2="df.isna().mean().sort_values(ascending=False)",
    solution="""
def solve(df):
    return df.isna().mean().sort_values(ascending=False)
""",
    explanation="""
The mean of a boolean column is the fraction of True values, so `isna().mean()` is the missing share and `isna().sum()` the missing count. This is usually the second line of any EDA, right after `df.info()` (which prints non-null counts and dtypes).
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.isna.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.info.html"],
    wrong_solutions=[
        dict(code="def solve(df):\n    return df.isna().sum().sort_values(ascending=False)", why="counts, not shares"),
        dict(code="def solve(df):\n    return df.isna().mean().sort_values()", why="ascending"),
    ],
),
dict(
    id="pd-005",
    title="Column profile table",
    difficulty="Medium",
    tags=["EDA"],
    signature="def solve(df: pd.DataFrame) -> pd.DataFrame:",
    statement="""
Build a quick profile of `df`: one row per column of `df` (index = the column names, in their original order) with columns:

* `dtype`: the dtype as a string (e.g. `'float64'`);
* `n_unique`: number of distinct **non-missing** values;
* `n_missing`: number of missing values.
""",
    setup="""
EXAMPLE = lambda: {"df": D.hr(seed=0, n=8)}
""",
    tests="""
TESTS = [
    lambda: {"df": D.churn(seed=1, n=60, messy=True)},
    lambda: {"df": D.orders_raw(seed=2, n=300)},
    Test(lambda: {"df": D.hr(seed=3, n=1)}, "single row"),
]
""",
    hint1="Each piece is a Series indexed by column: `df.dtypes.astype(str)`, `df.nunique()`, `df.isna().sum()`; combine them with `pd.DataFrame({...})`.",
    hint2="pd.DataFrame({'dtype': df.dtypes.astype(str), 'n_unique': df.nunique(), 'n_missing': df.isna().sum()})",
    solution="""
def solve(df):
    return pd.DataFrame({"dtype": df.dtypes.astype(str), "n_unique": df.nunique(),
                         "n_missing": df.isna().sum()})
""",
    explanation="""
Building a DataFrame from a dict of Series aligns them on their index (the column names). `nunique()` ignores NaN by default (`dropna=False` counts it as a value). `count()` is the opposite of `isna().sum()`: it counts non-missing values.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.nunique.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.dtypes.html"],
    wrong_solutions=[
        dict(code="def solve(df):\n    return pd.DataFrame({'dtype': df.dtypes.astype(str), 'n_unique': df.nunique(dropna=False), 'n_missing': df.isna().sum()})", why="counts NaN as a value"),
        dict(code="def solve(df):\n    return pd.DataFrame({'dtype': df.dtypes.astype(str), 'n_unique': df.nunique(), 'n_missing': df.count()})", why="count() is non-missing"),
    ],
),
dict(
    id="pd-006",
    title="Most correlated pair of features",
    difficulty="Medium",
    tags=["EDA"],
    signature="def solve(df: pd.DataFrame) -> tuple:",
    statement="""
Among the **numeric** columns of `df` (ignore the others), find the pair of distinct columns with the largest **absolute** Pearson correlation.

Return `(col_a, col_b, corr)` where `col_a` comes before `col_b` in `df`'s column order and `corr` is the signed correlation (a float).
""",
    setup="""
def neg(seed, n):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=n)
    return {"df": pd.DataFrame({"name": [f"r{i}" for i in range(n)], "a": rng.normal(size=n),
                                "b": x, "c": -2 * x + rng.normal(0, 0.3, n), "d": x + rng.normal(0, 1.5, n)})}

EXAMPLE = lambda: {"df": D.hr(seed=0, n=40)}
""",
    tests="""
TESTS = [
    lambda: {"df": D.hr(seed=1, n=300)},
    Test(lambda: neg(2, 200), "strongest correlation is negative"),
    lambda: {"df": D.churn(seed=3, n=500)},
]
""",
    hint1="`df.select_dtypes('number').corr()`, keep the upper triangle (`np.triu(..., k=1)` as a mask with `.where`), `.stack()` it, then `.abs().idxmax()`.",
    hint2="c = df.select_dtypes('number').corr()\npairs = c.where(np.triu(np.ones(c.shape, dtype=bool), k=1)).stack()\na, b = pairs.abs().idxmax()",
    solution="""
def solve(df):
    c = df.select_dtypes("number").corr()
    pairs = c.where(np.triu(np.ones(c.shape, dtype=bool), k=1)).stack()
    a, b = pairs.abs().idxmax()
    return a, b, float(pairs[(a, b)])
""",
    explanation="""
The diagonal is always 1, so mask it out, and keep one triangle to avoid seeing each pair twice. `stack()` turns the matrix into a Series indexed by `(row, col)` pairs and drops the masked NaNs. In pandas 2+ `corr()` raises on non-numeric columns (`numeric_only=False` is the default), hence `select_dtypes`.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.corr.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.stack.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.select_dtypes.html"],
    wrong_solutions=[
        dict(code="""
def solve(df):
    c = df.select_dtypes("number").corr()
    pairs = c.where(np.triu(np.ones(c.shape, dtype=bool), k=1)).stack()
    a, b = pairs.idxmax()
    return a, b, float(pairs[(a, b)])
""", why="ignores negative correlations"),
        dict(code="""
def solve(df):
    pairs = df.select_dtypes("number").corr().stack()
    a, b = pairs.abs().idxmax()
    return a, b, float(pairs[(a, b)])
""", why="diagonal included"),
    ],
),
# ------------------------------------------------------------------ construction / types
dict(
    id="pd-007",
    title="DataFrame from API records",
    difficulty="Easy",
    tags=["construction"],
    signature="def solve(records: list) -> pd.DataFrame:",
    statement="""
`records` is a list of dicts parsed from a JSON API, e.g. `{"id": 1, "name": "Ana", "score": 91.5}`. Some records lack some keys.

Return a DataFrame with exactly the columns `id, name, score, team` in that order (missing values as NaN, including a column no record has), default index.
""",
    setup="""
def make(seed, n, with_team=True):
    rng = np.random.default_rng(seed)
    recs = []
    for i in range(n):
        r = {"id": i + 1, "name": f"user{i}", "score": round(float(rng.uniform(40, 100)), 1)}
        if with_team and rng.random() < 0.6:
            r["team"] = str(rng.choice(["red", "blue"]))
        if rng.random() < 0.2:
            del r["score"]
        if rng.random() < 0.2:
            r["extra"] = 1
        recs.append(dict(reversed(list(r.items()))) if rng.random() < 0.3 else r)
    return {"records": recs}

EXAMPLE = lambda: {"records": [{"id": 1, "name": "Ana", "score": 91.5}, {"name": "Ben", "id": 2, "team": "red"},
                               {"id": 3, "name": "Cy", "score": 78.0, "extra": True}]}
""",
    tests="""
TESTS = [
    lambda: make(1, 10),
    lambda: make(2, 200),
    Test(lambda: make(3, 5, with_team=False), "no record has a team"),
]
""",
    hint1="`pd.DataFrame(records, columns=[...])` selects and orders the keys, creating all-NaN columns for keys that never appear.",
    hint2="pd.DataFrame(records, columns=['id', 'name', 'score', 'team'])",
    solution="""
def solve(records):
    return pd.DataFrame(records, columns=["id", "name", "score", "team"])
""",
    explanation="""
With a list of dicts, `columns=` acts as a selector: extra keys are dropped, missing ones become NaN, and the order is yours. Without it, columns appear in first-seen order and a key that never occurs is simply absent, so downstream code breaks on some batches. For nested JSON, use `pd.json_normalize`.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.json_normalize.html"],
    wrong_solutions=[
        dict(code="def solve(records):\n    return pd.DataFrame(records)", why="column set and order depend on the data"),
        dict(code="def solve(records):\n    return pd.DataFrame(records)[['id', 'name', 'score']]", why="team missing"),
    ],
),
dict(
    id="pd-008",
    title="Fix column types",
    difficulty="Easy",
    tags=["type conversion"],
    signature="def solve(df: pd.DataFrame) -> pd.DataFrame:",
    statement="""
`df` (orders) arrived with wrong types: `quantity` holds whole numbers stored as strings, `unit_price` holds decimal strings, and `region` is a low-cardinality label.

Return a copy with `quantity` as **int64**, `unit_price` as **float64** and `region` as **category**; other columns unchanged. Dtypes are checked.
""",
    setup="""
def make(seed, n):
    df = D.orders(seed=seed, n=n)
    return {"df": df.astype({"quantity": str, "unit_price": str})}

EXAMPLE = lambda: make(0, 5)
""",
    tests="""
TESTS = [
    lambda: make(1, 50),
    lambda: make(2, 1000),
    Test(lambda: make(3, 1), "single row"),
]
""",
    compare=dict(check_dtype=True),
    hint1="`df.astype({...})` takes a dict mapping column name to dtype.",
    hint2="df.astype({'quantity': 'int64', 'unit_price': 'float64', 'region': 'category'})",
    solution="""
def solve(df):
    return df.astype({"quantity": "int64", "unit_price": "float64", "region": "category"})
""",
    explanation="""
`astype` with a dict converts several columns at once and returns a new frame. `category` stores each distinct label once plus small integer codes: less memory and faster groupbys on repeated strings. Use `pd.to_numeric(errors='coerce')` instead when some values may not parse.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.astype.html",
          "https://pandas.pydata.org/docs/user_guide/categorical.html"],
    wrong_solutions=[
        dict(code="def solve(df):\n    return df.astype({'quantity': 'int64', 'unit_price': 'float64'})", why="region not categorical"),
        dict(code="def solve(df):\n    return df.astype({'quantity': 'float64', 'unit_price': 'float64', 'region': 'category'})", why="quantity as float"),
    ],
),
dict(
    id="pd-009",
    title="Prices stored as text",
    difficulty="Medium",
    tags=["type conversion", "strings"],
    signature="def solve(s: pd.Series) -> pd.Series:",
    statement="""
`s` holds prices exported as text, like `'$1,234.50'`, plus junk such as `'n/a'`, `'call us'` or empty strings.

Return a float Series with the same index and name: remove the `$` sign and the thousands commas, convert to numbers, and turn anything that still can't be parsed into NaN.
""",
    setup="""
def make(seed, n, junk=0.1):
    rng = np.random.default_rng(seed)
    s = np.array(["${:,.2f}".format(v) for v in np.round(rng.lognormal(5.5, 1.5, n), 2)], dtype=object)
    s[0] = "$12,345.60"
    bad = rng.random(len(s)) < junk
    s[bad] = rng.choice(["n/a", "call us", "", "TBD"], bad.sum())
    return {"s": pd.Series(s, name="unit_price", dtype="str")}

EXAMPLE = lambda: {"s": pd.Series(["$12.50", "$1,234.00", "n/a", "$0.99", "call us"], name="price")}
""",
    tests="""
TESTS = [
    lambda: make(1, 40),
    lambda: make(2, 600, junk=0.3),
    Test(lambda: make(3, 5, junk=0.0), "no junk"),
]
""",
    compare=dict(check_dtype=True, check_names=True),
    hint1="Strip the symbols with `s.str.replace(r'[$,]', '', regex=True)`, then `pd.to_numeric(..., errors='coerce')`.",
    hint2="pd.to_numeric(s.str.replace(r'[$,]', '', regex=True), errors='coerce')",
    solution="""
def solve(s):
    return pd.to_numeric(s.str.replace(r"[$,]", "", regex=True), errors="coerce")
""",
    explanation="""
`errors='coerce'` turns unparseable values into NaN instead of raising, which makes it the standard tool for dirty numeric text. Count the NaNs afterwards: a jump means you missed a format. `astype(float)` raises on the first bad value. `errors='ignore'` was deprecated in pandas 2.2 and removed in 3.0.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.to_numeric.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.Series.str.replace.html"],
    wrong_solutions=[
        dict(code="def solve(s):\n    return pd.to_numeric(s.str.replace('$', ''), errors='coerce')", why="thousands commas kept: big prices become NaN"),
        dict(code="def solve(s):\n    return pd.to_numeric(s.str.strip('$'), errors='coerce')", why="commas kept"),
    ],
),
# ------------------------------------------------------------------ selection
dict(
    id="pd-010",
    title="Big orders from the North",
    difficulty="Easy",
    tags=["selection"],
    signature="def solve(orders: pd.DataFrame) -> pd.DataFrame:",
    statement="""
Return the `order_id`, `customer_id` and `revenue` columns of the orders from the **North** region with revenue **above 500**, keeping the original index labels and row order.
""",
    setup="""
EXAMPLE = lambda: {"orders": D.orders(seed=0, n=25, n_customers=8)}
""",
    tests="""
TESTS = [
    lambda: {"orders": D.orders(seed=1, n=100)},
    lambda: {"orders": D.orders(seed=2, n=2000, n_customers=300)},
    Test(lambda: {"orders": D.orders(seed=3, n=3)}, "maybe no match"),
]
""",
    hint1="Combine conditions with `&` (each in parentheses) inside `.loc[row_mask, column_list]`.",
    hint2="orders.loc[(orders['region'] == 'North') & (orders['revenue'] > 500), ['order_id', 'customer_id', 'revenue']]",
    solution="""
def solve(orders):
    mask = (orders["region"] == "North") & (orders["revenue"] > 500)
    return orders.loc[mask, ["order_id", "customer_id", "revenue"]]
""",
    explanation="""
Use `&`, `|`, `~` for element-wise logic, and parenthesize each comparison: `&` binds tighter than `==`. Python's `and` raises "truth value of a Series is ambiguous". One `.loc[rows, cols]` call is clearer than chained `df[mask][cols]` and is the form that also works for assignment.
""",
    docs=["https://pandas.pydata.org/docs/user_guide/indexing.html#boolean-indexing",
          "https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.loc.html"],
    wrong_solutions=[
        dict(code="def solve(orders):\n    mask = (orders['region'] == 'North') | (orders['revenue'] > 500)\n    return orders.loc[mask, ['order_id', 'customer_id', 'revenue']]", why="or instead of and"),
        dict(code="def solve(orders):\n    mask = (orders['region'] == 'North') & (orders['revenue'] > 500)\n    return orders.loc[mask, ['order_id', 'customer_id', 'revenue']].reset_index(drop=True)", why="index reset"),
    ],
),
dict(
    id="pd-011",
    title="Orders in chosen categories with 2 to 4 items",
    difficulty="Easy",
    tags=["selection"],
    signature="def solve(orders: pd.DataFrame, categories: list) -> pd.DataFrame:",
    statement="""
Return the orders whose `category` is one of `categories` **and** whose `quantity` is between 2 and 4, **inclusive** on both ends. Keep all columns, the original index and row order.
""",
    setup="""
EXAMPLE = lambda: {"orders": D.orders(seed=0, n=20), "categories": ["Books", "Home"]}
""",
    tests="""
TESTS = [
    lambda: {"orders": D.orders(seed=1, n=200), "categories": ["Electronics"]},
    lambda: {"orders": D.orders(seed=2, n=1000), "categories": ["Clothing", "Sports", "Books"]},
    Test(lambda: {"orders": D.orders(seed=3, n=50), "categories": []}, "empty category list"),
]
""",
    hint1="`Series.isin(list)` for membership and `Series.between(lo, hi)` (inclusive by default).",
    hint2="orders[orders['category'].isin(categories) & orders['quantity'].between(2, 4)]",
    solution="""
def solve(orders, categories):
    return orders[orders["category"].isin(categories) & orders["quantity"].between(2, 4)]
""",
    explanation="""
`isin` is the vectorized `in`; `between(lo, hi, inclusive='both')` is shorthand for `(s >= lo) & (s <= hi)`. Pass `inclusive='left'`, `'right'` or `'neither'` to change the ends. Write `~s.isin(...)` for "not in".
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.Series.isin.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.Series.between.html"],
    wrong_solutions=[
        dict(code="def solve(orders, categories):\n    return orders[orders['category'].isin(categories) & orders['quantity'].between(2, 4, inclusive='neither')]", why="exclusive bounds"),
        dict(code="def solve(orders, categories):\n    return orders[orders['category'].isin(categories) & (orders['quantity'] > 2) & (orders['quantity'] < 4)]", why="strict inequalities"),
    ],
),
dict(
    id="pd-012",
    title="Filter with variables in a query string",
    difficulty="Easy",
    tags=["selection"],
    signature="def solve(hr: pd.DataFrame, dept: str, min_salary: float) -> pd.DataFrame:",
    statement="""
Return the employees of department `dept` whose `salary` is **at least** `min_salary`, keeping all columns, the original index and order. Write the filter as a readable query string that refers to the two function arguments.
""",
    setup="""
def make(seed, n, dept, q):
    hr = D.hr(seed=seed, n=n)
    known = hr.loc[hr["department"] == dept, "salary"].dropna()
    return {"hr": hr, "dept": dept, "min_salary": float(known.quantile(q, interpolation="nearest"))}

EXAMPLE = lambda: make(0, 30, "Engineering", 0.5)
""",
    tests="""
TESTS = [
    lambda: make(1, 200, "Sales", 0.3),
    lambda: make(2, 800, "Finance", 0.8),
    Test(lambda: make(3, 60, "HR", 1.0), "threshold equals the top salary"),
]
""",
    hint1="`DataFrame.query` accepts boolean expressions; prefix Python variables with `@`.",
    hint2="hr.query('department == @dept and salary >= @min_salary')",
    solution="""
def solve(hr, dept, min_salary):
    return hr.query("department == @dept and salary >= @min_salary")
""",
    explanation="""
`query` reads like SQL and avoids repeating `hr[...]`; `@name` pulls in a local variable, and backticks quote column names with spaces. It's handy in method chains. For programmatic filters, boolean masks are more explicit and easier to debug.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.query.html"],
    wrong_solutions=[
        dict(code="def solve(hr, dept, min_salary):\n    return hr.query('department == @dept and salary > @min_salary')", why="strictly greater"),
        dict(code="def solve(hr, dept, min_salary):\n    return hr.query('salary >= @min_salary')", why="department ignored"),
    ],
),
dict(
    id="pd-013",
    title="First rows by position, not by label",
    difficulty="Easy",
    tags=["selection"],
    signature="def solve(df: pd.DataFrame) -> pd.DataFrame:",
    statement="""
`df` has been filtered and sorted, so its index labels are no longer `0..n-1` (label `0` may sit anywhere). Return the **first three rows by position** and the **last two columns by position**.
""",
    setup="""
def make(seed, n):
    o = D.orders(seed=seed, n=n)
    return {"df": o.sort_values("revenue", ascending=False)}

EXAMPLE = lambda: make(0, 8)
""",
    tests="""
TESTS = [
    lambda: make(1, 50),
    lambda: make(2, 500),
    Test(lambda: make(3, 2), "fewer than three rows"),
]
""",
    hint1="`.iloc` is purely positional: `df.iloc[row_slice, col_slice]` with negative positions counting from the end.",
    hint2="df.iloc[:3, -2:]",
    solution="""
def solve(df):
    return df.iloc[:3, -2:]
""",
    explanation="""
`.loc` selects by **label** and its slices include the end label; `.iloc` selects by **position** and excludes the end, like Python lists. After sorting or filtering, `df.loc[0:2]` means "from the row labelled 0 to the row labelled 2", wherever those rows are.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.iloc.html",
          "https://pandas.pydata.org/docs/user_guide/indexing.html#different-choices-for-indexing"],
    wrong_solutions=[
        dict(code="def solve(df):\n    return df.loc[0:2, df.columns[-2:]]", why="label slice"),
        dict(code="def solve(df):\n    return df.sort_index().iloc[:3, -2:]", why="re-sorted by label"),
    ],
),
dict(
    id="pd-014",
    title="Sort by region, then by revenue descending",
    difficulty="Easy",
    tags=["sorting & ranking"],
    signature="def solve(orders: pd.DataFrame) -> pd.DataFrame:",
    statement="""
Sort `orders` by `region` A to Z, then by `revenue` from highest to lowest within each region. Rows that tie on both keep their original relative order. Keep the original index labels.
""",
    setup="""
EXAMPLE = lambda: {"orders": D.orders(seed=0, n=10, n_customers=5)}
""",
    tests="""
TESTS = [
    lambda: {"orders": D.orders(seed=1, n=100)},
    lambda: {"orders": D.orders(seed=2, n=1500)},
    Test(lambda: {"orders": pd.concat([D.orders(seed=3, n=6)] * 2)}, "duplicate rows"),
]
""",
    hint1="`sort_values` takes lists: `by=[...]` and `ascending=[...]` of the same length.",
    hint2="orders.sort_values(['region', 'revenue'], ascending=[True, False])",
    solution="""
def solve(orders):
    return orders.sort_values(["region", "revenue"], ascending=[True, False], kind="stable")
""",
    explanation="""
One `ascending` flag per key. Multi-key sorts are stable in pandas, but single-key `sort_values` defaults to quicksort, which is not: pass `kind='stable'` whenever tie order matters. Add `ignore_index=True` only if you want a fresh 0..n-1 index.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.sort_values.html"],
    wrong_solutions=[
        dict(code="def solve(orders):\n    return orders.sort_values(['region', 'revenue'], ascending=False)", why="regions Z to A"),
        dict(code="def solve(orders):\n    return orders.sort_values(['region', 'revenue'], ascending=[True, False], ignore_index=True)", why="index reset"),
    ],
),
dict(
    id="pd-015",
    title="Top-n orders, keeping ties",
    difficulty="Easy",
    tags=["sorting & ranking"],
    signature="def solve(orders: pd.DataFrame, n: int) -> pd.DataFrame:",
    statement="""
Return the `n` orders with the highest `revenue`, largest first. If several orders tie with the `n`-th one, keep **all** of them (so the result may have more than `n` rows). Keep the original index.
""",
    setup="""
def make(seed, size, n, ties=False):
    o = D.orders(seed=seed, n=size)
    if ties:
        top = o["revenue"].nlargest(n).iloc[-1]
        o.loc[o.sample(3, random_state=seed).index, "revenue"] = top
    return {"orders": o, "n": n}

EXAMPLE = lambda: make(0, 15, 3, ties=True)
""",
    tests="""
TESTS = [
    lambda: make(1, 100, 5),
    Test(lambda: make(2, 400, 10, ties=True), "ties at the cut-off"),
    Test(lambda: make(3, 4, 4), "n equals the number of rows"),
]
""",
    hint1="`DataFrame.nlargest(n, column, keep='all')`.",
    hint2="orders.nlargest(n, 'revenue', keep='all')",
    solution="""
def solve(orders, n):
    return orders.nlargest(n, "revenue", keep="all")
""",
    explanation="""
`nlargest` is faster than a full `sort_values().head(n)` and is explicit about ties: `keep='first'` (the default) cuts arbitrarily at `n`, while `keep='all'` keeps every tie. Use `nsmallest` for the other end.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.nlargest.html"],
    wrong_solutions=[
        dict(code="def solve(orders, n):\n    return orders.nlargest(n, 'revenue')", why="ties dropped"),
        dict(code="def solve(orders, n):\n    return orders.sort_values('revenue').tail(n)", why="ascending order, ties dropped"),
    ],
),
dict(
    id="pd-016",
    title="Salary percentile within the department",
    difficulty="Medium",
    tags=["sorting & ranking", "group-wise ops"],
    signature="def solve(hr: pd.DataFrame) -> pd.Series:",
    statement="""
For each employee, return the percentile rank of their `salary` **within their department**, between 0 and 1 (highest salary = 1.0; tied salaries share the average rank). Missing salaries stay NaN. Return a Series aligned to `hr`'s index.
""",
    setup="""
EXAMPLE = lambda: {"hr": D.hr(seed=0, n=12)}
""",
    tests="""
TESTS = [
    lambda: {"hr": D.hr(seed=1, n=80)},
    lambda: {"hr": D.hr(seed=2, n=1500)},
    Test(lambda: {"hr": D.hr(seed=3, n=3)}, "tiny departments"),
]
""",
    hint1="`groupby(...)[col].rank(pct=True)` ranks within each group and keeps the original index.",
    hint2="hr.groupby('department')['salary'].rank(pct=True)",
    solution="""
def solve(hr):
    return hr.groupby("department")["salary"].rank(pct=True)
""",
    explanation="""
`rank` behaves like `transform`: one value per row, aligned to the original index. `method='average'` (the default) shares tied ranks; `'min'` gives competition ranking and `'first'` breaks ties by order. `pct=True` divides by the number of non-null values in the group.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.api.typing.SeriesGroupBy.rank.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.Series.rank.html"],
    wrong_solutions=[
        dict(code="def solve(hr):\n    return hr['salary'].rank(pct=True)", why="company-wide rank"),
        dict(code="def solve(hr):\n    return hr.groupby('department')['salary'].rank(pct=True, method='first')", why="ties broken by order"),
    ],
),
# ------------------------------------------------------------------ column ops / strings / dates
dict(
    id="pd-017",
    title="Add derived columns in one chain",
    difficulty="Easy",
    tags=["method chaining", "column ops"],
    signature="def solve(orders: pd.DataFrame) -> pd.DataFrame:",
    statement="""
Return a copy of `orders` with three new columns appended, in this order:

* `month`: the month number (1-12) of `order_date`;
* `big`: True when `revenue` is above 300;
* `rev_per_item`: `revenue / quantity`.

Don't modify `orders` itself.
""",
    setup="""
EXAMPLE = lambda: {"orders": D.orders(seed=0, n=6)}
""",
    tests="""
TESTS = [
    lambda: {"orders": D.orders(seed=1, n=60)},
    lambda: {"orders": D.orders(seed=2, n=1000)},
    Test(lambda: {"orders": D.orders(seed=3, n=1)}, "single row"),
]
""",
    mutation_check=True,
    hint1="`DataFrame.assign(new=...)` returns a copy; pass lambdas (`lambda d: ...`) so each new column can use the frame as it is at that point of the chain.",
    hint2="orders.assign(month=lambda d: d['order_date'].dt.month,\n              big=lambda d: d['revenue'] > 300,\n              rev_per_item=lambda d: d['revenue'] / d['quantity'])",
    solution="""
def solve(orders):
    return orders.assign(
        month=lambda d: d["order_date"].dt.month,
        big=lambda d: d["revenue"] > 300,
        rev_per_item=lambda d: d["revenue"] / d["quantity"],
    )
""",
    explanation="""
`assign` never mutates and returns the new frame, so it composes in method chains (`df.query(...).assign(...).groupby(...)`). Lambdas receive the intermediate frame, so later columns can depend on earlier ones within the same `assign`. Plain `df['x'] = ...` modifies in place.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.assign.html"],
    wrong_solutions=[
        dict(code="def solve(orders):\n    orders['month'] = orders['order_date'].dt.month\n    orders['big'] = orders['revenue'] > 300\n    orders['rev_per_item'] = orders['revenue'] / orders['quantity']\n    return orders", why="mutates the input"),
        dict(code="def solve(orders):\n    return orders.assign(month=lambda d: d['order_date'].dt.month, big=lambda d: d['revenue'] > 300, rev_per_item=lambda d: d['revenue'] / d['quantity']).assign(month=lambda d: d['month'].astype(str).str.zfill(2))", why="month as text '01'"),
    ],
),
dict(
    id="pd-018",
    title="Recode region codes",
    difficulty="Easy",
    tags=["column ops"],
    signature="def solve(s: pd.Series) -> pd.Series:",
    statement="""
`s` holds region codes `N`, `S`, `E`, `W`, and occasionally an unknown code. Return a Series (same index and name) with the full names `North`, `South`, `East`, `West`; **unknown codes must become NaN** (not stay as they are).
""",
    setup="""
def make(seed, n, unknown=0.05):
    rng = np.random.default_rng(seed)
    codes = rng.choice(["N", "S", "E", "W"], n).astype(object)
    codes[rng.random(n) < unknown] = "X"
    return {"s": pd.Series(codes, name="region_code", dtype="str")}

EXAMPLE = lambda: {"s": pd.Series(["N", "E", "X", "W", "S"], name="region_code")}
""",
    tests="""
TESTS = [
    lambda: make(1, 30),
    lambda: make(2, 1000, unknown=0.2),
    Test(lambda: make(3, 5, unknown=0.0), "no unknown code"),
]
""",
    compare=dict(check_names=True),
    hint1="`Series.map(dict)`: values missing from the dict become NaN (`replace` would keep them).",
    hint2="s.map({'N': 'North', 'S': 'South', 'E': 'East', 'W': 'West'})",
    solution="""
def solve(s):
    return s.map({"N": "North", "S": "South", "E": "East", "W": "West"})
""",
    explanation="""
`map(dict)` is a lookup: anything not in the dict becomes NaN, which surfaces unexpected codes. `replace(dict)` only substitutes the listed values and leaves everything else as it was. Pick based on whether unknown values should survive.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.Series.map.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.Series.replace.html"],
    wrong_solutions=[
        dict(code="def solve(s):\n    return s.replace({'N': 'North', 'S': 'South', 'E': 'East', 'W': 'West'})", why="unknown codes kept"),
    ],
),
dict(
    id="pd-019",
    title="Normalize inconsistent spellings",
    difficulty="Easy",
    tags=["strings"],
    signature="def solve(raw: pd.DataFrame) -> pd.Series:",
    statement="""
In `raw` (a messy orders export), the `region` column has case and whitespace variants such as `' North'`, `'SOUTH'` or `'east '`. Return the cleaned `region` column: surrounding whitespace removed and Title-cased (`'North'`), same index and name.
""",
    setup="""
EXAMPLE = lambda: {"raw": D.orders_raw(seed=0, n=10)}
""",
    tests="""
TESTS = [
    lambda: {"raw": D.orders_raw(seed=1, n=100)},
    lambda: {"raw": D.orders_raw(seed=2, n=2000)},
    Test(lambda: {"raw": D.orders_raw(seed=3, n=3)}, "tiny"),
]
""",
    compare=dict(check_names=True),
    hint1="Chain vectorized string methods: `s.str.strip().str.title()`.",
    hint2="raw['region'].str.strip().str.title()",
    solution="""
def solve(raw):
    return raw["region"].str.strip().str.title()
""",
    explanation="""
The `.str` accessor applies Python string methods element-wise and skips missing values. Normalize **before** grouping or joining: otherwise `'North'` and `' north'` are counted as two regions. Check with `value_counts()` before and after.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.Series.str.strip.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.Series.str.title.html"],
    wrong_solutions=[
        dict(code="def solve(raw):\n    return raw['region'].str.title()", why="whitespace kept"),
        dict(code="def solve(raw):\n    return raw['region'].str.strip().str.lower()", why="lower-case"),
    ],
),
dict(
    id="pd-020",
    title="Zero out negative glitches, keep NaN",
    difficulty="Easy",
    tags=["conditional logic"],
    signature="def solve(df: pd.DataFrame) -> pd.DataFrame:",
    statement="""
`df` holds numeric sensor columns where negative readings are glitches. Replace every negative value with 0 and leave everything else unchanged: **missing values must stay NaN**.
""",
    setup="""
def make(seed, n, k=3):
    rng = np.random.default_rng(seed)
    X = np.round(rng.normal(5, 4, (n, k)), 2)
    X[rng.random((n, k)) < 0.1] = np.nan
    return {"df": pd.DataFrame(X, columns=[f"s{i + 1}" for i in range(k)])}

EXAMPLE = lambda: {"df": pd.DataFrame({"s1": [1.5, -0.2, np.nan], "s2": [-3.0, 4.0, 0.0]})}
""",
    tests="""
TESTS = [
    lambda: make(1, 20),
    lambda: make(2, 2000, 5),
    Test(lambda: make(3, 1, 2), "single row"),
]
""",
    hint1="`df.mask(cond, other)` replaces values where `cond` is True; `df.where(cond, other)` replaces where it is **False**.",
    hint2="df.mask(df < 0, 0)",
    solution="""
def solve(df):
    return df.mask(df < 0, 0)
""",
    explanation="""
Comparisons with NaN are False. `df.where(df >= 0, 0)` therefore replaces NaN too, because "NaN >= 0" is False, while `mask(df < 0, 0)` leaves it alone. `df.clip(lower=0)` is another NaN-safe option. Think about which side of the condition NaN falls on.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.mask.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.where.html"],
    wrong_solutions=[
        dict(code="def solve(df):\n    return df.where(df >= 0, 0)", why="NaN replaced by 0"),
        dict(code="def solve(df):\n    return df.abs()", why="flips the sign"),
    ],
),
dict(
    id="pd-021",
    title="Case-insensitive product search",
    difficulty="Easy",
    tags=["strings"],
    signature="def solve(products: pd.Series) -> pd.Series:",
    statement="""
`products` holds product names (some are missing). Return a boolean Series with the same index that is True where the name contains `'pro'` in any letter case (`'Pro'`, `'PRO'`, `'improve'`...) and **False** where the name is missing.
""",
    setup="""
NAMES = ["MacBook Pro", "iPad", "PROtein bar", "Improve kit", "Laptop stand", "pro cable", "Mouse", "Projector", "Keyboard"]

def make(seed, n):
    rng = np.random.default_rng(seed)
    v = rng.choice(NAMES, n).astype(object)
    v[rng.random(n) < 0.15] = None
    return {"products": pd.Series(v, name="product", dtype=object)}

EXAMPLE = lambda: {"products": pd.Series(["MacBook Pro", None, "Mouse", "improve kit"], name="product", dtype=object)}
""",
    tests="""
TESTS = [
    lambda: make(1, 30),
    lambda: make(2, 1000),
    Test(lambda: {"products": pd.Series([None, "PRO", None], name="product", dtype=object)}, "mostly missing"),
]
""",
    compare=dict(check_dtype=True),
    hint1="`s.str.contains(pattern, case=False, na=False)`.",
    hint2="products.str.contains('pro', case=False, na=False)",
    solution="""
def solve(products):
    return products.str.contains("pro", case=False, na=False)
""",
    explanation="""
`na=False` decides what missing values become. On object columns (pandas 2, or mixed data like here) they would come back as NaN and break boolean indexing. With pandas 3's default `str` dtype they already come back False, but be explicit. The pattern is a regex: pass `regex=False` for literal text with `.`, `(` or `+`.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.Series.str.contains.html"],
    wrong_solutions=[
        dict(code="def solve(products):\n    return products.str.contains('pro', na=False)", why="case-sensitive"),
        dict(code="def solve(products):\n    return products.str.lower().str.contains('pro')", why="missing values not False"),
    ],
),
dict(
    id="pd-022",
    title="Extract amount and unit from package sizes",
    difficulty="Medium",
    tags=["strings"],
    signature="def solve(s: pd.Series) -> pd.DataFrame:",
    statement="""
`s` holds package sizes such as `'500ml'`, `'1.5 L'`, `'250 g'` or `'2KG'`. Return a DataFrame with the same index and two columns:

* `amount`: the number, as a float;
* `unit`: the letters that follow it, lower-cased (`'ml'`, `'l'`, `'g'`, `'kg'`).

Strings with no number-plus-unit pattern get NaN in both columns.
""",
    setup="""
SIZES = ["500ml", "1.5 L", "250 g", "2KG", "330 ml", "0.75l", "12 g", "1 kg", "approx. 2 kg", "family pack"]

def make(seed, n):
    rng = np.random.default_rng(seed)
    return {"s": pd.Series(rng.choice(SIZES, n), name="size", dtype="str")}

EXAMPLE = lambda: {"s": pd.Series(["500ml", "1.5 L", "250 g", "family pack"], name="size")}
""",
    tests="""
TESTS = [
    lambda: make(1, 20),
    lambda: make(2, 500),
    Test(lambda: {"s": pd.Series(["2KG"], name="size")}, "single upper-case value"),
]
""",
    hint1="`s.str.extract(r'(?P<amount>\\d+(?:\\.\\d+)?)\\s*(?P<unit>[A-Za-z]+)')` returns one column per named group; then convert/lower-case them.",
    hint2="out = s.str.extract(r'(?P<amount>\\d+(?:\\.\\d+)?)\\s*(?P<unit>[A-Za-z]+)')\nout.assign(amount=out['amount'].astype(float), unit=out['unit'].str.lower())",
    solution="""
def solve(s):
    out = s.str.extract(r"(?P<amount>\\d+(?:\\.\\d+)?)\\s*(?P<unit>[A-Za-z]+)")
    return out.assign(amount=out["amount"].astype(float), unit=out["unit"].str.lower())
""",
    explanation="""
Named groups `(?P<name>...)` become column names, and non-matching rows come back as NaN. `(?:...)` groups without capturing, which keeps the optional decimal part out of the output. Extracted values are strings, so convert explicitly.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.Series.str.extract.html"],
    wrong_solutions=[
        dict(code="""
def solve(s):
    out = s.str.extract(r"(?P<amount>\\d+)\\s*(?P<unit>[A-Za-z]+)")
    return out.assign(amount=out["amount"].astype(float), unit=out["unit"].str.lower())
""", why="decimals not captured"),
        dict(code="""
def solve(s):
    out = s.str.extract(r"(?P<amount>\\d+(?:\\.\\d+)?)\\s*(?P<unit>[A-Za-z]+)")
    return out.assign(amount=out["amount"].astype(float))
""", why="unit not lower-cased"),
    ],
),
dict(
    id="pd-023",
    title="Split 'Last, First' names",
    difficulty="Easy",
    tags=["strings"],
    signature="def solve(s: pd.Series) -> pd.DataFrame:",
    statement="""
`s` holds names formatted `'Last, First'` (the first name may itself contain spaces, e.g. `'Garcia, Ana Maria'`). Return a DataFrame with the same index and columns `first` and `last` (in that order), surrounding whitespace removed.
""",
    setup="""
FIRST = ["Ana", "Ben", "Chloe Anne", "Dev", "Eva"]
LAST = ["Smith", "Garcia", "Chen", "Van Der Berg", "Okafor"]

def make(seed, n):
    rng = np.random.default_rng(seed)
    return {"s": pd.Series([f"{l},  {f}" if rng.random() < 0.3 else f"{l}, {f}" for f, l in zip(rng.choice(FIRST, n), rng.choice(LAST, n))], name="name")}

EXAMPLE = lambda: {"s": pd.Series(["Smith, Ana", "Van Der Berg,  Chloe Anne"], name="name")}
""",
    tests="""
TESTS = [
    lambda: make(1, 10),
    lambda: make(2, 400),
    Test(lambda: {"s": pd.Series(["Doe, Jane"], name="name")}, "single name"),
]
""",
    hint1="`s.str.split(',', n=1, expand=True)` returns a DataFrame with columns 0 and 1; strip both with `.str.strip()`.",
    hint2="parts = s.str.split(',', n=1, expand=True)\npd.DataFrame({'first': parts[1].str.strip(), 'last': parts[0].str.strip()})",
    solution="""
def solve(s):
    parts = s.str.split(",", n=1, expand=True)
    return pd.DataFrame({"first": parts[1].str.strip(), "last": parts[0].str.strip()})
""",
    explanation="""
`expand=True` returns columns instead of lists, and `n=1` splits only at the first separator, so stray extra commas don't create extra columns. Without `expand` you get a Series of lists, which is rarely what you want.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.Series.str.split.html"],
    wrong_solutions=[
        dict(code="def solve(s):\n    parts = s.str.split(',', n=1, expand=True)\n    return pd.DataFrame({'first': parts[1], 'last': parts[0]})", why="whitespace kept"),
        dict(code="def solve(s):\n    parts = s.str.split(',', n=1, expand=True)\n    return pd.DataFrame({'last': parts[0].str.strip(), 'first': parts[1].str.strip()})", why="column order"),
    ],
),
dict(
    id="pd-024",
    title="Date parts and weekends",
    difficulty="Easy",
    tags=["dates & times"],
    signature="def solve(orders: pd.DataFrame) -> pd.DataFrame:",
    statement="""
From the datetime column `order_date`, return a DataFrame with the same index and columns `year`, `month`, `weekday` (the English day name, e.g. `'Monday'`) and `is_weekend` (True on Saturday and Sunday).
""",
    setup="""
EXAMPLE = lambda: {"orders": D.orders(seed=0, n=6)}
""",
    tests="""
TESTS = [
    lambda: {"orders": D.orders(seed=1, n=50)},
    lambda: {"orders": D.orders(seed=2, n=1000)},
    Test(lambda: {"orders": pd.DataFrame({"order_date": pd.to_datetime(["2024-06-01", "2024-06-02", "2024-06-03"])})}, "a weekend"),
]
""",
    hint1="The `.dt` accessor: `.dt.year`, `.dt.month`, `.dt.day_name()`, `.dt.dayofweek` (Monday = 0).",
    hint2="d = orders['order_date'].dt\npd.DataFrame({'year': d.year, 'month': d.month, 'weekday': d.day_name(), 'is_weekend': d.dayofweek >= 5})",
    solution="""
def solve(orders):
    d = orders["order_date"].dt
    return pd.DataFrame({"year": d.year, "month": d.month, "weekday": d.day_name(),
                         "is_weekend": d.dayofweek >= 5})
""",
    explanation="""
`.dt` exposes datetime fields element-wise (`year`, `month`, `day`, `hour`, `dayofweek`, `quarter`, `is_month_end`...) and methods like `day_name()`, `strftime()`, `floor('h')`. `dayofweek` counts Monday as 0, so the weekend is `>= 5`. The accessor only exists on datetime dtype, so parse first.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.Series.dt.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.Series.dt.dayofweek.html"],
    wrong_solutions=[
        dict(code="def solve(orders):\n    d = orders['order_date'].dt\n    return pd.DataFrame({'year': d.year, 'month': d.month, 'weekday': d.day_name(), 'is_weekend': d.dayofweek > 5})", why="Saturday missed"),
        dict(code="def solve(orders):\n    d = orders['order_date'].dt\n    return pd.DataFrame({'year': d.year, 'month': d.month, 'weekday': d.dayofweek, 'is_weekend': d.dayofweek >= 5})", why="weekday as a number"),
    ],
),
dict(
    id="pd-025",
    title="Parse hand-typed day-first dates",
    difficulty="Medium",
    tags=["dates & times", "type conversion"],
    signature="def solve(s: pd.Series) -> pd.Series:",
    statement="""
`s` holds dates typed as `'DD/MM/YYYY'` (so `'03/04/2024'` is 3 April 2024), including a few invalid entries such as `'31/02/2024'` or `'unknown'`. Return a datetime Series with the same index; invalid entries become `NaT`.
""",
    setup="""
def make(seed, n, bad=0.1):
    rng = np.random.default_rng(seed)
    d = pd.Timestamp("2023-01-01") + pd.to_timedelta(rng.integers(0, 700, n), unit="D")
    v = d.strftime("%d/%m/%Y").to_numpy().astype(object)
    v[0] = "03/04/2024"
    k = rng.random(n) < bad
    v[k] = rng.choice(["31/02/2024", "unknown", "", "2024-13-45"], k.sum())
    return {"s": pd.Series(v, name="signup", dtype="str")}

EXAMPLE = lambda: {"s": pd.Series(["03/04/2024", "25/12/2023", "31/02/2024", "unknown"], name="signup")}
""",
    tests="""
TESTS = [
    lambda: make(1, 30),
    lambda: make(2, 1000, bad=0.3),
    Test(lambda: {"s": pd.Series(["01/02/2024", "12/11/2024"], name="signup")}, "ambiguous days"),
]
""",
    hint1="`pd.to_datetime(s, format='%d/%m/%Y', errors='coerce')`.",
    hint2="pd.to_datetime(s, format='%d/%m/%Y', errors='coerce')",
    solution="""
def solve(s):
    return pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")
""",
    explanation="""
An explicit `format` is fast and unambiguous; without it pandas infers the format from the first value and may read `03/04` as March 4. `errors='coerce'` turns impossible dates into NaT instead of raising. Strip junk first if the format varies within a column.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.to_datetime.html"],
    wrong_solutions=[
        dict(code="def solve(s):\n    return pd.to_datetime(s, format='%m/%d/%Y', errors='coerce')", why="month first"),
        dict(code="def solve(s):\n    return pd.to_datetime(s, errors='coerce')", why="format inferred: month first"),
    ],
),
# ------------------------------------------------------------------ missing data / duplicates
dict(
    id="pd-026",
    title="Fill numeric gaps with column medians",
    difficulty="Easy",
    tags=["missing data"],
    signature="def solve(df: pd.DataFrame) -> pd.DataFrame:",
    statement="""
Fill the missing values of every **numeric** column of `df` with that column's median. Leave the non-numeric columns, including their missing values, untouched.
""",
    setup="""
def make(seed, n):
    df = D.hr(seed=seed, n=n)
    rng = np.random.default_rng(seed)
    df.loc[rng.random(n) < 0.1, "city"] = np.nan
    df.loc[rng.random(n) < 0.1, "years_experience"] = np.nan
    return {"df": df}

EXAMPLE = lambda: make(0, 8)
""",
    tests="""
TESTS = [
    lambda: make(1, 60),
    lambda: make(2, 1000),
    Test(lambda: {"df": D.orders(seed=3, n=10)}, "nothing missing"),
]
""",
    hint1="`df.fillna(value_series)` fills each column with the matching entry of the Series: pass the medians of the numeric columns.",
    hint2="df.fillna(df.median(numeric_only=True))",
    solution="""
def solve(df):
    return df.fillna(df.median(numeric_only=True))
""",
    explanation="""
`fillna` with a Series (or dict) fills column by column, matching on column names; columns missing from it are left alone. Medians are robust to outliers (salaries, prices). In a modelling pipeline, compute them on the training set only (`SimpleImputer`).
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.fillna.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.median.html"],
    wrong_solutions=[
        dict(code="def solve(df):\n    return df.fillna(df.mean(numeric_only=True))", why="mean instead of median"),
        dict(code="def solve(df):\n    return df.fillna(0)", why="zero fill, touches text columns"),
    ],
),
dict(
    id="pd-027",
    title="Fill missing salaries with the department median",
    difficulty="Medium",
    tags=["missing data", "group-wise ops"],
    signature="def solve(hr: pd.DataFrame) -> pd.Series:",
    statement="""
Return the `salary` column with each missing value replaced by the median **known** salary of that employee's `department`. Same index and name.
""",
    setup="""
EXAMPLE = lambda: {"hr": D.hr(seed=0, n=15, missing_share=0.25)}
""",
    tests="""
TESTS = [
    lambda: {"hr": D.hr(seed=1, n=80, missing_share=0.2)},
    lambda: {"hr": D.hr(seed=2, n=2000)},
    Test(lambda: {"hr": D.hr(seed=3, n=10, missing_share=0.0)}, "nothing missing"),
]
""",
    compare=dict(check_names=True),
    hint1="`groupby('department')['salary'].transform('median')` gives every row its group's median; pass it to `fillna`.",
    hint2="hr['salary'].fillna(hr.groupby('department')['salary'].transform('median'))",
    solution="""
def solve(hr):
    return hr["salary"].fillna(hr.groupby("department")["salary"].transform("median"))
""",
    explanation="""
`fillna` with a Series fills position-by-position on the index, so the fill values must be aligned to the rows: that is exactly what `transform` returns. `groupby(...).median()` returns one row per department and would misalign. Group-wise imputation keeps differences between groups (Engineering vs HR pay).
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.api.typing.DataFrameGroupBy.transform.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.Series.fillna.html"],
    wrong_solutions=[
        dict(code="def solve(hr):\n    return hr['salary'].fillna(hr['salary'].median())", why="company-wide median"),
        dict(code="def solve(hr):\n    return hr['salary'].fillna(hr.groupby('department')['salary'].median())", why="misaligned fill"),
    ],
),
dict(
    id="pd-028",
    title="Drop incomplete rows",
    difficulty="Easy",
    tags=["missing data"],
    signature="def solve(df: pd.DataFrame) -> pd.DataFrame:",
    statement="""
`df` is an HR table with 10 columns. Drop every row where `salary` is missing, and also every row that has **fewer than 8 non-missing values** overall. Keep the original index.
""",
    setup="""
def make(seed, n, holes=0.15):
    df = D.hr(seed=seed, n=n)
    rng = np.random.default_rng(seed)
    for c in ["city", "performance", "years_experience"]:
        df[c] = df[c].astype(object if c == "city" else float)
        df.loc[rng.random(n) < holes, c] = np.nan
    return {"df": df}

EXAMPLE = lambda: make(0, 12, holes=0.4)
""",
    tests="""
TESTS = [
    lambda: make(1, 50),
    lambda: make(2, 1000, holes=0.3),
    Test(lambda: make(3, 5, holes=0.0), "only salary/bonus gaps"),
]
""",
    hint1="`dropna(subset=[...])` looks at chosen columns; `dropna(thresh=k)` keeps rows with at least `k` non-missing values.",
    hint2="df.dropna(subset=['salary']).dropna(thresh=8)",
    solution="""
def solve(df):
    return df.dropna(subset=["salary"]).dropna(thresh=8)
""",
    explanation="""
Plain `dropna()` drops a row if *any* value is missing, which often throws away most of the data (here every employee without a bonus). `subset` targets the columns that matter; `thresh` keeps rows that are complete enough.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.dropna.html"],
    wrong_solutions=[
        dict(code="def solve(df):\n    return df.dropna()", why="drops any row with a NaN"),
        dict(code="def solve(df):\n    return df.dropna(thresh=8)", why="missing salary kept"),
    ],
),
dict(
    id="pd-029",
    title="Interpolate sensor gaps in time",
    difficulty="Medium",
    tags=["missing data", "time series"],
    signature="def solve(s: pd.Series) -> pd.Series:",
    statement="""
`s` is one sensor's temperature, indexed by **irregular** timestamps (a `DatetimeIndex`; some readings were never recorded), with NaN where a recorded reading is missing. Fill each NaN by linear interpolation **in time**, weighting by the actual time gaps rather than by row position. Leading NaNs stay NaN.
""",
    setup="""
def make(seed, days=1):
    r = D.sensors(seed=seed, n_sensors=1, days=days, drop_share=0.3, nan_share=0.15, spike_share=0)
    s = r.set_index("timestamp")["temperature"]
    s.iloc[0] = np.nan
    return {"s": s}

EXAMPLE = lambda: {"s": pd.Series([10.0, np.nan, 13.0, np.nan, 20.0],
                                  index=pd.to_datetime(["2024-01-01 00:00", "2024-01-01 01:00", "2024-01-01 04:00",
                                                        "2024-01-01 05:00", "2024-01-01 06:00"]), name="temperature")}
""",
    tests="""
TESTS = [
    lambda: make(1),
    lambda: make(2, days=5),
    Test(lambda: {"s": pd.Series([np.nan, 1.0, 2.0], index=pd.date_range("2024-01-01", periods=3, freq="7min"))}, "leading NaN, regular spacing"),
]
""",
    hint1="`Series.interpolate(method='time')` uses the DatetimeIndex distances.",
    hint2="s.interpolate(method='time')",
    solution="""
def solve(s):
    return s.interpolate(method="time")
""",
    explanation="""
The default `method='linear'` treats rows as equally spaced; with gaps in the timestamps that puts the filled value in the wrong place. `'time'` (or `'index'` for numeric indexes) weights by the actual distance. Leading NaNs have no left neighbour, so they stay unless you also pass `limit_direction='both'`.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.Series.interpolate.html"],
    wrong_solutions=[
        dict(code="def solve(s):\n    return s.interpolate()", why="by position"),
        dict(code="def solve(s):\n    return s.ffill()", why="forward fill"),
    ],
),
dict(
    id="pd-030",
    title="Keep the latest record per employee",
    difficulty="Medium",
    tags=["duplicates"],
    signature="def solve(raw: pd.DataFrame) -> pd.DataFrame:",
    statement="""
`raw` (an HR export, rows in no particular order) lists some employees twice: an older and a newer record, distinguished by the `updated` timestamp. Keep only the **most recent** record of each `employee_id`, and return the rows sorted by `employee_id` with a fresh `0..n-1` index.
""",
    setup="""
EXAMPLE = lambda: {"raw": D.hr_raw(seed=0, n=8, dup_share=0.3)}
""",
    tests="""
TESTS = [
    lambda: {"raw": D.hr_raw(seed=1, n=60)},
    lambda: {"raw": D.hr_raw(seed=2, n=1000, dup_share=0.2)},
    Test(lambda: {"raw": D.hr_raw(seed=3, n=6, dup_share=0.0)}, "no duplicates"),
]
""",
    hint1="Sort by `updated`, then `drop_duplicates(subset='employee_id', keep='last')`.",
    hint2="raw.sort_values('updated').drop_duplicates('employee_id', keep='last').sort_values('employee_id', ignore_index=True)",
    solution="""
def solve(raw):
    return (raw.sort_values("updated")
               .drop_duplicates("employee_id", keep="last")
               .sort_values("employee_id", ignore_index=True))
""",
    explanation="""
`drop_duplicates` keeps rows by **position**, so first decide what "last" means by sorting on the timestamp. `subset=` defines what counts as a duplicate (here the key), not the whole row. Equivalent: `raw.loc[raw.groupby('employee_id')['updated'].idxmax()]`.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.drop_duplicates.html"],
    wrong_solutions=[
        dict(code="def solve(raw):\n    return raw.drop_duplicates('employee_id', keep='last').sort_values('employee_id', ignore_index=True)", why="file order, not time order"),
        dict(code="def solve(raw):\n    return raw.sort_values('updated').drop_duplicates('employee_id').sort_values('employee_id', ignore_index=True)", why="keeps the oldest"),
    ],
),
dict(
    id="pd-031",
    title="Ordered job levels",
    difficulty="Medium",
    tags=["categoricals"],
    signature="def solve(hr: pd.DataFrame) -> pd.DataFrame:",
    statement="""
Convert `level` to an **ordered** categorical with the order `Junior < Mid < Senior < Lead`, then return the employees sorted by level, Junior first (ties keep their original order). Keep the index. Dtypes are checked.
""",
    setup="""
EXAMPLE = lambda: {"hr": D.hr(seed=0, n=8)}
""",
    tests="""
TESTS = [
    lambda: {"hr": D.hr(seed=1, n=60)},
    lambda: {"hr": D.hr(seed=2, n=1000)},
    Test(lambda: {"hr": D.hr(seed=3, n=1)}, "single row"),
]
""",
    compare=dict(check_dtype=True),
    hint1="`pd.Categorical(values, categories=[...], ordered=True)` (or `astype(pd.CategoricalDtype(...))`), then `sort_values(kind='stable')`.",
    hint2="lv = pd.Categorical(hr['level'], categories=['Junior', 'Mid', 'Senior', 'Lead'], ordered=True)\nhr.assign(level=lv).sort_values('level', kind='stable')",
    solution="""
def solve(hr):
    lv = pd.Categorical(hr["level"], categories=["Junior", "Mid", "Senior", "Lead"], ordered=True)
    return hr.assign(level=lv).sort_values("level", kind="stable")
""",
    explanation="""
Strings sort alphabetically (Junior, Lead, Mid, Senior); an ordered categorical sorts by your category order and supports comparisons like `hr['level'] > 'Mid'`. Values not listed in `categories` become NaN, which is a good way to catch typos.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.Categorical.html",
          "https://pandas.pydata.org/docs/user_guide/categorical.html#sorting-and-order"],
    wrong_solutions=[
        dict(code="def solve(hr):\n    return hr.sort_values('level', kind='stable')", why="alphabetical"),
        dict(code="def solve(hr):\n    return hr.assign(level=hr['level'].astype('category')).sort_values('level', kind='stable')", why="unordered, alphabetical categories"),
    ],
),
dict(
    id="pd-032",
    title="Category mix in percent",
    difficulty="Easy",
    tags=["aggregation"],
    signature="def solve(orders: pd.DataFrame) -> pd.Series:",
    statement="""
Return the share of orders in each `category`, in **percent** rounded to 1 decimal, as a Series indexed by category and sorted from the most to the least common. Categories with equal shares may appear in any order.
""",
    setup="""
EXAMPLE = lambda: {"orders": D.orders(seed=0, n=20)}
""",
    tests="""
TESTS = [
    lambda: {"orders": D.orders(seed=1, n=150)},
    lambda: {"orders": D.orders(seed=2, n=3000)},
    Test(lambda: {"orders": D.orders(seed=3, n=1)}, "single order"),
]

def check(got, exp, inputs):
    if not isinstance(got, pd.Series):
        fail(f"expected a Series, got {type(got).__name__}")
    msg = compare(got.sort_index(), exp.sort_index())
    if msg:
        return msg
    if not got.is_monotonic_decreasing:
        fail("not sorted from most to least common")
""",
    hint1="`value_counts(normalize=True)` gives shares (0-1), sorted by frequency; multiply by 100 and `round(1)`.",
    hint2="orders['category'].value_counts(normalize=True).mul(100).round(1)",
    solution="""
def solve(orders):
    return orders["category"].value_counts(normalize=True).mul(100).round(1)
""",
    explanation="""
`value_counts()` sorts by count, descending, and drops NaN unless `dropna=False`. `normalize=True` divides by the number of non-null values. Use `.sort_index()` when you want the categories in label order instead.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.Series.value_counts.html"],
    wrong_solutions=[
        dict(code="def solve(orders):\n    return orders['category'].value_counts(normalize=True).round(1)", why="fractions, not percent"),
        dict(code="def solve(orders):\n    return orders['category'].value_counts()", why="counts"),
    ],
),
dict(
    id="pd-033",
    title="Age bands",
    difficulty="Medium",
    tags=["binning"],
    signature="def solve(customers: pd.DataFrame) -> pd.Series:",
    statement="""
Bin `age` into the bands `'18-24'`, `'25-34'`, `'35-49'`, `'50-64'` and `'65+'`, so that 25 falls in `'25-34'` and 65 in `'65+'`. Return the labels as a **categorical** Series with the same index. Dtypes are checked.
""",
    setup="""
def make(seed, n):
    c = D.customers(seed=seed, n=n)
    c.loc[c.index[:5], "age"] = [18, 25, 35, 50, 65][: min(5, n)]
    return {"customers": c}

EXAMPLE = lambda: make(0, 8)
""",
    tests="""
TESTS = [
    lambda: make(1, 50),
    lambda: make(2, 1000),
    Test(lambda: make(3, 3), "edge ages"),
]
""",
    compare=dict(check_dtype=True),
    hint1="`pd.cut(s, bins, right=False, labels=[...])`: bins are right-closed by default.",
    hint2="pd.cut(customers['age'], [18, 25, 35, 50, 65, np.inf], right=False,\n       labels=['18-24', '25-34', '35-49', '50-64', '65+'])",
    solution="""
def solve(customers):
    return pd.cut(customers["age"], [18, 25, 35, 50, 65, np.inf], right=False,
                  labels=["18-24", "25-34", "35-49", "50-64", "65+"])
""",
    explanation="""
`pd.cut` uses fixed edges you choose; by default intervals are `(a, b]`, so 25 would land in the first band and 18 in none. `right=False` gives `[a, b)`. Use `np.inf` as the last edge for an open-ended band. Values outside all bins become NaN.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.cut.html"],
    wrong_solutions=[
        dict(code="def solve(customers):\n    return pd.cut(customers['age'], [18, 25, 35, 50, 65, np.inf], labels=['18-24', '25-34', '35-49', '50-64', '65+'])", why="right-closed"),
        dict(code="def solve(customers):\n    return pd.cut(customers['age'], [18, 25, 35, 50, 65, 120], right=False, labels=['18-24', '25-34', '35-49', '50-64', '65+']).astype(str)", why="strings, not categorical"),
    ],
),
dict(
    id="pd-034",
    title="Spend quartiles",
    difficulty="Easy",
    tags=["binning"],
    signature="def solve(spend: pd.Series) -> pd.Series:",
    statement="""
`spend` holds each customer's annual spend (skewed: a few big spenders). Label every customer with their spend **quartile**, `'Q1'` (lowest quarter) to `'Q4'`, so that the four groups have (nearly) equal sizes. Return a categorical Series with the same index. Dtypes are checked.
""",
    setup="""
def make(seed, n):
    rng = np.random.default_rng(seed)
    return {"spend": pd.Series(np.round(rng.lognormal(6, 1.1, n), 2), name="spend")}

EXAMPLE = lambda: make(0, 12)
""",
    tests="""
TESTS = [
    lambda: make(1, 40),
    lambda: make(2, 2000),
    Test(lambda: make(3, 4), "four customers"),
]
""",
    compare=dict(check_dtype=True),
    hint1="`pd.qcut(s, 4, labels=[...])` cuts at sample quantiles (equal counts), unlike `pd.cut`, which uses equal widths.",
    hint2="pd.qcut(spend, 4, labels=['Q1', 'Q2', 'Q3', 'Q4'])",
    solution="""
def solve(spend):
    return pd.qcut(spend, 4, labels=["Q1", "Q2", "Q3", "Q4"])
""",
    explanation="""
`qcut` picks the edges from the data's quantiles, so each bin holds about the same number of rows. On skewed data, `cut(s, 4)` puts almost everyone in the first bin. If many values tie at an edge, `qcut` raises "Bin edges must be unique": pass `duplicates='drop'`, or rank first (`s.rank(method='first')`).
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.qcut.html"],
    wrong_solutions=[
        dict(code="def solve(spend):\n    return pd.cut(spend, 4, labels=['Q1', 'Q2', 'Q3', 'Q4'])", why="equal-width bins"),
        dict(code="def solve(spend):\n    return pd.qcut(spend, 4, labels=['Q4', 'Q3', 'Q2', 'Q1'])", why="labels reversed"),
    ],
),
# ------------------------------------------------------------------ groupby
dict(
    id="pd-035",
    title="Region summary with named aggregations",
    difficulty="Easy",
    tags=["aggregation"],
    signature="def solve(orders: pd.DataFrame) -> pd.DataFrame:",
    statement="""
Return one row per region (index = `region`, sorted A to Z) with exactly these columns, in this order:

* `n_orders`: number of orders;
* `revenue`: total revenue;
* `avg_qty`: mean quantity per order.
""",
    setup="""
EXAMPLE = lambda: {"orders": D.orders(seed=0, n=15)}
""",
    tests="""
TESTS = [
    lambda: {"orders": D.orders(seed=1, n=100)},
    lambda: {"orders": D.orders(seed=2, n=3000, n_customers=400)},
    Test(lambda: {"orders": D.orders(seed=3, n=2)}, "two orders"),
]
""",
    hint1="Named aggregation: `groupby('region').agg(new_name=('column', 'func'), ...)`.",
    hint2="orders.groupby('region').agg(n_orders=('order_id', 'count'), revenue=('revenue', 'sum'), avg_qty=('quantity', 'mean'))",
    solution="""
def solve(orders):
    return orders.groupby("region").agg(
        n_orders=("order_id", "count"),
        revenue=("revenue", "sum"),
        avg_qty=("quantity", "mean"),
    )
""",
    explanation="""
Named aggregation gives flat, readable column names in one step: no MultiIndex columns to rename afterwards. `groupby` sorts the group keys by default (`sort=False` keeps first-seen order). Add `as_index=False` or `.reset_index()` to get `region` back as a column.
""",
    docs=["https://pandas.pydata.org/docs/user_guide/groupby.html#named-aggregation",
          "https://pandas.pydata.org/docs/reference/api/pandas.api.typing.DataFrameGroupBy.agg.html"],
    wrong_solutions=[
        dict(code="def solve(orders):\n    return orders.groupby('region').agg(n_orders=('order_id', 'count'), revenue=('revenue', 'mean'), avg_qty=('quantity', 'mean'))", why="mean revenue"),
        dict(code="def solve(orders):\n    return orders.groupby('region').agg(revenue=('revenue', 'sum'), n_orders=('order_id', 'count'), avg_qty=('quantity', 'mean'))", why="column order"),
    ],
),
dict(
    id="pd-036",
    title="Each customer's share of their region's revenue",
    difficulty="Medium",
    tags=["group-wise ops"],
    signature="def solve(orders: pd.DataFrame) -> pd.DataFrame:",
    statement="""
`orders` has one row per order: `order_id, customer_id, order_date, region, category, quantity, unit_price, revenue`. Each customer belongs to exactly one region.

Return one row per customer with columns `customer_id, region, revenue, share`, where `revenue` is the customer's total revenue and `share` is that total divided by the total revenue of the customer's region.

Sort by `region` ascending, then `share` descending (ties: `customer_id` ascending), and reset the index to 0..n-1.
""",
    setup="""
EXAMPLE = lambda: {"orders": D.orders(seed=0, n=12, n_customers=6)}
""",
    tests="""
TESTS = [
    lambda: {"orders": D.orders(seed=1, n=60, n_customers=15)},
    lambda: {"orders": D.orders(seed=2, n=400, n_customers=80)},
    Test(lambda: {"orders": D.orders(seed=3, n=1)}, "single order"),
    Test(lambda: {"orders": D.orders(seed=4, n=30, n_customers=3)}, "few customers per region"),
]
""",
    hint1="Total per customer with `groupby(...).sum()`, then divide by the region total broadcast back to each row with `groupby('region')['revenue'].transform('sum')`.",
    hint2="out = orders.groupby(['customer_id', 'region'], as_index=False)['revenue'].sum()\nout['share'] = out['revenue'] / out.groupby('region')['revenue'].transform('sum')",
    solution="""
def solve(orders):
    out = orders.groupby(["customer_id", "region"], as_index=False)["revenue"].sum()
    out["share"] = out["revenue"] / out.groupby("region")["revenue"].transform("sum")
    return out.sort_values(["region", "share", "customer_id"],
                           ascending=[True, False, True], ignore_index=True)
""",
    explanation="""
`transform('sum')` returns the region total aligned to every row, so the division is one vectorized step. Using `.sum()` / `.agg()` instead gives one row per *region*; assigning that back aligns on the index and silently produces NaN. The alternative is merging the region totals back in.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.api.typing.DataFrameGroupBy.transform.html",
          "https://pandas.pydata.org/docs/user_guide/groupby.html#transformation"],
    wrong_solutions=[
        dict(code="""
def solve(orders):
    out = orders.groupby(["customer_id", "region"], as_index=False)["revenue"].sum()
    out["share"] = out["revenue"] / out["revenue"].sum()
    return out.sort_values(["region", "share", "customer_id"], ascending=[True, False, True], ignore_index=True)
""", why="share of the grand total, not of the region"),
        dict(code="""
def solve(orders):
    out = orders.groupby(["customer_id", "region"], as_index=False)["revenue"].sum()
    out["share"] = out["revenue"] / out.groupby("region")["revenue"].sum()
    return out.sort_values(["region", "share", "customer_id"], ascending=[True, False, True], ignore_index=True)
""", why="agg instead of transform: misaligned, NaN"),
        dict(code="""
def solve(orders):
    out = orders.groupby(["customer_id", "region"], as_index=False)["revenue"].sum()
    out["share"] = out["revenue"] / out.groupby("region")["revenue"].transform("sum")
    return out.sort_values(["region", "share"], ignore_index=True)
""", why="share sorted ascending"),
    ],
),
dict(
    id="pd-037",
    title="Head count vs reported salaries",
    difficulty="Easy",
    tags=["aggregation"],
    signature="def solve(hr: pd.DataFrame) -> pd.DataFrame:",
    statement="""
Per department (index = `department`, sorted A to Z), return two columns:

* `headcount`: number of employees, **including** those whose salary is missing;
* `n_salaries`: number of employees with a known salary.
""",
    setup="""
EXAMPLE = lambda: {"hr": D.hr(seed=0, n=15, missing_share=0.2)}
""",
    tests="""
TESTS = [
    lambda: {"hr": D.hr(seed=1, n=100, missing_share=0.1)},
    lambda: {"hr": D.hr(seed=2, n=3000)},
    Test(lambda: {"hr": D.hr(seed=3, n=4, missing_share=0.5)}, "tiny"),
]
""",
    hint1="`GroupBy.size()` counts rows; `GroupBy[col].count()` counts non-missing values.",
    hint2="g = hr.groupby('department')\npd.DataFrame({'headcount': g.size(), 'n_salaries': g['salary'].count()})",
    solution="""
def solve(hr):
    g = hr.groupby("department")
    return pd.DataFrame({"headcount": g.size(), "n_salaries": g["salary"].count()})
""",
    explanation="""
`size()` counts rows, NaN included; `count()` counts non-null values per column. Mixing them up silently undercounts groups whenever data is missing. `value_counts()` on the key column equals `size()`, but sorted by count.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.api.typing.DataFrameGroupBy.size.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.api.typing.DataFrameGroupBy.count.html"],
    wrong_solutions=[
        dict(code="def solve(hr):\n    g = hr.groupby('department')\n    return pd.DataFrame({'headcount': g['salary'].count(), 'n_salaries': g['salary'].count()})", why="headcount ignores missing salaries"),
        dict(code="def solve(hr):\n    g = hr.groupby('department')\n    return pd.DataFrame({'headcount': g.size(), 'n_salaries': g.size()})", why="n_salaries counts rows"),
    ],
),
dict(
    id="pd-038",
    title="Orders of repeat customers only",
    difficulty="Medium",
    tags=["group-wise ops"],
    signature="def solve(orders: pd.DataFrame) -> pd.DataFrame:",
    statement="""
Keep only the orders placed by customers who have **at least 3 orders** in total. Return those rows with all columns, the original index and order.
""",
    setup="""
EXAMPLE = lambda: {"orders": D.orders(seed=0, n=15, n_customers=8)}
""",
    tests="""
TESTS = [
    lambda: {"orders": D.orders(seed=1, n=80, n_customers=30)},
    lambda: {"orders": D.orders(seed=2, n=3000, n_customers=500)},
    Test(lambda: {"orders": D.orders(seed=3, n=4, n_customers=4)}, "maybe nobody qualifies"),
]
""",
    hint1="`groupby(key).filter(lambda g: ...)` keeps whole groups whose condition is True (or compare `transform('size')` with 3).",
    hint2="orders.groupby('customer_id').filter(lambda g: len(g) >= 3)",
    solution="""
def solve(orders):
    return orders.groupby("customer_id").filter(lambda g: len(g) >= 3)
""",
    explanation="""
`filter` returns the original rows (index and order preserved) of the groups that pass. The vectorized equivalent, faster with many groups, is `orders[orders.groupby('customer_id')['order_id'].transform('size') >= 3]`.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.api.typing.DataFrameGroupBy.filter.html"],
    wrong_solutions=[
        dict(code="def solve(orders):\n    return orders.groupby('customer_id').filter(lambda g: len(g) > 3)", why="more than 3"),
        dict(code="def solve(orders):\n    counts = orders['customer_id'].value_counts()\n    return orders[orders['customer_id'].isin(counts[counts >= 3].index)].sort_values('customer_id')", why="re-sorted"),
    ],
),
dict(
    id="pd-039",
    title="Order number per customer",
    difficulty="Easy",
    tags=["group-wise ops"],
    signature="def solve(orders: pd.DataFrame) -> pd.Series:",
    statement="""
`orders` is sorted by date. For each order, return which order it is **for that customer**: 1 for the customer's first order, 2 for the second, and so on. Return a Series aligned to `orders`' index.
""",
    setup="""
EXAMPLE = lambda: {"orders": D.orders(seed=0, n=12, n_customers=4)}
""",
    tests="""
TESTS = [
    lambda: {"orders": D.orders(seed=1, n=80)},
    lambda: {"orders": D.orders(seed=2, n=3000, n_customers=300)},
    Test(lambda: {"orders": D.orders(seed=3, n=1)}, "single order"),
]
""",
    hint1="`groupby(key).cumcount()` numbers the rows within each group from 0.",
    hint2="orders.groupby('customer_id').cumcount() + 1",
    solution="""
def solve(orders):
    return orders.groupby("customer_id").cumcount() + 1
""",
    explanation="""
`cumcount` follows the current row order, so sort first if needed. Typical uses: "first purchase" flags (`== 0`), the n-th order per user, or cohort analysis. `groupby(...).rank(method='first')` on a date column does the same without relying on the row order.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.api.typing.DataFrameGroupBy.cumcount.html"],
    wrong_solutions=[
        dict(code="def solve(orders):\n    return orders.groupby('customer_id').cumcount()", why="starts at 0"),
        dict(code="def solve(orders):\n    return orders.groupby('customer_id')['order_id'].transform('size')", why="total orders"),
    ],
),
dict(
    id="pd-040",
    title="Monthly revenue per region",
    difficulty="Medium",
    tags=["aggregation", "dates & times"],
    signature="def solve(orders: pd.DataFrame) -> pd.DataFrame:",
    statement="""
Return total revenue per region and calendar month as a long table with columns `region`, `month` (text like `'2024-03'`) and `revenue`, sorted by region then month, with a default 0..n-1 index. Only combinations that have orders appear.
""",
    setup="""
EXAMPLE = lambda: {"orders": D.orders(seed=0, n=20)}
""",
    tests="""
TESTS = [
    lambda: {"orders": D.orders(seed=1, n=150)},
    lambda: {"orders": D.orders(seed=2, n=3000)},
    Test(lambda: {"orders": D.orders(seed=3, n=1)}, "single order"),
]
""",
    hint1="Derive the month key with `.dt.strftime('%Y-%m')` (or `.dt.to_period('M')`), then `groupby([...], as_index=False)['revenue'].sum()`.",
    hint2="orders.assign(month=orders['order_date'].dt.strftime('%Y-%m')).groupby(['region', 'month'], as_index=False)['revenue'].sum()",
    solution="""
def solve(orders):
    return (orders.assign(month=orders["order_date"].dt.strftime("%Y-%m"))
                  .groupby(["region", "month"], as_index=False)["revenue"].sum())
""",
    explanation="""
Group by several keys with a list; `as_index=False` keeps the keys as columns (equivalent to `.reset_index()`). The result is sorted by the keys. For a wide month-by-region table use `pivot_table` or `.unstack()`; for a regular time series, `resample('MS')` per region.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.groupby.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.Series.dt.strftime.html"],
    wrong_solutions=[
        dict(code="def solve(orders):\n    return orders.assign(month=orders['order_date'].dt.strftime('%Y-%m')).groupby(['month', 'region'], as_index=False)['revenue'].sum()", why="sorted by month first, column order"),
        dict(code="def solve(orders):\n    return orders.assign(month=orders['order_date'].dt.strftime('%m')).groupby(['region', 'month'], as_index=False)['revenue'].sum()", why="month without year"),
    ],
),
# ------------------------------------------------------------------ reshaping
dict(
    id="pd-041",
    title="Revenue matrix with totals",
    difficulty="Medium",
    tags=["reshaping", "aggregation"],
    signature="def solve(orders: pd.DataFrame) -> pd.DataFrame:",
    statement="""
Build a region by category table of **total** revenue: one row per region (A to Z), one column per category (A to Z), `0` where a combination has no orders, plus a final row and a final column named `All` holding the totals.
""",
    setup="""
EXAMPLE = lambda: {"orders": D.orders(seed=0, n=20)}
""",
    tests="""
TESTS = [
    lambda: {"orders": D.orders(seed=1, n=150)},
    lambda: {"orders": D.orders(seed=2, n=4000)},
    Test(lambda: {"orders": D.orders(seed=3, n=4)}, "sparse"),
]
""",
    hint1="`pivot_table(index=..., columns=..., values=..., aggfunc='sum', fill_value=0, margins=True)`.",
    hint2="orders.pivot_table(index='region', columns='category', values='revenue', aggfunc='sum', fill_value=0, margins=True)",
    solution="""
def solve(orders):
    return orders.pivot_table(index="region", columns="category", values="revenue",
                              aggfunc="sum", fill_value=0, margins=True)
""",
    explanation="""
`pivot_table` defaults to `aggfunc='mean'`, a frequent silent bug when you wanted totals. `margins=True` adds the `All` row and column (`margins_name=` renames it). `pivot` (no aggregation) raises on duplicate index/column pairs; `pivot_table` aggregates them.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.pivot_table.html"],
    wrong_solutions=[
        dict(code="def solve(orders):\n    return orders.pivot_table(index='region', columns='category', values='revenue', fill_value=0, margins=True)", why="default aggfunc is mean"),
        dict(code="def solve(orders):\n    return orders.pivot_table(index='region', columns='category', values='revenue', aggfunc='sum', fill_value=0)", why="no totals"),
    ],
),
dict(
    id="pd-042",
    title="Internet mix by contract type",
    difficulty="Easy",
    tags=["reshaping"],
    signature="def solve(churn: pd.DataFrame) -> pd.DataFrame:",
    statement="""
Return a table with one row per `contract` type and one column per `internet` type, where each cell is the **share of that row's customers** with that internet type (each row sums to 1). Rows and columns sorted A to Z.
""",
    setup="""
EXAMPLE = lambda: {"churn": D.churn(seed=0, n=40)}
""",
    tests="""
TESTS = [
    lambda: {"churn": D.churn(seed=1, n=300)},
    lambda: {"churn": D.churn(seed=2, n=5000)},
    Test(lambda: {"churn": D.churn(seed=3, n=6)}, "tiny"),
]
""",
    hint1="`pd.crosstab(rows, cols, normalize='index')` divides each row by its total.",
    hint2="pd.crosstab(churn['contract'], churn['internet'], normalize='index')",
    solution="""
def solve(churn):
    return pd.crosstab(churn["contract"], churn["internet"], normalize="index")
""",
    explanation="""
`crosstab` counts co-occurrences of two (or more) factors. `normalize='index'` gives row shares (P(internet given contract)), `'columns'` column shares, `True` shares of the grand total. Add `values=` and `aggfunc=` to aggregate a third column instead of counting.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.crosstab.html"],
    wrong_solutions=[
        dict(code="def solve(churn):\n    return pd.crosstab(churn['contract'], churn['internet'], normalize='columns')", why="column shares"),
        dict(code="def solve(churn):\n    return pd.crosstab(churn['contract'], churn['internet'], normalize=True)", why="share of the total"),
    ],
),
dict(
    id="pd-043",
    title="Quarterly columns to long format",
    difficulty="Easy",
    tags=["reshaping"],
    signature="def solve(wide: pd.DataFrame) -> pd.DataFrame:",
    statement="""
`wide` has one row per store with columns `store, Q1, Q2, Q3, Q4` (sales). Return a long table with columns `store, quarter, sales`, ordered by store and then by quarter (Q1 to Q4), with a default 0..n-1 index.
""",
    setup="""
def make(seed, n):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({"store": [f"S{i:02d}" for i in rng.permutation(n)]})
    for q in ["Q1", "Q2", "Q3", "Q4"]:
        df[q] = np.round(rng.gamma(5, 2000, n), 0)
    return {"wide": df}

EXAMPLE = lambda: make(0, 3)
""",
    tests="""
TESTS = [
    lambda: make(1, 10),
    lambda: make(2, 300),
    Test(lambda: make(3, 1), "one store"),
]
""",
    hint1="`df.melt(id_vars=..., var_name=..., value_name=...)`, then sort.",
    hint2="wide.melt(id_vars='store', var_name='quarter', value_name='sales').sort_values(['store', 'quarter'], ignore_index=True)",
    solution="""
def solve(wide):
    return (wide.melt(id_vars="store", var_name="quarter", value_name="sales")
                .sort_values(["store", "quarter"], ignore_index=True))
""",
    explanation="""
`melt` turns columns into rows ("wide to long"): `id_vars` stay as identifiers, the other columns' names go to `var_name` and their values to `value_name`. Its output is ordered column by column, so sort if you need row-major order. `pivot` is the inverse.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.melt.html"],
    wrong_solutions=[
        dict(code="def solve(wide):\n    return wide.melt(id_vars='store', var_name='quarter', value_name='sales')", why="not sorted by store"),
        dict(code="def solve(wide):\n    return wide.melt(id_vars='store').sort_values(['store', 'variable'], ignore_index=True)", why="default column names"),
    ],
),
dict(
    id="pd-044",
    title="Long prices to a wide table",
    difficulty="Easy",
    tags=["reshaping"],
    signature="def solve(prices: pd.DataFrame) -> pd.DataFrame:",
    statement="""
`prices` is a long daily panel with columns `date, ticker, close, volume`. Return a wide table of **closing prices**: index = date, one column per ticker (A to Z).
""",
    setup="""
EXAMPLE = lambda: {"prices": D.prices(seed=0, n_days=4, n_tickers=3)}
""",
    tests="""
TESTS = [
    lambda: {"prices": D.prices(seed=1, n_days=30, n_tickers=6)},
    lambda: {"prices": D.prices(seed=2, n_days=500, n_tickers=20)},
    Test(lambda: {"prices": D.prices(seed=3, n_days=20, n_tickers=5, gaps=True)}, "missing days become NaN"),
]
""",
    hint1="`df.pivot(index=..., columns=..., values=...)`.",
    hint2="prices.pivot(index='date', columns='ticker', values='close')",
    solution="""
def solve(prices):
    return prices.pivot(index="date", columns="ticker", values="close")
""",
    explanation="""
`pivot` reshapes without aggregating and raises if a (date, ticker) pair appears twice; then you need `pivot_table` or a dedupe. Without `values=` you get MultiIndex columns for every remaining column. The inverse is `stack()` or `melt()`.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.pivot.html"],
    wrong_solutions=[
        dict(code="def solve(prices):\n    return prices.pivot(index='date', columns='ticker')", why="all value columns"),
        dict(code="def solve(prices):\n    return prices.pivot(index='ticker', columns='date', values='close')", why="transposed"),
    ],
),
dict(
    id="pd-045",
    title="From (region, category) pairs to a grid",
    difficulty="Easy",
    tags=["reshaping"],
    signature="def solve(s: pd.Series) -> pd.DataFrame:",
    statement="""
`s` is total revenue indexed by a (`region`, `category`) MultiIndex (only combinations that occurred are present). Return a DataFrame with regions as rows and categories as columns; combinations that never occurred must be `0.0`.
""",
    setup="""
def make(seed, n):
    o = D.orders(seed=seed, n=n)
    return {"s": o.groupby(["region", "category"])["revenue"].sum()}

EXAMPLE = lambda: make(0, 12)
""",
    tests="""
TESTS = [
    lambda: make(1, 60),
    lambda: make(2, 2000),
    Test(lambda: make(3, 2), "two pairs"),
]
""",
    hint1="`Series.unstack()` moves the last index level to the columns; `fill_value=` replaces the holes.",
    hint2="s.unstack(fill_value=0.0)",
    solution="""
def solve(s):
    return s.unstack(fill_value=0.0)
""",
    explanation="""
`unstack(level)` pivots an index level into columns (the last level by default) and `stack()` does the reverse. Pass `level='region'` or `0` to unstack a different level. Missing combinations become NaN unless you pass `fill_value`.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.Series.unstack.html",
          "https://pandas.pydata.org/docs/user_guide/reshaping.html"],
    wrong_solutions=[
        dict(code="def solve(s):\n    return s.unstack(0, fill_value=0.0)", why="regions as columns"),
        dict(code="def solve(s):\n    return s.unstack()", why="holes are NaN"),
    ],
),
dict(
    id="pd-046",
    title="One ticker out of a (date, ticker) panel",
    difficulty="Medium",
    tags=["reshaping", "selection"],
    signature="def solve(panel: pd.DataFrame, ticker: str) -> pd.Series:",
    statement="""
`panel` is indexed by a (`date`, `ticker`) MultiIndex and has columns `close` and `volume`. Return the `close` series of `ticker`, indexed by **date only**.
""",
    setup="""
def make(seed, n_days, n_tickers, ticker):
    return {"panel": D.prices(seed=seed, n_days=n_days, n_tickers=n_tickers).set_index(["date", "ticker"]), "ticker": ticker}

EXAMPLE = lambda: make(0, 4, 3, "BRVO")
""",
    tests="""
TESTS = [
    lambda: make(1, 30, 5, "ECHO"),
    lambda: make(2, 500, 20, "ALFA"),
    Test(lambda: make(3, 1, 2, "BRVO"), "one date"),
]
""",
    hint1="`df.xs(key, level='ticker')` selects on an inner level and drops it.",
    hint2="panel.xs(ticker, level='ticker')['close']",
    solution="""
def solve(panel, ticker):
    return panel.xs(ticker, level="ticker")["close"]
""",
    explanation="""
`.loc[key]` matches the **first** level (`date` here). For an inner level use `xs(key, level=...)`, `panel.loc[(slice(None), ticker), 'close']` (keeps both levels), or `pd.IndexSlice`. `xs` drops the selected level by default (`drop_level=False` keeps it).
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.xs.html",
          "https://pandas.pydata.org/docs/user_guide/advanced.html"],
    wrong_solutions=[
        dict(code="def solve(panel, ticker):\n    return panel.xs(ticker, level='ticker', drop_level=False)['close']", why="MultiIndex kept"),
        dict(code="def solve(panel, ticker):\n    return panel.loc[(slice(None), ticker), 'close']", why="both levels kept"),
    ],
),
# ------------------------------------------------------------------ joins
dict(
    id="pd-047",
    title="Join orders to customers with different key names",
    difficulty="Easy",
    tags=["joining"],
    signature="def solve(orders: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:",
    statement="""
In this extract `orders` identifies the customer with `cust_id`, while `customers` uses `customer_id`. Attach `segment` and `signup_date` to **every** order: orders whose customer is unknown keep NaN/NaT.

Return all of `orders`' columns followed by `segment`, `signup_date` (no duplicate key column), with the orders in their original order and a default index.
""",
    setup="""
def make(seed, n, n_customers):
    o = D.orders(seed=seed, n=n, n_customers=n_customers).rename(columns={"customer_id": "cust_id"})
    return {"orders": o, "customers": D.customers(seed=seed, n=n_customers)}

EXAMPLE = lambda: make(0, 8, 5)
""",
    tests="""
TESTS = [
    lambda: make(1, 60, 20),
    lambda: make(2, 2000, 300),
    Test(lambda: {**make(3, 10, 4), "customers": D.customers(seed=3, n=4).iloc[:0]}, "empty customers table"),
]
""",
    hint1="`merge(right, left_on=..., right_on=..., how='left')`, then drop the right key.",
    hint2="orders.merge(customers[['customer_id', 'segment', 'signup_date']], left_on='cust_id', right_on='customer_id', how='left').drop(columns='customer_id')",
    solution="""
def solve(orders, customers):
    return (orders.merge(customers[["customer_id", "segment", "signup_date"]],
                         left_on="cust_id", right_on="customer_id", how="left")
                  .drop(columns="customer_id"))
""",
    explanation="""
`how='left'` keeps every left row, even without a match; the default `'inner'` silently drops orders from unknown customers. With `left_on`/`right_on` both key columns are kept, so drop one. A left merge also preserves the left row order (but resets the index).
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.merge.html"],
    wrong_solutions=[
        dict(code="def solve(orders, customers):\n    return orders.merge(customers[['customer_id', 'segment', 'signup_date']], left_on='cust_id', right_on='customer_id').drop(columns='customer_id')", why="inner join drops unknown customers"),
        dict(code="def solve(orders, customers):\n    return orders.merge(customers[['customer_id', 'segment', 'signup_date']], left_on='cust_id', right_on='customer_id', how='left')", why="duplicate key column"),
    ],
),
dict(
    id="pd-048",
    title="Audit a join",
    difficulty="Medium",
    tags=["joining"],
    signature="def solve(orders: pd.DataFrame, customers: pd.DataFrame) -> pd.Series:",
    statement="""
Before trusting a join, audit it. Do a **full outer** join of `orders` and `customers` on `customer_id` and count the resulting rows by origin. Return a Series of integers indexed exactly `['left_only', 'right_only', 'both']` (in that order): orders with an unknown customer, customers without any order, and matched rows.
""",
    setup="""
def make(seed, n, n_customers):
    return {"orders": D.orders(seed=seed, n=n, n_customers=n_customers, unknown_share=0.1),
            "customers": D.customers(seed=seed, n=n_customers)}

EXAMPLE = lambda: make(0, 10, 12)
""",
    tests="""
TESTS = [
    lambda: make(1, 60, 50),
    lambda: make(2, 2000, 300),
    Test(lambda: {"orders": D.orders(seed=3, n=5, n_customers=3, unknown_share=0.0), "customers": D.customers(seed=3, n=3)}, "everything matches"),
]
""",
    hint1="`merge(..., how='outer', indicator=True)` adds a `_merge` column; count it with `value_counts()` and `reindex` to fix the order.",
    hint2="m = orders.merge(customers, on='customer_id', how='outer', indicator=True)\nm['_merge'].value_counts().reindex(['left_only', 'right_only', 'both'])",
    solution="""
def solve(orders, customers):
    m = orders.merge(customers, on="customer_id", how="outer", indicator=True)
    return m["_merge"].value_counts().reindex(["left_only", "right_only", "both"])
""",
    explanation="""
`indicator=True` labels each row `left_only`, `right_only` or `both`: the quickest way to find unmatched keys (typos, stale ids) before they silently become NaN. An anti-join is `m[m['_merge'] == 'left_only']`, or simply `orders[~orders['customer_id'].isin(customers['customer_id'])]`.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.merge.html",
          "https://pandas.pydata.org/docs/user_guide/merging.html#merging-indicator"],
    wrong_solutions=[
        dict(code="def solve(orders, customers):\n    m = orders.merge(customers, on='customer_id', how='left', indicator=True)\n    return m['_merge'].value_counts().reindex(['left_only', 'right_only', 'both'])", why="left join: right_only always 0"),
        dict(code="def solve(orders, customers):\n    m = orders.merge(customers, on='customer_id', how='outer', indicator=True)\n    return m['_merge'].value_counts()", why="order not fixed"),
    ],
),
dict(
    id="pd-049",
    title="A safe many-to-one join",
    difficulty="Hard",
    tags=["joining", "duplicates"],
    signature="def solve(orders: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:",
    statement="""
`customers` accidentally contains several rows for some `customer_id`s (the customer re-registered; the row with the **latest** `signup_date` is the valid one). Attach `segment` to every order with a left join that is guaranteed **many-to-one**, so the number of order rows cannot grow.

Return `orders` with one extra column `segment`, orders in their original order, default index.
""",
    setup="""
def make(seed, n, n_customers, n_dup):
    rng = np.random.default_rng(seed)
    c = D.customers(seed=seed, n=n_customers)
    dup = c.sample(n_dup, random_state=seed).copy()
    dup["signup_date"] = dup["signup_date"] + pd.Timedelta(days=200)
    dup["segment"] = dup["segment"].map({"Consumer": "Corporate", "Corporate": "Small Business", "Small Business": "Consumer"})
    c = pd.concat([dup, c]).sample(frac=1, random_state=seed).reset_index(drop=True)
    return {"orders": D.orders(seed=seed, n=n, n_customers=n_customers), "customers": c}

EXAMPLE = lambda: make(0, 8, 5, 2)
""",
    tests="""
TESTS = [
    lambda: make(1, 80, 30, 6),
    lambda: make(2, 3000, 300, 50),
    Test(lambda: make(3, 10, 5, 0), "no duplicates"),
]
""",
    hint1="Deduplicate the right table first (`sort_values` + `drop_duplicates(keep='last')`), then `merge(..., how='left', validate='many_to_one')`.",
    hint2="latest = customers.sort_values('signup_date').drop_duplicates('customer_id', keep='last')\norders.merge(latest[['customer_id', 'segment']], on='customer_id', how='left', validate='many_to_one')",
    solution="""
def solve(orders, customers):
    latest = customers.sort_values("signup_date").drop_duplicates("customer_id", keep="last")
    return orders.merge(latest[["customer_id", "segment"]], on="customer_id", how="left",
                        validate="many_to_one")
""",
    explanation="""
A merge against a key with duplicates silently **multiplies** rows (an order matching two customer rows appears twice), so sums and counts inflate. `validate='many_to_one'` turns that silent bug into an immediate `MergeError`. Always compare `len()` before and after a join.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.merge.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.drop_duplicates.html"],
    wrong_solutions=[
        dict(code="def solve(orders, customers):\n    return orders.merge(customers[['customer_id', 'segment']], on='customer_id', how='left')", why="duplicate keys multiply rows"),
        dict(code="def solve(orders, customers):\n    first = customers.sort_values('signup_date').drop_duplicates('customer_id')\n    return orders.merge(first[['customer_id', 'segment']], on='customer_id', how='left')", why="keeps the oldest registration"),
    ],
),
dict(
    id="pd-050",
    title="Stack monthly extracts",
    difficulty="Easy",
    tags=["joining"],
    signature="def solve(frames: dict) -> pd.DataFrame:",
    statement="""
`frames` maps a month label (`'2024-01'`, `'2024-02'`, ...) to that month's orders DataFrame (all with the same columns). Combine them into one DataFrame whose **first** column is `month` (the label), followed by the original columns, with a fresh `0..n-1` index. Keep the dict's order.
""",
    setup="""
def make(seed, months, n):
    o = D.orders(seed=seed, n=n)
    key = o["order_date"].dt.strftime("%Y-%m")
    return {"frames": {m: o[key == m].reset_index(drop=True) for m in months}}

EXAMPLE = lambda: make(0, ["2024-01", "2024-02"], 12)
""",
    tests="""
TESTS = [
    lambda: make(1, ["2024-03", "2024-04", "2024-05"], 80),
    lambda: make(2, [f"2024-{m:02d}" for m in range(12, 0, -1)], 2000),
    Test(lambda: make(3, ["2024-06"], 30), "one month"),
]
""",
    hint1="`pd.concat(dict_of_frames, names=[...])` uses the dict keys as an outer index level; turn it into a column with `reset_index`.",
    hint2="pd.concat(frames, names=['month', 'row']).reset_index('month').reset_index(drop=True)",
    solution="""
def solve(frames):
    return pd.concat(frames, names=["month", "row"]).reset_index("month").reset_index(drop=True)
""",
    explanation="""
Passing a dict (or `keys=`) to `concat` records where each row came from, a provenance column for free. `ignore_index=True` alone would lose it. Concatenate once at the end rather than inside a loop: repeated `concat` is quadratic.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.concat.html"],
    wrong_solutions=[
        dict(code="def solve(frames):\n    return pd.concat(frames.values(), ignore_index=True)", why="month lost"),
        dict(code="def solve(frames):\n    return pd.concat([df.assign(month=m) for m, df in frames.items()], ignore_index=True)", why="month is the last column"),
    ],
),
dict(
    id="pd-051",
    title="Attach the latest quote to each trade",
    difficulty="Hard",
    tags=["joining", "time series"],
    signature="def solve(trades: pd.DataFrame, quotes: pd.DataFrame) -> pd.DataFrame:",
    statement="""
`trades` (`time, ticker, qty`) and `quotes` (`time, ticker, bid, ask`) are each sorted by `time`. For every trade, attach the `bid` and `ask` of the most recent quote **for the same ticker** at or before the trade time, but only if that quote is at most **2 seconds** old (otherwise NaN).

Return the trades' columns plus `bid`, `ask`, in trade order, with a default index.
""",
    setup="""
def make(seed, n_trades, n_quotes, tickers=("AAA", "BBB", "CCC")):
    rng = np.random.default_rng(seed)
    t0 = pd.Timestamp("2024-05-02 09:30:00")
    qt = t0 + pd.to_timedelta(np.sort(rng.uniform(0, 300, n_quotes)), unit="s")
    mid = rng.uniform(50, 150, len(tickers))
    qtk = rng.choice(list(tickers), n_quotes)
    m = np.array([mid[list(tickers).index(t)] for t in qtk]) + rng.normal(0, 0.2, n_quotes)
    quotes = pd.DataFrame({"time": qt, "ticker": qtk, "bid": np.round(m - 0.01, 2), "ask": np.round(m + 0.01, 2)})
    tt = t0 + pd.to_timedelta(np.sort(rng.uniform(0, 310, n_trades)), unit="s")
    trades = pd.DataFrame({"time": tt, "ticker": rng.choice(list(tickers), n_trades), "qty": rng.integers(1, 10, n_trades) * 100})
    return {"trades": trades, "quotes": quotes}

EXAMPLE = lambda: make(0, 6, 15)
""",
    tests="""
TESTS = [
    lambda: make(1, 40, 120),
    lambda: make(2, 2000, 3000),
    Test(lambda: make(3, 20, 6), "sparse quotes: many stale"),
]
""",
    hint1="`pd.merge_asof(left, right, on='time', by='ticker', tolerance=pd.Timedelta('2s'))` (direction='backward' is the default).",
    hint2="pd.merge_asof(trades, quotes, on='time', by='ticker', tolerance=pd.Timedelta('2s'))",
    solution="""
def solve(trades, quotes):
    return pd.merge_asof(trades, quotes, on="time", by="ticker", tolerance=pd.Timedelta("2s"))
""",
    explanation="""
`merge_asof` is a nearest-key join for time series: for each left row it takes the last right row with key <= the left key (`direction='backward'`), which is exactly "the information available at that time". `by=` matches within each ticker, and `tolerance` stops stale values from being carried forward forever. Both inputs must be sorted on `on`.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.merge_asof.html"],
    wrong_solutions=[
        dict(code="def solve(trades, quotes):\n    return pd.merge_asof(trades, quotes.drop(columns='ticker'), on='time', tolerance=pd.Timedelta('2s'))", why="ignores the ticker"),
        dict(code="def solve(trades, quotes):\n    return pd.merge_asof(trades, quotes, on='time', by='ticker')", why="no staleness limit"),
        dict(code="def solve(trades, quotes):\n    return pd.merge_asof(trades, quotes, on='time', by='ticker', tolerance=pd.Timedelta('2s'), direction='nearest')", why="may use a future quote"),
    ],
),
# ------------------------------------------------------------------ time series
dict(
    id="pd-052",
    title="Daily change and return",
    difficulty="Easy",
    tags=["time series"],
    signature="def solve(close: pd.Series) -> pd.DataFrame:",
    statement="""
`close` is a daily closing-price series indexed by date. Return a DataFrame with the same index and columns:

* `change`: today's close minus yesterday's;
* `ret`: the simple return versus yesterday.

The first day is NaN in both.
""",
    setup="""
def make(seed, n):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2024-01-01", periods=n, name="date")
    return {"close": pd.Series(np.round(100 * np.cumprod(1 + rng.normal(0, 0.01, n)), 2), index=idx, name="close")}

EXAMPLE = lambda: make(0, 5)
""",
    tests="""
TESTS = [
    lambda: make(1, 30),
    lambda: make(2, 1000),
    Test(lambda: make(3, 1), "single day"),
]
""",
    hint1="`Series.diff()` and `Series.pct_change()` (both compare with the previous row; `shift(1)` is the building block).",
    hint2="pd.DataFrame({'change': close.diff(), 'ret': close.pct_change()})",
    solution="""
def solve(close):
    return pd.DataFrame({"change": close.diff(), "ret": close.pct_change()})
""",
    explanation="""
`diff()` is `x - x.shift(1)` and `pct_change()` is `x / x.shift(1) - 1`. Positive shifts look back, so no lookahead. In pandas 2.1+, `pct_change` no longer forward-fills NaN by default (`fill_method=None`), so gaps give NaN returns instead of a fake 0.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.Series.pct_change.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.Series.diff.html"],
    wrong_solutions=[
        dict(code="def solve(close):\n    return pd.DataFrame({'change': close.diff(), 'ret': close.diff() / close})", why="divides by today's price"),
        dict(code="def solve(close):\n    return pd.DataFrame({'change': close.diff(-1), 'ret': close.pct_change(-1)})", why="compares with tomorrow"),
    ],
),
dict(
    id="pd-053",
    title="Per-ticker returns in a long panel",
    difficulty="Medium",
    tags=["time series", "group-wise ops"],
    signature="def solve(prices: pd.DataFrame) -> pd.Series:",
    statement="""
`prices` is a long daily panel (`date, ticker, close, volume`) sorted by (`date`, `ticker`). Return each row's daily simple return computed **within its own ticker** (each ticker's first date is NaN), as a Series aligned to `prices`' index.
""",
    setup="""
EXAMPLE = lambda: {"prices": D.prices(seed=0, n_days=4, n_tickers=3)}
""",
    tests="""
TESTS = [
    lambda: {"prices": D.prices(seed=1, n_days=40, n_tickers=5)},
    lambda: {"prices": D.prices(seed=2, n_days=500, n_tickers=20)},
    Test(lambda: {"prices": D.prices(seed=3, n_days=1, n_tickers=4)}, "one date"),
]
""",
    hint1="`groupby('ticker')['close'].pct_change()` restarts at every ticker and keeps the original index.",
    hint2="prices.groupby('ticker')['close'].pct_change()",
    solution="""
def solve(prices):
    return prices.groupby("ticker")["close"].pct_change()
""",
    explanation="""
In a long panel, consecutive rows belong to **different** tickers, so a plain `pct_change()` divides ALFA by BRVO. Grouped `shift`/`diff`/`pct_change` operate within each ticker and return values aligned to the original rows. The rows within each ticker must be in date order.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.api.typing.DataFrameGroupBy.pct_change.html"],
    wrong_solutions=[
        dict(code="def solve(prices):\n    return prices['close'].pct_change()", why="mixes tickers"),
        dict(code="def solve(prices):\n    return prices.sort_values(['ticker', 'date']).groupby('ticker')['close'].pct_change()", why="reordered rows"),
    ],
),
dict(
    id="pd-054",
    title="7-day rolling average with missing days",
    difficulty="Medium",
    tags=["window functions", "time series"],
    signature="def solve(daily: pd.Series) -> pd.Series:",
    statement="""
`daily` holds daily sales indexed by date, but days without sales have **no row at all**. Return, for each row, the mean of the sales within the trailing **7 calendar days** (the window ending at and including the row's date). Same index.
""",
    setup="""
def make(seed, n, keep=0.7):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-02-01", periods=n, freq="D", name="date")
    s = pd.Series(np.round(rng.gamma(4, 50, n), 2), index=idx, name="sales")
    return {"daily": s[rng.random(n) < keep]}

EXAMPLE = lambda: make(0, 12)
""",
    tests="""
TESTS = [
    lambda: make(1, 40),
    lambda: make(2, 1000, keep=0.5),
    Test(lambda: make(3, 10, keep=1.0), "no missing day"),
]
""",
    hint1="A time-based window: `s.rolling('7D').mean()` (requires a sorted DatetimeIndex).",
    hint2="daily.rolling('7D').mean()",
    solution="""
def solve(daily):
    return daily.rolling("7D").mean()
""",
    explanation="""
`rolling(7)` means 7 **rows**; with missing days those span more than a week. `rolling('7D')` means 7 **days** of index time, closed on the right, and needs no warm-up period (`min_periods` defaults to 1 for offset windows). Alternatively, reindex to a full calendar first (`asfreq('D')`).
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.Series.rolling.html",
          "https://pandas.pydata.org/docs/user_guide/window.html#rolling-window"],
    wrong_solutions=[
        dict(code="def solve(daily):\n    return daily.rolling(7).mean()", why="7 rows, not 7 days"),
        dict(code="def solve(daily):\n    return daily.rolling(7, min_periods=1).mean()", why="7 rows"),
    ],
),
dict(
    id="pd-055",
    title="All-time high to date",
    difficulty="Easy",
    tags=["window functions"],
    signature="def solve(close: pd.Series) -> pd.DataFrame:",
    statement="""
Return a DataFrame with the same index as `close` and columns:

* `ath`: the highest close **up to and including** each day;
* `below_ath`: `close / ath - 1` (0 on a new high, negative below it).
""",
    setup="""
def make(seed, n):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2023-01-02", periods=n, name="date")
    return {"close": pd.Series(np.round(100 * np.cumprod(1 + rng.normal(0.0003, 0.015, n)), 2), index=idx, name="close")}

EXAMPLE = lambda: make(0, 8)
""",
    tests="""
TESTS = [
    lambda: make(1, 60),
    lambda: make(2, 2500),
    Test(lambda: make(3, 1), "single day"),
]
""",
    hint1="A running maximum: `s.cummax()` (same as `s.expanding().max()`).",
    hint2="ath = close.cummax()\npd.DataFrame({'ath': ath, 'below_ath': close / ath - 1})",
    solution="""
def solve(close):
    ath = close.cummax()
    return pd.DataFrame({"ath": ath, "below_ath": close / ath - 1})
""",
    explanation="""
Expanding windows grow from the start: `cummax`, `cummin`, `cumsum` and `expanding().mean()` only use the past, so they are safe as features. `close.max()` is the max over the whole history, future included: lookahead. `below_ath.min()` is the maximum drawdown.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.Series.cummax.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.Series.expanding.html"],
    wrong_solutions=[
        dict(code="def solve(close):\n    ath = pd.Series(close.max(), index=close.index)\n    return pd.DataFrame({'ath': ath, 'below_ath': close / ath - 1})", why="uses the future maximum"),
        dict(code="def solve(close):\n    ath = close.rolling(20, min_periods=1).max()\n    return pd.DataFrame({'ath': ath, 'below_ath': close / ath - 1})", why="20-day high"),
    ],
),
dict(
    id="pd-056",
    title="Exponentially weighted average",
    difficulty="Medium",
    tags=["window functions"],
    signature="def solve(s: pd.Series, span: int) -> pd.Series:",
    statement="""
Return the exponentially weighted moving average of `s` with the given `span` (pandas' default adjusted weights). Missing values are skipped: they don't reset the average, and every row from the first non-missing value onward gets a value.
""",
    setup="""
def make(seed, n, span, nan=0.1):
    rng = np.random.default_rng(seed)
    v = np.round(np.cumsum(rng.normal(0, 1, n)), 3)
    v[rng.random(n) < nan] = np.nan
    return {"s": pd.Series(v, index=pd.bdate_range("2024-01-01", periods=n), name="x"), "span": span}

EXAMPLE = lambda: make(0, 8, 3)
""",
    tests="""
TESTS = [
    lambda: make(1, 50, 10),
    lambda: make(2, 2000, 60, nan=0.2),
    Test(lambda: make(3, 1, 5, nan=0.0), "single value"),
]
""",
    hint1="`s.ewm(span=span).mean()`; `span` relates to the smoothing factor by `alpha = 2 / (span + 1)`.",
    hint2="s.ewm(span=span).mean()",
    solution="""
def solve(s, span):
    return s.ewm(span=span).mean()
""",
    explanation="""
`ewm` weights recent observations more, with weights decaying geometrically. It is specified by exactly one of `span`, `com`, `halflife` or `alpha`. `adjust=True` (the default) normalizes the weights over the observed history, which matters at the start of the series; `adjust=False` is the recursive `y_t = (1 - a) y_{t-1} + a x_t`.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.Series.ewm.html"],
    wrong_solutions=[
        dict(code="def solve(s, span):\n    return s.ewm(alpha=1 / span).mean()", why="wrong smoothing factor"),
        dict(code="def solve(s, span):\n    return s.rolling(span, min_periods=1).mean()", why="simple moving average"),
    ],
),
dict(
    id="pd-057",
    title="Hourly min, mean and max of a sensor",
    difficulty="Medium",
    tags=["time series"],
    signature="def solve(s: pd.Series) -> pd.DataFrame:",
    statement="""
`s` is one sensor's temperature with an irregular `DatetimeIndex` (readings every ~15 minutes, some missing). Return a DataFrame with one row per **hour** (labelled by the start of the hour, every hour from the first to the last reading, empty hours as NaN) and columns `min`, `mean`, `max`.
""",
    setup="""
def make(seed, days, drop=0.1):
    r = D.sensors(seed=seed, n_sensors=1, days=days, drop_share=drop)
    return {"s": r.set_index("timestamp")["temperature"]}

EXAMPLE = lambda: {"s": make(0, 1)["s"].iloc[:14]}
""",
    tests="""
TESTS = [
    lambda: make(1, 1),
    Test(lambda: make(2, 7, drop=0.5), "many gaps"),
    Test(lambda: {"s": make(3, 1)["s"].iloc[:2]}, "two readings"),
]
""",
    hint1="`s.resample('h').agg(['min', 'mean', 'max'])` (use lower-case `'h'`; `'H'` is deprecated).",
    hint2="s.resample('h').agg(['min', 'mean', 'max'])",
    solution="""
def solve(s):
    return s.resample("h").agg(["min", "mean", "max"])
""",
    explanation="""
`resample` is a groupby on time buckets: labels are bucket starts by default, and empty buckets appear (NaN) so the result has a regular frequency. pandas 2.2 renamed several aliases (`'h'`, `'min'`, `'s'`, `'ME'`, `'QE'`, `'YE'`); the old upper-case ones raise deprecation warnings.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.Series.resample.html",
          "https://pandas.pydata.org/docs/user_guide/timeseries.html#offset-aliases"],
    wrong_solutions=[
        dict(code="def solve(s):\n    return s.groupby(s.index.hour).agg(['min', 'mean', 'max'])", why="hour of day, all days mixed"),
        dict(code="def solve(s):\n    return s.resample('h').agg(['min', 'mean', 'max']).dropna()", why="empty hours dropped"),
    ],
),
dict(
    id="pd-058",
    title="Fill in missing days with zero",
    difficulty="Easy",
    tags=["time series"],
    signature="def solve(sales: pd.Series) -> pd.Series:",
    statement="""
`sales` holds daily sales indexed by date, but days without sales are simply absent. Return a series covering **every calendar day** from the first to the last date, with the missing days filled with `0.0`.
""",
    setup="""
def make(seed, n, keep=0.6):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-03-01", periods=n, freq="D", name="date")
    s = pd.Series(np.round(rng.gamma(3, 40, n), 2), index=idx, name="sales")
    mask = rng.random(n) < keep
    mask[0] = mask[-1] = True
    return {"sales": s[mask]}

EXAMPLE = lambda: make(0, 8)
""",
    tests="""
TESTS = [
    lambda: make(1, 40),
    lambda: make(2, 1500, keep=0.3),
    Test(lambda: make(3, 1), "single day"),
]
""",
    hint1="`s.asfreq('D', fill_value=0.0)`, or `s.reindex(pd.date_range(start, end, freq='D'), fill_value=0.0)`.",
    hint2="sales.asfreq('D', fill_value=0.0)",
    solution="""
def solve(sales):
    return sales.asfreq("D", fill_value=0.0)
""",
    explanation="""
Missing rows are invisible to `rolling`, `shift` and `diff` (yesterday becomes "the previous row"), so regularize the index first. `asfreq` / `reindex(date_range(...))` insert the absent dates; whether to fill with 0, carry forward (`ffill`) or leave NaN depends on what absence means. For sales, no row means zero.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.Series.asfreq.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.date_range.html"],
    wrong_solutions=[
        dict(code="def solve(sales):\n    return sales.asfreq('D').ffill()", why="carries yesterday's sales forward"),
        dict(code="def solve(sales):\n    return sales.asfreq('D')", why="NaN, not zero"),
    ],
),
dict(
    id="pd-059",
    title="20-day rolling volatility per ticker",
    difficulty="Hard",
    tags=["window functions", "group-wise ops"],
    signature="def solve(prices: pd.DataFrame) -> pd.Series:",
    statement="""
`prices` is a long daily panel (`date, ticker, close, volume`) sorted by (`date`, `ticker`). For each ticker, compute the daily simple return, then the rolling **20-day standard deviation** of those returns (a full window of 20 returns is required, so each ticker's first 20 dates are NaN). Return a Series aligned to `prices`' index (same row order).
""",
    setup="""
EXAMPLE = lambda: {"prices": D.prices(seed=0, n_days=25, n_tickers=2)}
""",
    tests="""
TESTS = [
    lambda: {"prices": D.prices(seed=1, n_days=60, n_tickers=4)},
    lambda: {"prices": D.prices(seed=2, n_days=500, n_tickers=20)},
    Test(lambda: {"prices": D.prices(seed=3, n_days=15, n_tickers=3)}, "shorter than the window"),
]
""",
    hint1="Group twice: returns with `groupby('ticker')['close'].pct_change()`, then `ret.groupby(prices['ticker']).transform(lambda r: r.rolling(20).std())` (or `.rolling(20).std()` + `droplevel` + `sort_index`).",
    hint2="ret = prices.groupby('ticker')['close'].pct_change()\nret.groupby(prices['ticker']).transform(lambda r: r.rolling(20).std())",
    solution="""
def solve(prices):
    ret = prices.groupby("ticker")["close"].pct_change()
    return ret.groupby(prices["ticker"]).transform(lambda r: r.rolling(20).std())
""",
    explanation="""
Every window must stay inside one ticker. `groupby(...).rolling(20).std()` returns a (ticker, original index) MultiIndex in **group order**, so you need `.droplevel(0).sort_index()` to align it back. `transform` keeps the original order directly. Annualize with `* np.sqrt(252)` when needed.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.api.typing.DataFrameGroupBy.rolling.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.api.typing.SeriesGroupBy.transform.html"],
    wrong_solutions=[
        dict(code="def solve(prices):\n    ret = prices.groupby('ticker')['close'].pct_change()\n    return ret.rolling(20).std()", why="windows span several tickers"),
        dict(code="def solve(prices):\n    ret = prices.groupby('ticker')['close'].pct_change()\n    return ret.groupby(prices['ticker']).rolling(20).std().droplevel(0)", why="group order, not row order"),
    ],
),
# ------------------------------------------------------------------ misc
dict(
    id="pd-060",
    title="Count posts per tag",
    difficulty="Hard",
    tags=["reshaping", "strings"],
    signature="def solve(posts: pd.DataFrame) -> pd.Series:",
    statement="""
`posts` has a column `tags` with comma-separated tags such as `'python, pandas,ml'` (spaces optional); posts without tags have an empty string or NaN. Return the number of posts per tag as a Series indexed by tag, sorted by count descending and then by tag A to Z.
""",
    setup="""
TAGS = ["python", "pandas", "ml", "sql", "stats", "viz"]

def make(seed, n):
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n):
        k = int(rng.integers(0, 4))
        t = rng.choice(TAGS, k, replace=False)
        sep = ", " if rng.random() < 0.5 else ","
        rows.append(sep.join(t) if k else (np.nan if rng.random() < 0.5 else ""))
    return {"posts": pd.DataFrame({"post_id": range(1, n + 1), "tags": rows})}

EXAMPLE = lambda: {"posts": pd.DataFrame({"post_id": [1, 2, 3, 4], "tags": ["python, pandas", "ml,python", "", np.nan]})}
""",
    tests="""
TESTS = [
    lambda: make(1, 20),
    lambda: make(2, 2000),
    Test(lambda: {"posts": pd.DataFrame({"post_id": [1], "tags": ["sql"]})}, "one post"),
]
""",
    hint1="`str.split(',')` gives lists; `explode()` puts one element per row; then `str.strip()`, drop empties and `value_counts()`.",
    hint2="tags = posts['tags'].str.split(',').explode().str.strip()\ntags[tags.fillna('') != ''].value_counts()",
    solution="""
def solve(posts):
    tags = posts["tags"].str.split(",").explode().str.strip()
    counts = tags[tags.fillna("") != ""].value_counts()
    return counts.sort_index().sort_values(ascending=False, kind="stable")
""",
    explanation="""
`explode` turns each list element into its own row, repeating the original index, which is the standard way to handle multi-valued cells. Normalize (strip, lower) **after** exploding. Sorting by label first and then by count with a stable sort gives a deterministic tie order.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.Series.explode.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.Series.str.split.html"],
    wrong_solutions=[
        dict(code="def solve(posts):\n    tags = posts['tags'].str.split(',').explode()\n    counts = tags[tags.fillna('') != ''].value_counts()\n    return counts.sort_index().sort_values(ascending=False, kind='stable')", why="spaces not stripped"),
        dict(code="def solve(posts):\n    tags = posts['tags'].str.split(',').explode().str.strip()\n    return tags.value_counts().sort_index().sort_values(ascending=False, kind='stable')", why="empty string counted as a tag"),
    ],
),
dict(
    id="pd-061",
    title="Top category per region",
    difficulty="Medium",
    tags=["aggregation"],
    signature="def solve(orders: pd.DataFrame) -> pd.Series:",
    statement="""
Return, for each region (index, sorted A to Z), the **category** with the highest total revenue in that region.
""",
    setup="""
EXAMPLE = lambda: {"orders": D.orders(seed=0, n=25)}
""",
    tests="""
TESTS = [
    lambda: {"orders": D.orders(seed=1, n=200)},
    lambda: {"orders": D.orders(seed=2, n=5000)},
    Test(lambda: {"orders": D.orders(seed=3, n=3)}, "few orders"),
    Test(lambda: {"orders": pd.DataFrame({
        "region": ["North"] * 11 + ["South"] * 5,
        "category": ["Books"] * 10 + ["Electronics"] + ["Home"] * 3 + ["Sports"] * 2,
        "revenue": [50.0] * 10 + [300.0] + [100.0] * 3 + [200.0] * 2})}, "many small vs few large orders"),
]
""",
    hint1="Total by (region, category), `unstack()` to a grid, then `idxmax(axis=1)` returns the column label of each row's maximum.",
    hint2="orders.groupby(['region', 'category'])['revenue'].sum().unstack().idxmax(axis=1)",
    solution="""
def solve(orders):
    return orders.groupby(["region", "category"])["revenue"].sum().unstack().idxmax(axis=1)
""",
    explanation="""
`idxmax` returns the **label** of the maximum (`max` returns the value). On the unstacked grid, `axis=1` scans across categories. Equivalent long form: `s.groupby(level='region').idxmax()` returns (region, category) tuples. Since pandas 3, `idxmax` raises on all-NaN rows instead of returning NaN.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.idxmax.html"],
    wrong_solutions=[
        dict(code="def solve(orders):\n    return orders.groupby(['region', 'category'])['revenue'].count().unstack().idxmax(axis=1)", why="most orders, not most revenue"),
        dict(code="def solve(orders):\n    return orders.groupby(['region', 'category'])['revenue'].mean().unstack().idxmax(axis=1)", why="highest average order"),
    ],
),
dict(
    id="pd-062",
    title="One-hot encode categorical columns",
    difficulty="Easy",
    tags=["feature engineering"],
    signature="def solve(df: pd.DataFrame) -> pd.DataFrame:",
    statement="""
Replace the categorical columns `contract` and `internet` of `df` with 0/1 **integer** indicator columns, dropping the first level of each (to avoid perfect collinearity). The other columns stay first, in their original order; the indicators are named `<column>_<level>`. Dtypes are checked.
""",
    setup="""
def make(seed, n):
    return {"df": D.churn(seed=seed, n=n)[["tenure", "contract", "internet", "monthly_charges"]]}

EXAMPLE = lambda: make(0, 6)
""",
    tests="""
TESTS = [
    lambda: make(1, 50),
    lambda: make(2, 2000),
    Test(lambda: make(3, 12), "small"),
]
""",
    compare=dict(check_dtype=True),
    hint1="`pd.get_dummies(df, columns=[...], drop_first=True, dtype=int)`.",
    hint2="pd.get_dummies(df, columns=['contract', 'internet'], drop_first=True, dtype=int)",
    solution="""
def solve(df):
    return pd.get_dummies(df, columns=["contract", "internet"], drop_first=True, dtype=int)
""",
    explanation="""
`get_dummies` returns **bool** columns by default since pandas 2.0; pass `dtype=int` for 0/1. It's fine for quick analysis, but in a model use `OneHotEncoder`: `get_dummies` creates columns from whatever levels the data happens to contain, so train and test can end up with different columns.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.get_dummies.html"],
    wrong_solutions=[
        dict(code="def solve(df):\n    return pd.get_dummies(df, columns=['contract', 'internet'], drop_first=True)", why="bool dtype"),
        dict(code="def solve(df):\n    return pd.get_dummies(df, columns=['contract', 'internet'], dtype=int)", why="first level kept"),
    ],
),
dict(
    id="pd-063",
    title="Remove z-score outliers",
    difficulty="Medium",
    tags=["outliers"],
    signature="def solve(df: pd.DataFrame) -> pd.DataFrame:",
    statement="""
Drop every row where **any** numeric column has an absolute z-score above 3, where z uses the column mean and the sample standard deviation (`ddof=1`). Non-numeric columns are kept as they are; keep the original index. There are no missing values.
""",
    setup="""
def make(seed, n, n_out=3):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({"id": [f"r{i}" for i in range(n)], "a": rng.normal(10, 2, n), "b": rng.normal(-5, 1, n),
                       "c": rng.exponential(3, n)})
    idx = rng.choice(n, min(n_out, n), replace=False)
    df.loc[idx, "a"] = df.loc[idx, "a"] + rng.choice([-1, 1], len(idx)) * 12
    return {"df": df}

def borderline(seed, n=50):
    rng = np.random.default_rng(seed)
    a = rng.normal(0, 1, n)
    def z1(v):
        x = a.copy()
        x[0] = v
        return (x[0] - x.mean()) / x.std(ddof=1)
    lo, hi = 0.0, 50.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if z1(mid) < 2.99 else (lo, mid)
    a[0] = lo
    return {"df": pd.DataFrame({"id": [f"r{i}" for i in range(n)], "a": a, "b": rng.normal(0, 1, n).clip(-2, 2)})}

EXAMPLE = lambda: make(0, 30, 2)
""",
    tests="""
TESTS = [
    lambda: make(1, 100, 4),
    lambda: make(2, 5000, 30),
    Test(lambda: make(3, 200, 0), "no planted outliers"),
    Test(lambda: borderline(4), "z just below 3 with ddof=1"),
]
""",
    hint1="`num = df.select_dtypes('number')`; `z = (num - num.mean()) / num.std()`; keep rows where `(z.abs() <= 3).all(axis=1)`.",
    hint2="num = df.select_dtypes('number')\nz = (num - num.mean()) / num.std()\ndf[(z.abs() <= 3).all(axis=1)]",
    solution="""
def solve(df):
    num = df.select_dtypes("number")
    z = (num - num.mean()) / num.std()
    return df[(z.abs() <= 3).all(axis=1)]
""",
    explanation="""
pandas' `std()` uses `ddof=1` (sample) while NumPy's `np.std` defaults to `ddof=0`: a classic discrepancy. Z-scores assume roughly normal data and are themselves distorted by the outliers; the IQR rule or a median/MAD z-score is more robust for skewed columns (see column `c`).
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.std.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.select_dtypes.html"],
    wrong_solutions=[
        dict(code="def solve(df):\n    num = df.select_dtypes('number')\n    z = (num - num.mean()) / num.std()\n    return df[(z.abs() <= 3).any(axis=1)]", why="any instead of all"),
        dict(code="def solve(df):\n    num = df.select_dtypes('number')\n    z = (num - num.mean()) / num.std(ddof=0)\n    return df[(z.abs() <= 3).all(axis=1)]", why="population std"),
    ],
),
dict(
    id="pd-064",
    title="IQR outliers within each department",
    difficulty="Hard",
    tags=["outliers", "group-wise ops"],
    signature="def solve(hr: pd.DataFrame) -> pd.DataFrame:",
    statement="""
Flag salary outliers **within each department** with the 1.5 x IQR rule: a salary is an outlier if it lies below `Q1 - 1.5 * IQR` or above `Q3 + 1.5 * IQR`, with Q1, Q3 and IQR computed per department (pandas' default linear interpolation).

Return the rows of `hr` that are **not** outliers; rows with a missing salary are dropped too. Keep the original index.
""",
    setup="""
def make(seed, n, n_out=4):
    hr = D.hr(seed=seed, n=n)
    rng = np.random.default_rng(seed)
    idx = rng.choice(n, min(n_out, n), replace=False)
    hr.loc[idx, "salary"] = hr.loc[idx, "salary"] * rng.choice([0.3, 3.0], len(idx))
    return {"hr": hr}

EXAMPLE = lambda: make(0, 25, 2)
""",
    tests="""
TESTS = [
    lambda: make(1, 120, 6),
    lambda: make(2, 3000, 40),
    Test(lambda: make(3, 10, 0), "small"),
]
""",
    hint1="Per-row group quantiles with `groupby('department')['salary'].transform('quantile', 0.25)` (and 0.75), then `Series.between(lo, hi)`.",
    hint2="g = hr.groupby('department')['salary']\nq1, q3 = g.transform('quantile', 0.25), g.transform('quantile', 0.75)\nhr[hr['salary'].between(q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1))]",
    solution="""
def solve(hr):
    g = hr.groupby("department")["salary"]
    q1, q3 = g.transform("quantile", 0.25), g.transform("quantile", 0.75)
    iqr = q3 - q1
    return hr[hr["salary"].between(q1 - 1.5 * iqr, q3 + 1.5 * iqr)]
""",
    explanation="""
Outliers are relative to their group: a 120k salary is normal in Engineering and extreme in HR, so compute fences per department with `transform`. `between` with NaN returns False, which drops missing salaries. Decide that consciously, or handle them separately.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.api.typing.SeriesGroupBy.transform.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.Series.quantile.html"],
    wrong_solutions=[
        dict(code="""
def solve(hr):
    q1, q3 = hr["salary"].quantile(0.25), hr["salary"].quantile(0.75)
    iqr = q3 - q1
    return hr[hr["salary"].between(q1 - 1.5 * iqr, q3 + 1.5 * iqr)]
""", why="company-wide fences"),
        dict(code="""
def solve(hr):
    g = hr.groupby("department")["salary"]
    q1, q3 = g.transform("quantile", 0.25), g.transform("quantile", 0.75)
    iqr = q3 - q1
    return hr[hr["salary"].between(q1 - 3 * iqr, q3 + 3 * iqr)]
""", why="3 x IQR"),
    ],
),
dict(
    id="pd-065",
    title="Reusable cleaning step in a chain",
    difficulty="Medium",
    tags=["method chaining", "strings"],
    signature="def solve(raw: pd.DataFrame) -> pd.DataFrame:",
    statement="""
Clean the orders export `raw` in **one method chain**: drop exact duplicate rows, apply the same text normalization (strip surrounding whitespace, then Title-case) to both `region` and `category` through a small helper function of your own, and reset the index to `0..n-1`. Columns keep their order.
""",
    setup="""
def make(seed, n):
    raw = D.orders_raw(seed=seed, n=n)
    rng = np.random.default_rng(seed)
    cat = raw["category"].to_numpy().astype(object)
    k = rng.random(len(cat)) < 0.2
    cat[k] = [c.upper() if rng.random() < 0.5 else " " + c.lower() for c in cat[k]]
    return {"raw": raw.assign(category=cat.astype(str))}

EXAMPLE = lambda: make(0, 10)
""",
    tests="""
TESTS = [
    lambda: make(1, 80),
    lambda: make(2, 2000),
    Test(lambda: make(3, 2), "tiny"),
]
""",
    hint1="Write `def tidy(df, cols): return df.assign(**{c: ... for c in cols})` and call it inside the chain with `.pipe(tidy, ['region', 'category'])`.",
    hint2="raw.drop_duplicates().pipe(tidy, ['region', 'category']).reset_index(drop=True)",
    solution="""
def tidy(df, cols):
    return df.assign(**{c: df[c].str.strip().str.title() for c in cols})

def solve(raw):
    return raw.drop_duplicates().pipe(tidy, ["region", "category"]).reset_index(drop=True)
""",
    explanation="""
`df.pipe(f, *args)` is `f(df, *args)` written in chain order, so custom steps read top to bottom like built-in methods. Keep helpers pure (return a new frame) so chains stay re-runnable. Here dropping duplicates **before** normalizing matters: `' north'` and `'North'` rows aren't exact duplicates yet.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.pipe.html"],
    wrong_solutions=[
        dict(code="""
def tidy(df, cols):
    return df.assign(**{c: df[c].str.strip().str.title() for c in cols})

def solve(raw):
    return raw.pipe(tidy, ["region", "category"]).drop_duplicates().reset_index(drop=True)
""", why="normalizing first creates extra duplicates"),
        dict(code="""
def tidy(df, cols):
    return df.assign(**{c: df[c].str.title() for c in cols})

def solve(raw):
    return raw.drop_duplicates().pipe(tidy, ["region", "category"]).reset_index(drop=True)
""", why="whitespace kept"),
    ],
),
dict(
    id="pd-066",
    title="Sessionize a clickstream",
    difficulty="Hard",
    tags=["time series", "group-wise ops"],
    signature="def solve(clicks: pd.DataFrame) -> pd.Series:",
    statement="""
`clicks` has columns `user_id` and `ts` (datetime) and is sorted by user, then time. A **session** starts at a user's first click and whenever **more than 30 minutes** have passed since that user's previous click. Return each click's session number, counting from 1 within each user, as an integer Series aligned to `clicks`.
""",
    setup="""
def make(seed, n_users, n):
    rng = np.random.default_rng(seed)
    users = np.sort(rng.integers(1, n_users + 1, n))
    gaps = np.where(rng.random(n) < 0.15, rng.uniform(31, 300, n), rng.uniform(0.1, 29, n))
    ts = pd.Timestamp("2024-07-01 08:00") + pd.to_timedelta(np.cumsum(gaps), unit="min")
    df = pd.DataFrame({"user_id": users, "ts": ts}).sort_values(["user_id", "ts"], ignore_index=True)
    df.loc[1, "ts"] = df.loc[0, "ts"] + pd.Timedelta("30min")
    return {"clicks": df}

EXAMPLE = lambda: {"clicks": pd.DataFrame({"user_id": [1, 1, 1, 2, 2],
    "ts": pd.to_datetime(["2024-07-01 09:00", "2024-07-01 09:20", "2024-07-01 10:05", "2024-07-01 09:10", "2024-07-01 09:40"])})}
""",
    tests="""
TESTS = [
    lambda: make(1, 3, 30),
    lambda: make(2, 200, 5000),
    Test(lambda: make(3, 1, 2), "exactly 30 minutes apart"),
]
""",
    hint1="Per user, `diff()` the timestamps and flag gaps `> pd.Timedelta('30min')`; a grouped `cumsum()` of the flags (+1) numbers the sessions.",
    hint2="new = clicks.groupby('user_id')['ts'].diff() > pd.Timedelta('30min')\nnew.groupby(clicks['user_id']).cumsum() + 1",
    solution="""
def solve(clicks):
    new = clicks.groupby("user_id")["ts"].diff() > pd.Timedelta("30min")
    return new.groupby(clicks["user_id"]).cumsum() + 1
""",
    explanation="""
The "flag the change, then cumsum the flags" pattern turns boundaries into run ids. It is fully vectorized and also builds streak ids (`(s != s.shift()).cumsum()`). Each user's first click has a NaT gap, and `NaT > 30min` is False, so it gets session 1 without special-casing. Both steps must be grouped by user.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.api.typing.DataFrameGroupBy.diff.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.api.typing.DataFrameGroupBy.cumsum.html"],
    wrong_solutions=[
        dict(code="def solve(clicks):\n    new = clicks['ts'].diff() > pd.Timedelta('30min')\n    return new.groupby(clicks['user_id']).cumsum() + 1", why="gaps measured across users"),
        dict(code="def solve(clicks):\n    new = clicks.groupby('user_id')['ts'].diff() >= pd.Timedelta('30min')\n    return new.groupby(clicks['user_id']).cumsum() + 1", why="exactly 30 minutes starts a new session"),
    ],
),
dict(
    id="pd-067",
    title="Summary statistics of the numeric columns",
    difficulty="Easy",
    tags=["EDA"],
    signature="def solve(df: pd.DataFrame) -> pd.DataFrame:",
    statement="""
Return the standard summary statistics of the **numeric** columns of `df` as a table with **one row per numeric column** (in column order) and the columns `count, mean, std, min, 25%, 50%, 75%, max`, rounded to 2 decimals. Missing values are ignored, so `count` is the number of non-missing values.
""",
    setup="""
EXAMPLE = lambda: {"df": D.hr(seed=0, n=30)}
""",
    tests="""
TESTS = [
    lambda: {"df": D.churn(seed=1, n=200)},
    lambda: {"df": D.orders(seed=2, n=3000)},
    Test(lambda: {"df": D.hr(seed=3, n=2)}, "two rows"),
]
""",
    hint1="`df.describe()` summarizes the numeric columns (one column per variable, one row per statistic); transpose it with `.T`.",
    hint2="df.describe().T.round(2)",
    solution="""
def solve(df):
    return df.describe().T.round(2)
""",
    explanation="""
`describe()` is the one-line numeric overview: count (watch for missing values), mean vs median (skew), min/max (impossible values, outliers). Transposing gives one row per variable, which reads better with many columns. `include='all'` adds text columns (count, unique, top, freq); `percentiles=[...]` changes the quantiles.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.describe.html"],
    wrong_solutions=[
        dict(code="def solve(df):\n    return df.describe().round(2)", why="not transposed"),
        dict(code="def solve(df):\n    return df.describe(include='all').T.round(2)", why="text columns included"),
    ],
),
dict(
    id="pd-068",
    title="Rate in force on each business day",
    difficulty="Medium",
    tags=["time series"],
    signature="def solve(rate: pd.Series, dates: pd.DatetimeIndex) -> pd.Series:",
    statement="""
`rate` is a policy interest rate indexed by its **announcement dates** (irregular; some announcements fall on weekends). `dates` are daily business days. For each date in `dates`, return the rate **in force**: the most recent announcement on or before that date (NaN before the first announcement). Return a Series indexed by `dates`.
""",
    setup="""
def make(seed, n_ann, n_days, start="2024-01-01"):
    rng = np.random.default_rng(seed)
    ann = pd.to_datetime(start) + pd.to_timedelta(np.sort(rng.choice(np.arange(5, n_days * 1.4), n_ann, replace=False)).astype(int), unit="D")
    rate = pd.Series(np.round(np.cumsum(rng.choice([-0.25, 0.25, 0.5], n_ann)) + 3, 2), index=ann, name="rate")
    return {"rate": rate, "dates": pd.bdate_range(start, periods=n_days, name="date")}

EXAMPLE = lambda: {"rate": pd.Series([3.0, 3.25, 3.5], index=pd.to_datetime(["2024-01-03", "2024-01-06", "2024-01-10"]), name="rate"),
                   "dates": pd.bdate_range("2024-01-01", periods=9, name="date")}
""",
    tests="""
TESTS = [
    lambda: make(1, 6, 40),
    lambda: make(2, 30, 500),
    Test(lambda: {"rate": pd.Series([4.0], index=pd.to_datetime(["2024-03-09"]), name="rate"),
                  "dates": pd.bdate_range("2024-03-04", periods=8, name="date")}, "single weekend announcement"),
]
""",
    hint1="`s.reindex(new_index, method='ffill')` takes, for each new label, the last value at or before it, even if that exact date isn't in the new index (or use `s.asof(dates)` / `merge_asof`).",
    hint2="rate.reindex(dates, method='ffill')",
    solution="""
def solve(rate, dates):
    return rate.reindex(dates, method="ffill")
""",
    explanation="""
`reindex(dates).ffill()` looks equivalent but first **drops** every announcement whose date isn't in `dates` (the weekend ones), so the rate change shows up late. `method='ffill'` searches the original index instead (it needs to be sorted). This "as of" alignment is how you attach slow-moving data (rates, fundamentals) to a daily calendar without lookahead.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.Series.reindex.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.Series.asof.html"],
    wrong_solutions=[
        dict(code="def solve(rate, dates):\n    return rate.reindex(dates).ffill()", why="weekend announcements dropped"),
        dict(code="def solve(rate, dates):\n    return rate.reindex(dates, method='bfill')", why="uses the next announcement (lookahead)"),
    ],
),
]
