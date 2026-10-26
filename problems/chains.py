SECTION = "chains"

# Each chain step receives the *reference* output of the previous step (via
# REF), so one mistake never blocks the rest of the chain.
CHURN = '''
def raw(seed, n):
    return D.churn(seed=seed, n=n, messy=True)

def xy(seed, n):
    return REF("ch-003", df=REF("ch-002", raw=raw(seed, n)))
'''
SALARY = '''
def clean(seed, n):
    return REF("ch-007", raw=D.hr_raw(seed=seed, n=n))
'''
FACTOR = '''
def returns(seed, n_days, n_tickers):
    return REF("ch-010", prices=D.prices(seed=seed, n_days=n_days, n_tickers=n_tickers))

def labelled(seed, n_days, n_tickers):
    p = D.prices(seed=seed, n_days=n_days, n_tickers=n_tickers)
    return REF("ch-012", prices=p, features=REF("ch-011", R=REF("ch-010", prices=p)))
'''
SEGMENTS = '''
def rfm(seed, n, n_customers):
    return REF("ch-015", orders=D.orders(seed=seed, n=n, n_customers=n_customers))

def scaled(seed, n, n_customers):
    return REF("ch-016", rfm=rfm(seed, n, n_customers))
'''

PROBLEMS = [
# ================================================================== churn (classification)
dict(
    id="ch-001",
    chain="churn", step=1,
    title="Churn 1/5: first look at the raw table",
    difficulty="Easy",
    tags=["inspection"],
    signature="def solve(raw: pd.DataFrame) -> dict:",
    statement="""
You're handed `raw`, a telecom churn export (`customer_id, tenure, contract, internet, payment_method, monthly_charges, total_charges, support_calls, senior, region, churned`). Before modelling, inspect it. Return a dict with:

* `n_rows`: number of rows;
* `n_duplicates`: number of rows that exactly duplicate an **earlier** row;
* `missing`: `{column: count}` of missing values, only for columns that have any (in column order);
* `text_columns`: list of the non-numeric columns, in column order;
* `churn_rate`: mean of `churned`, rounded to 4 decimals.
""",
    setup=CHURN + """
EXAMPLE = lambda: {"raw": raw(0, 20)}
""",
    tests="""
TESTS = [
    lambda: {"raw": raw(1, 200)},
    lambda: {"raw": raw(2, 3000)},
    Test(lambda: {"raw": D.churn(seed=3, n=10)}, "clean table: nothing missing"),
]
""",
    hint1="`df.duplicated().sum()`, `df.isna().sum()` filtered to `> 0`, `df.select_dtypes(exclude='number').columns`.",
    hint2="miss = raw.isna().sum()\n{'n_duplicates': int(raw.duplicated().sum()), 'missing': miss[miss > 0].to_dict(),\n 'text_columns': raw.select_dtypes(exclude='number').columns.tolist()}",
    solution="""
def solve(raw):
    miss = raw.isna().sum()
    return {"n_rows": len(raw), "n_duplicates": int(raw.duplicated().sum()),
            "missing": miss[miss > 0].to_dict(),
            "text_columns": raw.select_dtypes(exclude="number").columns.tolist(),
            "churn_rate": round(float(raw["churned"].mean()), 4)}
""",
    explanation="""
Two red flags show up immediately: duplicates, and `total_charges` listed as text even though it is a number (it contains blanks). `duplicated()` marks repeats of an *earlier* row (`keep='first'`); `keep=False` marks every copy. In an interview, say these findings out loud before you clean anything.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.duplicated.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.select_dtypes.html"],
    wrong_solutions=[
        dict(code="""
def solve(raw):
    miss = raw.isna().sum()
    return {"n_rows": len(raw), "n_duplicates": int(raw.duplicated(keep=False).sum()),
            "missing": miss[miss > 0].to_dict(), "text_columns": raw.select_dtypes(exclude="number").columns.tolist(),
            "churn_rate": round(float(raw["churned"].mean()), 4)}
""", why="counts every copy"),
        dict(code="""
def solve(raw):
    return {"n_rows": len(raw), "n_duplicates": int(raw.duplicated().sum()),
            "missing": raw.isna().sum().to_dict(), "text_columns": raw.select_dtypes(exclude="number").columns.tolist(),
            "churn_rate": round(float(raw["churned"].mean()), 4)}
""", why="lists columns with no missing values"),
    ],
),
dict(
    id="ch-002",
    chain="churn", step=2,
    title="Churn 2/5: clean the raw table",
    difficulty="Medium",
    tags=["cleaning"],
    signature="def solve(raw: pd.DataFrame) -> pd.DataFrame:",
    statement="""
`raw` is the messy churn export: `customer_id, tenure, contract, internet, payment_method, monthly_charges, total_charges, support_calls, senior, region, churned`. Problems you found in step 1:

* some rows are exact duplicates;
* `total_charges` is text, with a blank `" "` for brand-new customers (`tenure == 0`);
* `contract` has spelling variants (`"month-to-month"`, `"Month to month"`, `"1 year"`, `"two year"`, ...) of the three labels `"Month-to-month"`, `"One year"`, `"Two year"`;
* `monthly_charges` has a few NaNs.

Return a cleaned copy with the same columns in the same order:

1. drop exact duplicate rows (keep the first);
2. convert `total_charges` to float, with blanks becoming `0.0`;
3. map every `contract` value to one of the three canonical labels;
4. fill missing `monthly_charges` with the median `monthly_charges` of customers with the same `internet` type (median computed after step 1);
5. reset the index to 0..n-1.
""",
    setup="""
EXAMPLE = lambda: {"raw": D.churn(seed=0, n=20, messy=True)}
""",
    tests="""
TESTS = [
    lambda: {"raw": D.churn(seed=1, n=200, messy=True)},
    lambda: {"raw": D.churn(seed=2, n=1500, messy=True)},
    Test(lambda: {"raw": D.churn(seed=3, n=8, messy=True)}, "tiny table"),
]
""",
    compare=dict(check_dtype=True),
    hint1="`drop_duplicates()`, `pd.to_numeric(..., errors='coerce')`, a mapping on `str.lower()`, and `groupby(...).transform('median')` inside `fillna`.",
    hint2="df['total_charges'] = pd.to_numeric(df['total_charges'], errors='coerce').fillna(0.0)\ndf['monthly_charges'] = df['monthly_charges'].fillna(df.groupby('internet')['monthly_charges'].transform('median'))",
    solution="""
CONTRACT = {"month-to-month": "Month-to-month", "month to month": "Month-to-month",
            "one year": "One year", "1 year": "One year", "two year": "Two year", "2 year": "Two year"}

def solve(raw):
    df = raw.drop_duplicates().reset_index(drop=True)
    df["total_charges"] = pd.to_numeric(df["total_charges"], errors="coerce").fillna(0.0)
    df["contract"] = df["contract"].str.strip().str.lower().map(CONTRACT)
    df["monthly_charges"] = df["monthly_charges"].fillna(
        df.groupby("internet")["monthly_charges"].transform("median"))
    return df
""",
    explanation="""
`to_numeric(errors='coerce')` turns unparseable text (the blanks) into NaN, which you then fill explicitly; `astype(float)` would raise instead. Lower-casing before mapping shrinks the variants to a handful of keys. `transform('median')` gives each row its own group's median, so `fillna` stays one vectorized call.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.to_numeric.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.drop_duplicates.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.api.typing.DataFrameGroupBy.transform.html"],
    wrong_solutions=[
        dict(code="""
CONTRACT = {"month-to-month": "Month-to-month", "month to month": "Month-to-month",
            "one year": "One year", "1 year": "One year", "two year": "Two year", "2 year": "Two year"}

def solve(raw):
    df = raw.drop_duplicates().reset_index(drop=True)
    df["total_charges"] = pd.to_numeric(df["total_charges"], errors="coerce").fillna(0.0)
    df["contract"] = df["contract"].str.strip().str.lower().map(CONTRACT)
    df["monthly_charges"] = df["monthly_charges"].fillna(df["monthly_charges"].median())
    return df
""", why="global median instead of per internet type"),
        dict(code="""
CONTRACT = {"month-to-month": "Month-to-month", "month to month": "Month-to-month",
            "one year": "One year", "1 year": "One year", "two year": "Two year", "2 year": "Two year"}

def solve(raw):
    df = raw.drop_duplicates().reset_index(drop=True)
    df["total_charges"] = pd.to_numeric(df["total_charges"], errors="coerce")
    df["contract"] = df["contract"].str.strip().str.lower().map(CONTRACT)
    df["monthly_charges"] = df["monthly_charges"].fillna(
        df.groupby("internet")["monthly_charges"].transform("median"))
    return df
""", why="blanks left as NaN"),
        dict(code="""
CONTRACT = {"month-to-month": "Month-to-month", "month to month": "Month-to-month",
            "one year": "One year", "1 year": "One year", "two year": "Two year", "2 year": "Two year"}

def solve(raw):
    df = raw.copy()
    df["total_charges"] = pd.to_numeric(df["total_charges"], errors="coerce").fillna(0.0)
    df["contract"] = df["contract"].str.strip().str.lower().map(CONTRACT)
    df["monthly_charges"] = df["monthly_charges"].fillna(
        df.groupby("internet")["monthly_charges"].transform("median"))
    return df.reset_index(drop=True)
""", why="kept duplicates"),
    ],
),
dict(
    id="ch-003",
    chain="churn", step=3,
    title="Churn 3/5: features and target",
    difficulty="Medium",
    tags=["feature engineering"],
    signature="def solve(df: pd.DataFrame) -> tuple:",
    statement="""
`df` is the cleaned churn table from step 2 (the reference output): `customer_id, tenure, contract, internet, payment_method, monthly_charges, total_charges, support_calls, senior, region, churned`.

Build the modelling inputs and return `(X, y)`:

* `y`: the `churned` column (a Series).
* `X`: every column except `customer_id` and `churned`, in their original order, followed by two new columns:
  * `avg_charge`: `total_charges / tenure`, and `monthly_charges` where `tenure == 0` (no division by zero);
  * `tenure_band`: `tenure` binned into the intervals [0, 12), [12, 24), [24, 48), [48, inf) labelled `"0-11"`, `"12-23"`, `"24-47"`, `"48+"`.

Keep the index of `df`.
""",
    setup="""
EXAMPLE = lambda: {"df": REF("ch-002", raw=D.churn(seed=0, n=20, messy=True))}
""",
    tests="""
TESTS = [
    lambda: {"df": REF("ch-002", raw=D.churn(seed=1, n=200, messy=True))},
    lambda: {"df": REF("ch-002", raw=D.churn(seed=2, n=1500, messy=True))},
    Test(lambda: {"df": REF("ch-002", raw=D.churn(seed=5, n=300, messy=True)).query("tenure in (0, 12, 24, 48)")}, "values on the bin edges"),
]
""",
    hint1="`np.where` (or `Series.where`) for the safe division, `pd.cut(..., right=False, labels=[...])` for the bands.",
    hint2="X['avg_charge'] = np.where(X['tenure'] > 0, X['total_charges'] / X['tenure'], X['monthly_charges'])\nX['tenure_band'] = pd.cut(X['tenure'], [0, 12, 24, 48, np.inf], right=False, labels=['0-11', '12-23', '24-47', '48+'])",
    solution="""
def solve(df):
    X = df.drop(columns=["customer_id", "churned"])
    X["avg_charge"] = (X["total_charges"] / X["tenure"]).where(X["tenure"] > 0, X["monthly_charges"])
    X["tenure_band"] = pd.cut(X["tenure"], [0, 12, 24, 48, np.inf], right=False,
                              labels=["0-11", "12-23", "24-47", "48+"])
    return X, df["churned"]
""",
    explanation="""
`pd.cut` bins are right-closed by default ((0, 12]); `right=False` gives [0, 12), so tenure 12 falls in "12-23" and tenure 0 is not lost as NaN. For the division, compute it everywhere and *replace* the tenure-0 rows: pandas returns `inf`/NaN instead of raising, so the bad values pass silently if you forget.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.cut.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.Series.where.html"],
    wrong_solutions=[
        dict(code="""
def solve(df):
    X = df.drop(columns=["customer_id", "churned"])
    X["avg_charge"] = (X["total_charges"] / X["tenure"]).where(X["tenure"] > 0, X["monthly_charges"])
    X["tenure_band"] = pd.cut(X["tenure"], [0, 12, 24, 48, np.inf], labels=["0-11", "12-23", "24-47", "48+"])
    return X, df["churned"]
""", why="right-closed bins: edges land in the wrong band, tenure 0 becomes NaN"),
        dict(code="""
def solve(df):
    X = df.drop(columns=["customer_id", "churned"])
    X["avg_charge"] = X["total_charges"] / X["tenure"]
    X["tenure_band"] = pd.cut(X["tenure"], [0, 12, 24, 48, np.inf], right=False, labels=["0-11", "12-23", "24-47", "48+"])
    return X, df["churned"]
""", why="division by zero for tenure 0"),
    ],
),
dict(
    id="ch-004",
    chain="churn", step=4,
    title="Churn 4/5: the modelling pipeline",
    difficulty="Medium",
    tags=["pipelines"],
    signature="def solve(X: pd.DataFrame, y: pd.Series):",
    statement="""
`X, y` are the features and target from step 3 (`X` mixes numeric, text and categorical columns). Build, **without fitting it**, a `Pipeline` with two steps:

1. `"prep"`: a `ColumnTransformer` with `"num"` = `StandardScaler` on the numeric columns and `"cat"` = `OneHotEncoder(handle_unknown="ignore")` on all other columns, both selected **by dtype**;
2. `"model"`: `LogisticRegression(max_iter=1000)`.

Return the unfitted pipeline (step 5 cross-validates it). The tests fit your pipeline and compare its predictions with the specified one.
""",
    setup=CHURN + """
EXAMPLE = lambda: dict(zip(["X", "y"], xy(0, 60)))
""",
    tests="""
TESTS = [
    lambda: dict(zip(["X", "y"], xy(1, 300))),
    lambda: dict(zip(["X", "y"], xy(2, 1500))),
    Test(lambda: dict(zip(["X", "y"], xy(3, 40))), "small"),
]

def check(got, exp, inputs):
    from sklearn.pipeline import Pipeline
    from sklearn.exceptions import NotFittedError
    from sklearn.utils.validation import check_is_fitted
    if not isinstance(got, Pipeline):
        fail(f"return a Pipeline, got {type(got).__name__}")
    names = [n for n, _ in got.steps]
    if names != ["prep", "model"]:
        fail(f"step names should be ['prep', 'model'], got {names}")
    try:
        check_is_fitted(got)
        fitted = True
    except NotFittedError:
        fitted = False
    if fitted:
        fail("return the pipeline unfitted: step 5 cross-validates it")
    X, y = inputs["X"], inputs["y"]
    try:
        p = got.fit(X, y).predict_proba(X)[:, 1]
    except Exception as e:
        fail(f"fitting your pipeline on (X, y) failed: {type(e).__name__}: {e}")
    q = exp.fit(X, y).predict_proba(X)[:, 1]
    if not np.allclose(p, q, atol=1e-6):
        fail("predictions differ from the specified pipeline (scaling, encoding or column selection?)")
""",
    hint1="`Pipeline([('prep', ColumnTransformer([...])), ('model', ...)])` with `make_column_selector(dtype_include='number')` / `(dtype_exclude='number')`.",
    hint2="pre = ColumnTransformer([('num', StandardScaler(), make_column_selector(dtype_include='number')),\n                         ('cat', OneHotEncoder(handle_unknown='ignore'), make_column_selector(dtype_exclude='number'))])\nPipeline([('prep', pre), ('model', LogisticRegression(max_iter=1000))])",
    solution="""
from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

def solve(X, y):
    pre = ColumnTransformer([("num", StandardScaler(), make_column_selector(dtype_include="number")),
                             ("cat", OneHotEncoder(handle_unknown="ignore"), make_column_selector(dtype_exclude="number"))])
    return Pipeline([("prep", pre), ("model", LogisticRegression(max_iter=1000))])
""",
    explanation="""
One pipeline object holds every learned step, so cross-validation refits all of them on each training fold (no leakage), and `predict` on new data repeats the exact same preprocessing. `dtype_exclude='number'` catches str, object and the categorical `tenure_band` alike. Keep construction and fitting separate.
""",
    docs=["https://scikit-learn.org/stable/modules/compose.html#columntransformer-for-heterogeneous-data",
          "https://scikit-learn.org/stable/modules/generated/sklearn.pipeline.Pipeline.html"],
    wrong_solutions=[
        dict(code="""
from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

def solve(X, y):
    pre = ColumnTransformer([("num", StandardScaler(), make_column_selector(dtype_include="number")),
                             ("cat", OneHotEncoder(handle_unknown="ignore"), make_column_selector(dtype_exclude="number"))])
    return Pipeline([("prep", pre), ("model", LogisticRegression(max_iter=1000))]).fit(X, y)
""", why="already fitted"),
        dict(code="""
from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

def solve(X, y):
    pre = ColumnTransformer([("num", StandardScaler(), make_column_selector(dtype_include="number"))])
    return Pipeline([("prep", pre), ("model", LogisticRegression(max_iter=1000))])
""", why="categorical columns dropped"),
    ],
),
dict(
    id="ch-005",
    chain="churn", step=5,
    title="Churn 5/5: cross-validated AUC vs a baseline",
    difficulty="Medium",
    tags=["evaluation"],
    signature="def solve(pipe, X: pd.DataFrame, y: pd.Series) -> dict:",
    statement="""
`pipe` is the unfitted pipeline from step 4 and `X, y` the data from step 3. With `StratifiedKFold(5, shuffle=True, random_state=0)`, compute the mean cross-validated **ROC AUC** of `pipe` and of a baseline `DummyClassifier(strategy="prior")`. Return `{"model_auc": ..., "baseline_auc": ...}`.
""",
    setup=CHURN + """
def make(seed, n):
    X, y = xy(seed, n)
    return {"pipe": REF("ch-004", X=X, y=y), "X": X, "y": y}

EXAMPLE = lambda: make(0, 120)
""",
    tests="""
TESTS = [
    lambda: make(1, 300),
    lambda: make(2, 1500),
    Test(lambda: make(3, 60), "small"),
]
""",
    hint1="`cross_val_score(estimator, X, y, cv=cv, scoring='roc_auc').mean()` for both estimators with the same `cv` object.",
    hint2="cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)\ncross_val_score(pipe, X, y, cv=cv, scoring='roc_auc').mean()",
    solution="""
from sklearn.dummy import DummyClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score

def solve(pipe, X, y):
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
    auc = lambda est: float(cross_val_score(est, X, y, cv=cv, scoring="roc_auc").mean())
    return {"model_auc": auc(pipe), "baseline_auc": auc(DummyClassifier(strategy="prior"))}
""",
    explanation="""
Using the same folds for both estimators makes the comparison paired and fair. A constant predictor has AUC 0.5, so "0.80 vs 0.50" is the sentence to say. Next steps in an interview: the spread across folds, a calibration check, and the top drivers (coefficients from step 4, or permutation importance).
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.cross_val_score.html",
          "https://scikit-learn.org/stable/modules/generated/sklearn.dummy.DummyClassifier.html"],
    wrong_solutions=[
        dict(code="""
from sklearn.dummy import DummyClassifier
from sklearn.model_selection import cross_val_score

def solve(pipe, X, y):
    return {"model_auc": float(cross_val_score(pipe, X, y, cv=5, scoring="roc_auc").mean()),
            "baseline_auc": float(cross_val_score(DummyClassifier(strategy="prior"), X, y, cv=5, scoring="roc_auc").mean())}
""", why="unshuffled folds"),
        dict(code="""
from sklearn.dummy import DummyClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score

def solve(pipe, X, y):
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
    return {"model_auc": float(cross_val_score(pipe, X, y, cv=cv).mean()),
            "baseline_auc": float(cross_val_score(DummyClassifier(strategy="prior"), X, y, cv=cv).mean())}
""", why="accuracy, not AUC"),
    ],
),
# ================================================================== salary (regression)
dict(
    id="ch-006",
    chain="salary", step=1,
    title="Salary 1/4: first look at the HR export",
    difficulty="Easy",
    tags=["inspection"],
    signature="def solve(raw: pd.DataFrame) -> dict:",
    statement="""
`raw` is a messy HR export: `employee_id, department, level, city, remote, hire_date, years_experience, performance, salary, updated`. Return a dict:

* `n_rows`: number of rows;
* `n_repeated_ids`: number of rows whose `employee_id` already appeared in an earlier row;
* `department_spellings`: number of distinct raw `department` strings;
* `departments`: number of distinct departments after stripping whitespace and Title-casing;
* `salary_unparsed`: number of `salary` values that are still not numbers after removing the thousands commas.
""",
    setup="""
EXAMPLE = lambda: {"raw": D.hr_raw(seed=0, n=20)}
""",
    tests="""
TESTS = [
    lambda: {"raw": D.hr_raw(seed=1, n=150)},
    lambda: {"raw": D.hr_raw(seed=2, n=2000)},
    Test(lambda: {"raw": D.hr_raw(seed=3, n=6, dup_share=0.0)}, "no repeats"),
]
""",
    hint1="`s.duplicated().sum()`, `nunique()` before and after `.str.strip().str.title()`, and `pd.to_numeric(s.str.replace(',', ''), errors='coerce').isna().sum()`.",
    hint2="sal = pd.to_numeric(raw['salary'].str.replace(',', ''), errors='coerce')\nraw['employee_id'].duplicated().sum(), raw['department'].str.strip().str.title().nunique(), sal.isna().sum()",
    solution="""
def solve(raw):
    sal = pd.to_numeric(raw["salary"].str.replace(",", ""), errors="coerce")
    return {"n_rows": len(raw), "n_repeated_ids": int(raw["employee_id"].duplicated().sum()),
            "department_spellings": int(raw["department"].nunique()),
            "departments": int(raw["department"].str.strip().str.title().nunique()),
            "salary_unparsed": int(sal.isna().sum())}
""",
    explanation="""
Counting spellings before and after normalization quantifies the mess (here about 15 spellings for 5 departments). Measuring the parse failures tells you whether the remaining NaNs are real missing values (`'n/a'`) or a format you haven't handled yet.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.Series.duplicated.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.Series.nunique.html"],
    wrong_solutions=[
        dict(code="""
def solve(raw):
    sal = pd.to_numeric(raw["salary"], errors="coerce")
    return {"n_rows": len(raw), "n_repeated_ids": int(raw["employee_id"].duplicated().sum()),
            "department_spellings": int(raw["department"].nunique()),
            "departments": int(raw["department"].str.strip().str.title().nunique()),
            "salary_unparsed": int(sal.isna().sum())}
""", why="commas not removed"),
        dict(code="""
def solve(raw):
    sal = pd.to_numeric(raw["salary"].str.replace(",", ""), errors="coerce")
    return {"n_rows": len(raw), "n_repeated_ids": int(raw.duplicated().sum()),
            "department_spellings": int(raw["department"].nunique()),
            "departments": int(raw["department"].str.strip().str.title().nunique()),
            "salary_unparsed": int(sal.isna().sum())}
""", why="whole-row duplicates (the records differ)"),
    ],
),
dict(
    id="ch-007",
    chain="salary", step=2,
    title="Salary 2/4: clean the HR export",
    difficulty="Medium",
    tags=["cleaning"],
    signature="def solve(raw: pd.DataFrame) -> pd.DataFrame:",
    statement="""
Clean `raw` (the HR export from step 1) and return a DataFrame with the same columns in the same order:

1. keep only each employee's **most recent** record (latest `updated`);
2. `salary`: remove thousands commas and convert to float (`'n/a'` becomes NaN);
3. `department`: strip whitespace and Title-case;
4. `hire_date`: parse the `DD/MM/YYYY` strings to datetimes;
5. drop rows with a missing `salary`;
6. sort by `employee_id` and reset the index to 0..n-1.

Dtypes are checked.
""",
    setup="""
EXAMPLE = lambda: {"raw": D.hr_raw(seed=0, n=12, dup_share=0.25)}
""",
    tests="""
TESTS = [
    lambda: {"raw": D.hr_raw(seed=1, n=150)},
    lambda: {"raw": D.hr_raw(seed=2, n=2000)},
    Test(lambda: {"raw": D.hr_raw(seed=3, n=6, dup_share=0.0)}, "no repeats"),
]
""",
    compare=dict(check_dtype=True),
    hint1="Sort by `updated`, `drop_duplicates('employee_id', keep='last')`, then `assign` the converted columns (`pd.to_numeric`, `.str.strip().str.title()`, `pd.to_datetime(format='%d/%m/%Y')`), `dropna(subset=['salary'])`.",
    hint2="(raw.sort_values('updated').drop_duplicates('employee_id', keep='last')\n    .assign(salary=lambda d: pd.to_numeric(d['salary'].str.replace(',', ''), errors='coerce'),\n            hire_date=lambda d: pd.to_datetime(d['hire_date'], format='%d/%m/%Y'))\n    .dropna(subset=['salary']).sort_values('employee_id', ignore_index=True))",
    solution="""
def solve(raw):
    return (raw.sort_values("updated").drop_duplicates("employee_id", keep="last")
               .assign(salary=lambda d: pd.to_numeric(d["salary"].str.replace(",", ""), errors="coerce"),
                       department=lambda d: d["department"].str.strip().str.title(),
                       hire_date=lambda d: pd.to_datetime(d["hire_date"], format="%d/%m/%Y"))
               .dropna(subset=["salary"])
               .sort_values("employee_id", ignore_index=True))
""",
    explanation="""
One readable chain: dedupe, convert, filter, order. `assign` with an existing column name replaces it **in place** (the column order is kept). Deduplicate by key *before* converting, and after sorting by timestamp, so "last" means latest.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.assign.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.to_datetime.html"],
    wrong_solutions=[
        dict(code="""
def solve(raw):
    return (raw.sort_values("updated").drop_duplicates("employee_id")
               .assign(salary=lambda d: pd.to_numeric(d["salary"].str.replace(",", ""), errors="coerce"),
                       department=lambda d: d["department"].str.strip().str.title(),
                       hire_date=lambda d: pd.to_datetime(d["hire_date"], format="%d/%m/%Y"))
               .dropna(subset=["salary"]).sort_values("employee_id", ignore_index=True))
""", why="keeps the oldest record"),
        dict(code="""
def solve(raw):
    return (raw.sort_values("updated").drop_duplicates("employee_id", keep="last")
               .assign(salary=lambda d: pd.to_numeric(d["salary"].str.replace(",", ""), errors="coerce"),
                       department=lambda d: d["department"].str.strip().str.title(),
                       hire_date=lambda d: pd.to_datetime(d["hire_date"], format="%m/%d/%Y", errors="coerce"))
               .dropna(subset=["salary"]).sort_values("employee_id", ignore_index=True))
""", why="month-first dates"),
    ],
),
dict(
    id="ch-008",
    chain="salary", step=3,
    title="Salary 3/4: features and target",
    difficulty="Medium",
    tags=["feature engineering"],
    signature="def solve(df: pd.DataFrame) -> tuple:",
    statement="""
`df` is the cleaned HR table from step 2. Return `(X, y)` with the index of `df`:

* `y`: `salary`;
* `X`: columns `department, level, city, years_experience, performance` (as they are), then `remote` as an integer 0/1, then `tenure_years`: the time from `hire_date` to 2025-06-01, in days divided by 365.25.
""",
    setup=SALARY + """
EXAMPLE = lambda: {"df": clean(0, 12)}
""",
    tests="""
TESTS = [
    lambda: {"df": clean(1, 150)},
    lambda: {"df": clean(2, 2000)},
    Test(lambda: {"df": clean(3, 4)}, "tiny"),
]
""",
    compare=dict(check_dtype=True),
    hint1="Select the columns, then `assign(remote=df['remote'].astype(int), tenure_years=(pd.Timestamp('2025-06-01') - df['hire_date']).dt.days / 365.25)`.",
    hint2="X = df[['department', 'level', 'city', 'years_experience', 'performance']].assign(\n    remote=df['remote'].astype(int),\n    tenure_years=(pd.Timestamp('2025-06-01') - df['hire_date']).dt.days / 365.25)",
    solution="""
def solve(df):
    X = df[["department", "level", "city", "years_experience", "performance"]].assign(
        remote=df["remote"].astype(int),
        tenure_years=(pd.Timestamp("2025-06-01") - df["hire_date"]).dt.days / 365.25)
    return X, df["salary"]
""",
    explanation="""
Subtracting datetimes gives a Timedelta; `.dt.days` turns it into numbers. Use a **fixed** reference date (the snapshot date), not `pd.Timestamp.now()`, so the features are reproducible. Leave the categoricals as text: the pipeline in step 4 encodes them.
""",
    docs=["https://pandas.pydata.org/docs/user_guide/timedeltas.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.Series.dt.days.html"],
    wrong_solutions=[
        dict(code="""
def solve(df):
    X = df[["department", "level", "city", "years_experience", "performance"]].assign(
        remote=df["remote"].astype(int),
        tenure_years=(pd.Timestamp("2025-06-01") - df["hire_date"]).dt.days)
    return X, df["salary"]
""", why="tenure in days"),
        dict(code="""
def solve(df):
    X = df[["department", "level", "city", "years_experience", "performance", "remote"]].assign(
        tenure_years=(pd.Timestamp("2025-06-01") - df["hire_date"]).dt.days / 365.25)
    return X, df["salary"]
""", why="remote left as bool"),
    ],
),
dict(
    id="ch-009",
    chain="salary", step=4,
    title="Salary 4/4: Ridge vs baseline, cross-validated",
    difficulty="Hard",
    tags=["pipelines", "evaluation"],
    signature="def solve(X: pd.DataFrame, y: pd.Series) -> dict:",
    statement="""
`X, y` come from step 3. Evaluate with `KFold(5, shuffle=True, random_state=0)`:

* the model: a `ColumnTransformer` (`"num"`: `StandardScaler` on numeric columns, `"cat"`: `OneHotEncoder(handle_unknown="ignore")` on the others, selected by dtype) followed by `Ridge(alpha=1.0)`;
* the baseline: `DummyRegressor()` (predicts the training mean).

Return `{"model_rmse": ..., "model_r2": ..., "baseline_rmse": ...}`: the mean cross-validated RMSE (a **positive** number) and R².
""",
    setup=SALARY + """
def make(seed, n):
    X, y = REF("ch-008", df=clean(seed, n))
    return {"X": X, "y": y}

EXAMPLE = lambda: make(0, 80)
""",
    tests="""
TESTS = [
    lambda: make(1, 200),
    lambda: make(2, 2000),
    Test(lambda: make(3, 40), "small"),
]
""",
    hint1="`cross_validate(est, X, y, cv=cv, scoring=['neg_root_mean_squared_error', 'r2'])`; scikit-learn maximizes scores, so error metrics come negated: flip the sign.",
    hint2="res = cross_validate(make_pipeline(pre, Ridge(alpha=1.0)), X, y, cv=cv, scoring=['neg_root_mean_squared_error', 'r2'])\n-res['test_neg_root_mean_squared_error'].mean(), res['test_r2'].mean()",
    solution="""
from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold, cross_validate
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

def solve(X, y):
    pre = ColumnTransformer([("num", StandardScaler(), make_column_selector(dtype_include="number")),
                             ("cat", OneHotEncoder(handle_unknown="ignore"), make_column_selector(dtype_exclude="number"))])
    cv, scoring = KFold(n_splits=5, shuffle=True, random_state=0), ["neg_root_mean_squared_error", "r2"]
    m = cross_validate(make_pipeline(pre, Ridge(alpha=1.0)), X, y, cv=cv, scoring=scoring)
    b = cross_validate(DummyRegressor(), X, y, cv=cv, scoring=scoring)
    return {"model_rmse": float(-m["test_neg_root_mean_squared_error"].mean()),
            "model_r2": float(m["test_r2"].mean()),
            "baseline_rmse": float(-b["test_neg_root_mean_squared_error"].mean())}
""",
    explanation="""
Scorers follow "greater is better", so losses are exposed as `neg_*`; forgetting the minus sign gives a negative RMSE. The baseline's R² is about 0 and its RMSE is roughly the std of salaries, so the model's RMSE should be judged against it. Ridge's penalty assumes scaled features.
""",
    docs=["https://scikit-learn.org/stable/modules/model_evaluation.html#scoring-parameter",
          "https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html"],
    wrong_solutions=[
        dict(code="""
from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold, cross_validate
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

def solve(X, y):
    pre = ColumnTransformer([("num", StandardScaler(), make_column_selector(dtype_include="number")),
                             ("cat", OneHotEncoder(handle_unknown="ignore"), make_column_selector(dtype_exclude="number"))])
    cv, scoring = KFold(n_splits=5, shuffle=True, random_state=0), ["neg_root_mean_squared_error", "r2"]
    m = cross_validate(make_pipeline(pre, Ridge(alpha=1.0)), X, y, cv=cv, scoring=scoring)
    b = cross_validate(DummyRegressor(), X, y, cv=cv, scoring=scoring)
    return {"model_rmse": float(m["test_neg_root_mean_squared_error"].mean()), "model_r2": float(m["test_r2"].mean()),
            "baseline_rmse": float(b["test_neg_root_mean_squared_error"].mean())}
""", why="negative RMSE"),
        dict(code="""
from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold, cross_validate
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder

def solve(X, y):
    pre = ColumnTransformer([("num", "passthrough", make_column_selector(dtype_include="number")),
                             ("cat", OneHotEncoder(handle_unknown="ignore"), make_column_selector(dtype_exclude="number"))])
    cv, scoring = KFold(n_splits=5, shuffle=True, random_state=0), ["neg_root_mean_squared_error", "r2"]
    m = cross_validate(make_pipeline(pre, Ridge(alpha=1.0)), X, y, cv=cv, scoring=scoring)
    b = cross_validate(DummyRegressor(), X, y, cv=cv, scoring=scoring)
    return {"model_rmse": float(-m["test_neg_root_mean_squared_error"].mean()), "model_r2": float(m["test_r2"].mean()),
            "baseline_rmse": float(-b["test_neg_root_mean_squared_error"].mean())}
""", why="numeric features not scaled"),
    ],
),
# ================================================================== factor (time series)
dict(
    id="ch-010",
    chain="factor", step=1,
    title="Factor 1/5: the daily returns matrix",
    difficulty="Easy",
    tags=["time series"],
    signature="def solve(prices: pd.DataFrame) -> pd.DataFrame:",
    statement="""
`prices` is a long daily panel (`date, ticker, close, volume`). Return the **wide** matrix of daily simple returns: index = date, one column per ticker (A to Z), first row NaN.
""",
    setup="""
EXAMPLE = lambda: {"prices": D.prices(seed=0, n_days=6, n_tickers=3)}
""",
    tests="""
TESTS = [
    lambda: {"prices": D.prices(seed=1, n_days=60, n_tickers=8)},
    lambda: {"prices": D.prices(seed=2, n_days=250, n_tickers=20)},
    Test(lambda: {"prices": D.prices(seed=3, n_days=2, n_tickers=2)}, "two days"),
]
""",
    hint1="`pivot(index='date', columns='ticker', values='close')` then `.pct_change()` (per column).",
    hint2="prices.pivot(index='date', columns='ticker', values='close').pct_change()",
    solution="""
def solve(prices):
    return prices.pivot(index="date", columns="ticker", values="close").pct_change()
""",
    explanation="""
Going wide makes per-ticker time-series operations column-wise and vectorized: no groupby needed, and dates align across tickers. Missing days become NaN cells instead of silently shifting rows. Go back to long with `stack()` when you need a row per (date, ticker).
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.pivot.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.pct_change.html"],
    wrong_solutions=[
        dict(code="def solve(prices):\n    return prices.pivot(index='date', columns='ticker', values='close').pct_change(axis=1)", why="across tickers"),
        dict(code="def solve(prices):\n    return prices.pivot(index='date', columns='ticker', values='close').diff()", why="price changes"),
    ],
),
dict(
    id="ch-011",
    chain="factor", step=2,
    title="Factor 2/5: lagged momentum and volatility features",
    difficulty="Medium",
    tags=["feature engineering", "time series"],
    signature="def solve(R: pd.DataFrame) -> pd.DataFrame:",
    statement="""
`R` is the wide daily returns matrix from step 1 (index `date`, one column per ticker). For each date and ticker, build two features that use only information available **before** that date:

* `mom`: the sum of **log** returns (`log(1 + r)`) over the 20 days ending **yesterday**;
* `vol`: the standard deviation of simple returns over the 20 days ending yesterday.

Return a long DataFrame with columns `date, ticker, mom, vol`, sorted by date then ticker, without rows where a feature is missing, and with a default index.
""",
    setup=FACTOR + """
EXAMPLE = lambda: {"R": returns(0, 30, 3)}
""",
    tests="""
TESTS = [
    lambda: {"R": returns(1, 80, 6)},
    lambda: {"R": returns(2, 300, 20)},
    Test(lambda: {"R": returns(3, 22, 2)}, "barely long enough"),
]
""",
    hint1="Rolling on the wide frame (`np.log1p(R).rolling(20).sum()`, `R.rolling(20).std()`), `.shift(1)` to end yesterday, then `stack()` both into a long frame and `dropna()`.",
    hint2="mom = np.log1p(R).rolling(20).sum().shift(1)\nvol = R.rolling(20).std().shift(1)\npd.concat({'mom': mom.stack(), 'vol': vol.stack()}, axis=1).dropna()",
    solution="""
def solve(R):
    mom = np.log1p(R).rolling(20).sum().shift(1)
    vol = R.rolling(20).std().shift(1)
    out = pd.concat({"mom": mom.stack(), "vol": vol.stack()}, axis=1).dropna()
    return out.rename_axis(["date", "ticker"]).reset_index()
""",
    explanation="""
The `.shift(1)` is what makes these features tradable: a window ending **today** contains today's return, which you won't know at the time you trade on today's signal. Since pandas 3, `stack()` keeps NaN rows (the old `dropna=True` default is gone), so drop them explicitly.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.rolling.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.stack.html"],
    wrong_solutions=[
        dict(code="""
def solve(R):
    mom = np.log1p(R).rolling(20).sum()
    vol = R.rolling(20).std()
    out = pd.concat({"mom": mom.stack(), "vol": vol.stack()}, axis=1).dropna()
    return out.rename_axis(["date", "ticker"]).reset_index()
""", why="windows include today (lookahead)"),
        dict(code="""
def solve(R):
    mom = R.rolling(20).sum().shift(1)
    vol = R.rolling(20).std().shift(1)
    out = pd.concat({"mom": mom.stack(), "vol": vol.stack()}, axis=1).dropna()
    return out.rename_axis(["date", "ticker"]).reset_index()
""", why="sum of simple returns"),
    ],
),
dict(
    id="ch-012",
    chain="factor", step=3,
    title="Factor 3/5: forward-return labels",
    difficulty="Medium",
    tags=["time series", "feature engineering"],
    signature="def solve(prices: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:",
    statement="""
`prices` is the long daily panel (sorted by date, ticker) and `features` the long table from step 2 (`date, ticker, mom, vol`). Add the label `fwd_5`: each ticker's close **5 trading days ahead** divided by today's close, minus 1. Attach it to `features` by (`date`, `ticker`), drop rows where the label is missing, keep the `features` row order, and reset the index.
""",
    setup=FACTOR + """
def make(seed, n_days, n_tickers):
    p = D.prices(seed=seed, n_days=n_days, n_tickers=n_tickers)
    return {"prices": p, "features": REF("ch-011", R=REF("ch-010", prices=p))}

EXAMPLE = lambda: make(0, 30, 3)
""",
    tests="""
TESTS = [
    lambda: make(1, 80, 6),
    lambda: make(2, 300, 20),
    Test(lambda: make(3, 27, 2), "almost no labelled rows"),
]
""",
    hint1="`prices.groupby('ticker')['close'].shift(-5) / prices['close'] - 1`, then `merge` on `['date', 'ticker']`.",
    hint2="fwd = prices.groupby('ticker')['close'].shift(-5) / prices['close'] - 1\nfeatures.merge(prices[['date', 'ticker']].assign(fwd_5=fwd), on=['date', 'ticker']).dropna(subset=['fwd_5'])",
    solution="""
def solve(prices, features):
    fwd = prices.groupby("ticker")["close"].shift(-5) / prices["close"] - 1
    lab = prices[["date", "ticker"]].assign(fwd_5=fwd)
    return (features.merge(lab, on=["date", "ticker"], how="left")
                    .dropna(subset=["fwd_5"]).reset_index(drop=True))
""",
    explanation="""
The label is the only place a negative shift belongs. Each label covers 5 future days, so labels on neighbouring dates overlap. That's why step 4 leaves an embargo between training and test periods. Joining on keys (instead of relying on row order) keeps features and labels matched even if a table is re-sorted.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.api.typing.DataFrameGroupBy.shift.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.merge.html"],
    wrong_solutions=[
        dict(code="""
def solve(prices, features):
    fwd = prices["close"].shift(-5) / prices["close"] - 1
    lab = prices[["date", "ticker"]].assign(fwd_5=fwd)
    return features.merge(lab, on=["date", "ticker"], how="left").dropna(subset=["fwd_5"]).reset_index(drop=True)
""", why="shift across tickers"),
        dict(code="""
def solve(prices, features):
    fwd = prices.groupby("ticker")["close"].shift(5) / prices["close"] - 1
    lab = prices[["date", "ticker"]].assign(fwd_5=fwd)
    return features.merge(lab, on=["date", "ticker"], how="left").dropna(subset=["fwd_5"]).reset_index(drop=True)
""", why="past return, not forward"),
    ],
),
dict(
    id="ch-013",
    chain="factor", step=4,
    title="Factor 4/5: walk-forward predictions with an embargo",
    difficulty="Hard",
    tags=["time series", "evaluation"],
    signature="def solve(data: pd.DataFrame) -> pd.DataFrame:",
    statement="""
`data` comes from step 3 (`date, ticker, mom, vol, fwd_5`, sorted by date, ticker). Run a monthly **walk-forward**: for each calendar month from the **third** month present in `data` onward (the test month),

* let `dates` be the sorted unique dates of `data` and `d0` the first date of the test month;
* train `Ridge(alpha=1.0)` on features `[mom, vol]` and target `fwd_5`, using only rows dated **before** `dates[i0 - 5]`, where `i0` is the position of `d0` in `dates` (a 5-date embargo, because labels look 5 days ahead);
* predict `fwd_5` for the test month's rows.

Return the test rows (all original columns) plus a `pred` column, concatenated in month order, with a default index.
""",
    setup=FACTOR + """
EXAMPLE = lambda: {"data": labelled(0, 90, 5)}
""",
    tests="""
TESTS = [
    lambda: {"data": labelled(1, 140, 8)},
    lambda: {"data": labelled(2, 300, 20)},
    Test(lambda: {"data": labelled(3, 75, 4)}, "a single test month"),
]
""",
    hint1="Loop over `data['date'].dt.to_period('M').unique()[2:]`; the cut-off is `dates[dates.get_loc(d0) - 5]` with `dates = pd.DatetimeIndex(data['date'].unique()).sort_values()`.",
    hint2="for m in month.unique()[2:]:\n    test = data[month == m]\n    cut = dates[dates.get_loc(test['date'].min()) - 5]\n    train = data[data['date'] < cut]\n    model = Ridge(alpha=1.0).fit(train[['mom', 'vol']], train['fwd_5'])",
    solution="""
from sklearn.linear_model import Ridge

def solve(data):
    dates = pd.DatetimeIndex(data["date"].unique()).sort_values()
    month = data["date"].dt.to_period("M")
    out = []
    for m in month.unique()[2:]:
        test = data[month == m]
        train = data[data["date"] < dates[dates.get_loc(test["date"].min()) - 5]]
        model = Ridge(alpha=1.0).fit(train[["mom", "vol"]], train["fwd_5"])
        out.append(test.assign(pred=model.predict(test[["mom", "vol"]])))
    return pd.concat(out, ignore_index=True)
""",
    explanation="""
Walk-forward retrains on an expanding past and predicts only the future, exactly as you would in production. Without the embargo, the last training labels (which look 5 days ahead) overlap the test period, a subtle leak that inflates backtests. Collect pieces in a list and `concat` once at the end.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.Series.dt.to_period.html"],
    wrong_solutions=[
        dict(code="""
from sklearn.linear_model import Ridge

def solve(data):
    month = data["date"].dt.to_period("M")
    out = []
    for m in month.unique()[2:]:
        test = data[month == m]
        train = data[data["date"] < test["date"].min()]
        model = Ridge(alpha=1.0).fit(train[["mom", "vol"]], train["fwd_5"])
        out.append(test.assign(pred=model.predict(test[["mom", "vol"]])))
    return pd.concat(out, ignore_index=True)
""", why="no embargo"),
        dict(code="""
from sklearn.linear_model import Ridge

def solve(data):
    month = data["date"].dt.to_period("M")
    model = Ridge(alpha=1.0).fit(data[["mom", "vol"]], data["fwd_5"])
    test = data[month.isin(month.unique()[2:])]
    return test.assign(pred=model.predict(test[["mom", "vol"]])).reset_index(drop=True)
""", why="one model trained on everything (lookahead)"),
    ],
),
dict(
    id="ch-014",
    chain="factor", step=5,
    title="Factor 5/5: information coefficient summary",
    difficulty="Medium",
    tags=["evaluation"],
    signature="def solve(preds: pd.DataFrame) -> dict:",
    statement="""
`preds` comes from step 4 (`date, ticker, mom, vol, fwd_5, pred`). For each date compute the **Spearman** rank correlation between `pred` and `fwd_5` across tickers (the IC). Return:

* `mean_ic`: the mean IC;
* `ic_tstat`: `mean_ic / std(IC) * sqrt(number of dates)` (sample std, `ddof=1`);
* `hit_rate`: the share of dates with a positive IC.
""",
    setup=FACTOR + """
def make(seed, n_days, n_tickers):
    return {"preds": REF("ch-013", data=labelled(seed, n_days, n_tickers))}

EXAMPLE = lambda: make(0, 90, 5)
""",
    tests="""
TESTS = [
    lambda: make(1, 140, 8),
    lambda: make(2, 300, 20),
    Test(lambda: make(3, 75, 4), "a single test month"),
]
""",
    compare=dict(rtol=1e-6, atol=1e-9),
    hint1="Per-date IC with `groupby('date')[['pred', 'fwd_5']].apply(lambda g: g['pred'].corr(g['fwd_5'], method='spearman'))`, then summarize the resulting Series.",
    hint2="ic = preds.groupby('date')[['pred', 'fwd_5']].apply(lambda g: g['pred'].corr(g['fwd_5'], method='spearman'))\nic.mean(), ic.mean() / ic.std() * np.sqrt(len(ic)), (ic > 0).mean()",
    solution="""
def solve(preds):
    ic = preds.groupby("date")[["pred", "fwd_5"]].apply(lambda g: g["pred"].corr(g["fwd_5"], method="spearman"))
    return {"mean_ic": float(ic.mean()), "ic_tstat": float(ic.mean() / ic.std() * np.sqrt(len(ic))),
            "hit_rate": float((ic > 0).mean())}
""",
    explanation="""
A per-date IC treats each cross-section as one experiment; the t-stat asks whether the average IC is distinguishable from 0. Because daily ICs with 5-day labels overlap, they're autocorrelated and the naive t-stat is overstated. Use Newey-West or non-overlapping dates to be honest about it.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.Series.corr.html"],
    wrong_solutions=[
        dict(code="""
def solve(preds):
    ic = preds.groupby("date")[["pred", "fwd_5"]].apply(lambda g: g["pred"].corr(g["fwd_5"]))
    return {"mean_ic": float(ic.mean()), "ic_tstat": float(ic.mean() / ic.std() * np.sqrt(len(ic))), "hit_rate": float((ic > 0).mean())}
""", why="Pearson"),
        dict(code="""
def solve(preds):
    ic = preds.groupby("date")[["pred", "fwd_5"]].apply(lambda g: g["pred"].corr(g["fwd_5"], method="spearman"))
    return {"mean_ic": float(ic.mean()), "ic_tstat": float(ic.mean() / ic.std()), "hit_rate": float((ic > 0).mean())}
""", why="t-stat without sqrt(n)"),
    ],
),
# ================================================================== segments (clustering + PCA)
dict(
    id="ch-015",
    chain="segments", step=1,
    title="Segments 1/4: an RFM table",
    difficulty="Medium",
    tags=["feature engineering"],
    signature="def solve(orders: pd.DataFrame) -> pd.DataFrame:",
    statement="""
From the orders table, build one row per customer (index = `customer_id`, sorted) with:

* `recency`: days between the customer's **last** order and the snapshot date, defined as the latest `order_date` in the table **plus one day**;
* `frequency`: number of orders;
* `monetary`: total revenue.
""",
    setup="""
EXAMPLE = lambda: {"orders": D.orders(seed=0, n=40, n_customers=10)}
""",
    tests="""
TESTS = [
    lambda: {"orders": D.orders(seed=1, n=300, n_customers=60)},
    lambda: {"orders": D.orders(seed=2, n=3000, n_customers=400)},
    Test(lambda: {"orders": D.orders(seed=3, n=5, n_customers=3)}, "tiny"),
]
""",
    hint1="Group by customer: `max()` of the dates, `size()`, `sum()` of revenue; recency is `(snapshot - last_date).dt.days`.",
    hint2="snap = orders['order_date'].max() + pd.Timedelta(days=1)\ng = orders.groupby('customer_id')\npd.DataFrame({'recency': (snap - g['order_date'].max()).dt.days, 'frequency': g.size(), 'monetary': g['revenue'].sum()})",
    solution="""
def solve(orders):
    snap = orders["order_date"].max() + pd.Timedelta(days=1)
    g = orders.groupby("customer_id")
    return pd.DataFrame({"recency": (snap - g["order_date"].max()).dt.days,
                         "frequency": g.size(), "monetary": g["revenue"].sum()})
""",
    explanation="""
RFM (recency, frequency, monetary value) is the classic customer-behaviour summary and a strong segmentation baseline. The snapshot is fixed from the data (not "today"), so results are reproducible; the extra day makes recency at least 1.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.api.typing.DataFrameGroupBy.agg.html"],
    wrong_solutions=[
        dict(code="""
def solve(orders):
    snap = orders["order_date"].max() + pd.Timedelta(days=1)
    g = orders.groupby("customer_id")
    return pd.DataFrame({"recency": (snap - g["order_date"].min()).dt.days, "frequency": g.size(), "monetary": g["revenue"].sum()})
""", why="days since the first order"),
        dict(code="""
def solve(orders):
    snap = orders["order_date"].max() + pd.Timedelta(days=1)
    g = orders.groupby("customer_id")
    return pd.DataFrame({"recency": (snap - g["order_date"].max()).dt.days, "frequency": g.size(), "monetary": g["revenue"].mean()})
""", why="average order value"),
    ],
),
dict(
    id="ch-016",
    chain="segments", step=2,
    title="Segments 2/4: tame skew, then scale",
    difficulty="Medium",
    tags=["feature engineering"],
    signature="def solve(rfm: pd.DataFrame) -> pd.DataFrame:",
    statement="""
`rfm` is the table from step 1. `frequency` and `monetary` are heavily right-skewed: replace them with `log(1 + x)`, keep `recency` as is, then **standardize** all three columns (zero mean, unit variance, population std as `StandardScaler` uses). Return a DataFrame with the same index and columns.
""",
    setup=SEGMENTS + """
EXAMPLE = lambda: {"rfm": rfm(0, 40, 10)}
""",
    tests="""
TESTS = [
    lambda: {"rfm": rfm(1, 300, 60)},
    lambda: {"rfm": rfm(2, 3000, 400)},
    Test(lambda: {"rfm": rfm(3, 12, 4)}, "few customers"),
]
""",
    hint1="`np.log1p` on the two skewed columns (via `assign`), then `StandardScaler().fit_transform(...)` wrapped back in a DataFrame (or `.set_output(transform='pandas')`).",
    hint2="X = rfm.assign(frequency=np.log1p(rfm['frequency']), monetary=np.log1p(rfm['monetary']))\npd.DataFrame(StandardScaler().fit_transform(X), index=X.index, columns=X.columns)",
    solution="""
from sklearn.preprocessing import StandardScaler

def solve(rfm):
    X = rfm.assign(frequency=np.log1p(rfm["frequency"]), monetary=np.log1p(rfm["monetary"]))
    return pd.DataFrame(StandardScaler().fit_transform(X), index=X.index, columns=X.columns)
""",
    explanation="""
k-means and PCA are driven by squared distances and variances: unscaled, `monetary` (in currency units) would dominate everything; un-logged, a few whales would. `log1p` is safe at 0. `StandardScaler` uses the population std (ddof=0), unlike pandas' `.std()`.
""",
    docs=["https://numpy.org/doc/stable/reference/generated/numpy.log1p.html",
          "https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html"],
    wrong_solutions=[
        dict(code="""
from sklearn.preprocessing import StandardScaler

def solve(rfm):
    return pd.DataFrame(StandardScaler().fit_transform(rfm), index=rfm.index, columns=rfm.columns)
""", why="no log transform"),
        dict(code="""
def solve(rfm):
    X = rfm.assign(frequency=np.log1p(rfm["frequency"]), monetary=np.log1p(rfm["monetary"]))
    return (X - X.mean()) / X.std()
""", why="pandas std uses ddof=1"),
    ],
),
dict(
    id="ch-017",
    chain="segments", step=3,
    title="Segments 3/4: choose k and cluster",
    difficulty="Hard",
    tags=["clustering"],
    signature="def solve(Xs: pd.DataFrame) -> pd.Series:",
    statement="""
`Xs` is the scaled table from step 2. For k = 2..6 fit `KMeans(n_clusters=k, n_init=10, random_state=0)` and pick the k with the **highest silhouette score** (smallest k on ties). Return that model's cluster labels as an integer Series named `cluster` with the index of `Xs`. (Any relabelling of the clusters is accepted.)
""",
    setup=SEGMENTS + """
EXAMPLE = lambda: {"Xs": scaled(0, 120, 30)}
""",
    tests="""
TESTS = [
    lambda: {"Xs": scaled(1, 300, 60)},
    lambda: {"Xs": scaled(2, 3000, 400)},
    Test(lambda: {"Xs": scaled(3, 60, 12)}, "few customers"),
]

def check(got, exp, inputs):
    if not isinstance(got, pd.Series):
        fail(f"return a Series, got {type(got).__name__}")
    if not got.index.equals(exp.index):
        fail("the index must be the index of Xs")
    if got.nunique() != exp.nunique():
        fail(f"expected {exp.nunique()} clusters (best silhouette), got {got.nunique()}")
    if not same_partition(got.to_numpy(), exp.to_numpy()):
        fail("the clustering differs from KMeans(n_clusters=best k, n_init=10, random_state=0)")
""",
    hint1="Score each k with `silhouette_score(Xs, KMeans(...).fit_predict(Xs))`, take the best with `max(range(2, 7), key=...)`, refit and wrap the labels in a Series.",
    hint2="best = max(range(2, 7), key=lambda k: silhouette_score(Xs, KMeans(n_clusters=k, n_init=10, random_state=0).fit_predict(Xs)))",
    solution="""
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

def solve(Xs):
    fit = lambda k: KMeans(n_clusters=k, n_init=10, random_state=0).fit_predict(Xs)
    best = max(range(2, 7), key=lambda k: silhouette_score(Xs, fit(k)))
    return pd.Series(fit(best), index=Xs.index, name="cluster")
""",
    explanation="""
Inertia always prefers more clusters; the silhouette trades cohesion against separation and peaks at a sensible k. Cluster ids are arbitrary (relabelling them changes nothing), so compare clusterings with partition measures like the adjusted Rand index, never label by label.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.metrics.silhouette_score.html",
          "https://scikit-learn.org/stable/modules/clustering.html#k-means"],
    wrong_solutions=[
        dict(code="""
from sklearn.cluster import KMeans

def solve(Xs):
    return pd.Series(KMeans(n_clusters=6, n_init=10, random_state=0).fit_predict(Xs), index=Xs.index, name="cluster")
""", why="k by lowest inertia (always the largest k)"),
    ],
),
dict(
    id="ch-018",
    chain="segments", step=4,
    title="Segments 4/4: profile the clusters and map them in 2-D",
    difficulty="Medium",
    tags=["dimensionality reduction", "clustering"],
    signature="def solve(rfm: pd.DataFrame, Xs: pd.DataFrame, labels: pd.Series) -> tuple:",
    statement="""
`rfm` (step 1, original units), `Xs` (step 2, scaled) and `labels` (step 3) share the customer index. Return `(profile, coords)`:

* `profile`: one row per cluster id (sorted), with the **mean** `recency`, `frequency`, `monetary` in **original units** plus a `size` column (number of customers);
* `coords`: a 2-D PCA projection of `Xs` (sklearn's `PCA(n_components=2)`), as a DataFrame with the customer index and columns `PC1`, `PC2`. Each component may be sign-flipped.
""",
    setup=SEGMENTS + """
def make(seed, n, n_customers):
    r = rfm(seed, n, n_customers)
    Xs = REF("ch-016", rfm=r)
    return {"rfm": r, "Xs": Xs, "labels": REF("ch-017", Xs=Xs)}

EXAMPLE = lambda: make(0, 120, 30)
""",
    tests="""
TESTS = [
    lambda: make(1, 300, 60),
    lambda: make(2, 3000, 400),
    Test(lambda: make(3, 60, 12), "few customers"),
]

def check(got, exp, inputs):
    if not isinstance(got, (tuple, list)) or len(got) != 2:
        fail("return a tuple (profile, coords)")
    msg = compare(got[0], exp[0], path="profile")
    if msg:
        return msg
    c, e = got[1], exp[1]
    if not isinstance(c, pd.DataFrame) or list(c.columns) != ["PC1", "PC2"]:
        fail("coords must be a DataFrame with columns ['PC1', 'PC2']")
    if not c.index.equals(e.index):
        fail("coords must keep the customer index")
    if not allclose_up_to_sign(c.to_numpy(), e.to_numpy(), axis=0):
        fail("coords are not the 2-D PCA projection of Xs (up to sign)")
""",
    hint1="`rfm.groupby(labels).mean()` plus `labels.value_counts()` for the sizes; `PCA(n_components=2).fit_transform(Xs)` for the map.",
    hint2="profile = rfm.groupby(labels).mean().assign(size=labels.value_counts())\ncoords = pd.DataFrame(PCA(n_components=2).fit_transform(Xs), index=Xs.index, columns=['PC1', 'PC2'])",
    solution="""
from sklearn.decomposition import PCA

def solve(rfm, Xs, labels):
    profile = rfm.groupby(labels).mean().assign(size=labels.value_counts())
    coords = pd.DataFrame(PCA(n_components=2).fit_transform(Xs), index=Xs.index, columns=["PC1", "PC2"])
    return profile, coords
""",
    explanation="""
Describe clusters in the **original** units ("recent, frequent, high spenders"), because scaled means are unreadable to stakeholders. `groupby` accepts any aligned Series as the key. PCA's 2-D map is for visualizing separation (scatter coloured by cluster); its axes are mixtures of features, so check `pca.components_` before naming them.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.PCA.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.groupby.html"],
    wrong_solutions=[
        dict(code="""
from sklearn.decomposition import PCA

def solve(rfm, Xs, labels):
    profile = Xs.groupby(labels).mean().assign(size=labels.value_counts())
    coords = pd.DataFrame(PCA(n_components=2).fit_transform(Xs), index=Xs.index, columns=["PC1", "PC2"])
    return profile, coords
""", why="profile in scaled units"),
        dict(code="""
from sklearn.decomposition import PCA

def solve(rfm, Xs, labels):
    profile = rfm.groupby(labels).mean().assign(size=labels.value_counts())
    coords = pd.DataFrame(PCA(n_components=2).fit_transform(rfm), index=Xs.index, columns=["PC1", "PC2"])
    return profile, coords
""", why="PCA on unscaled data"),
    ],
),
]
