SECTION = "sklearn"

# Shared setup snippets (plain strings, concatenated into problem setups).
CHURN_XY = '''
def churn_xy(seed, n, cols=("tenure", "monthly_charges", "support_calls", "senior")):
    df = D.churn(seed=seed, n=n)
    return df[list(cols)], df["churned"]
'''
CLF = '''
def clf_data(seed, n, k=8, informative=4, weights=None, sep=1.0):
    from sklearn.datasets import make_classification
    X, y = make_classification(n_samples=n, n_features=k, n_informative=informative, n_redundant=0,
                               weights=weights, class_sep=sep, random_state=seed)
    return pd.DataFrame(X, columns=[f"x{i}" for i in range(k)]), pd.Series(y, name="y")

def split(X, y, seed, frac=0.3):
    from sklearn.model_selection import train_test_split
    return train_test_split(X, y, test_size=frac, random_state=seed, stratify=y)
'''

PROBLEMS = [
# ------------------------------------------------------------------ splitting & preprocessing
dict(
    id="sk-001",
    title="Stratified train/test split",
    difficulty="Easy",
    tags=["splitting"],
    signature="def solve(X: pd.DataFrame, y: pd.Series) -> tuple:",
    statement="""
Split `(X, y)` into 75% train and 25% test, **stratified** on `y` so that both parts keep the class balance (positives are rare), reproducibly with `random_state=0`.

Return `(X_train, X_test, y_train, y_test)`. The tests check sizes, that the parts don't overlap, that `X` and `y` rows stay aligned, and the class proportions.
""",
    setup=CHURN_XY + """
def make(seed, n, rare=False):
    X, y = churn_xy(seed, n)
    if rare:
        y = (y & (X["support_calls"] >= 3)).astype(int)
    return {"X": X, "y": y}

EXAMPLE = lambda: make(0, 20)
""",
    tests="""
TESTS = [
    lambda: make(1, 200),
    Test(lambda: make(2, 1000, rare=True), "rare positives"),
    lambda: make(3, 401),
]

def check(got, exp, inputs):
    X, y = inputs["X"], inputs["y"]
    if not isinstance(got, (tuple, list)) or len(got) != 4:
        fail("return a tuple (X_train, X_test, y_train, y_test)")
    Xtr, Xte, ytr, yte = got
    n = len(y)
    n_test = int(np.ceil(0.25 * n))
    if len(Xte) != n_test or len(yte) != n_test:
        fail(f"the test set should have ceil(0.25 * {n}) = {n_test} rows, got {len(Xte)}")
    if len(Xtr) + len(Xte) != n:
        fail("train and test together must contain every row")
    if set(Xtr.index) & set(Xte.index):
        fail("train and test overlap")
    if not (Xtr.index.equals(ytr.index) and Xte.index.equals(yte.index)):
        fail("X and y rows are misaligned")
    for c, cnt in y.value_counts().items():
        want = cnt * n_test / n
        have = int((yte == c).sum())
        if abs(have - want) > 1:
            fail(f"class {c!r} has {have} test rows, expected about {want:.1f}: stratify on y")
""",
    hint1="`train_test_split(X, y, test_size=0.25, stratify=y, random_state=0)`.",
    hint2="from sklearn.model_selection import train_test_split\ntrain_test_split(X, y, test_size=0.25, stratify=y, random_state=0)",
    solution="""
from sklearn.model_selection import train_test_split

def solve(X, y):
    return train_test_split(X, y, test_size=0.25, stratify=y, random_state=0)
""",
    explanation="""
`stratify=y` keeps the class proportions identical in both parts; without it, a rare class can be badly under- or over-represented in a small test set. The return order is `X_train, X_test, y_train, y_test`, a classic source of swapped variables. For time-ordered data, don't shuffle at all: split by date.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.train_test_split.html"],
    wrong_solutions=[
        dict(code="from sklearn.model_selection import train_test_split\n\ndef solve(X, y):\n    return train_test_split(X, y, test_size=0.25, random_state=0)", why="not stratified"),
        dict(code="from sklearn.model_selection import train_test_split\n\ndef solve(X, y):\n    return train_test_split(X, y, test_size=0.75, stratify=y, random_state=0)", why="sizes swapped"),
    ],
),
dict(
    id="sk-002",
    title="Scale with training statistics only",
    difficulty="Easy",
    tags=["preprocessing", "leakage"],
    signature="def solve(X_train: np.ndarray, X_test: np.ndarray) -> tuple:",
    statement="""
Standardize the features to zero mean and unit variance with a `StandardScaler`, using statistics learned from the **training set only**, and apply the same transformation to the test set.

Return a tuple `(X_train_scaled, X_test_scaled, scaler)` where `scaler` is the fitted `StandardScaler`.
""",
    setup="""
def make(seed, n_train, n_test, k):
    rng = np.random.default_rng(seed)
    loc, scale = rng.uniform(-50, 50, k), rng.uniform(0.5, 20, k)
    X_train = rng.normal(loc, scale, size=(n_train, k))
    X_test = rng.normal(loc + scale, scale * 1.5, size=(n_test, k))   # shifted: leakage shows up
    return {"X_train": X_train, "X_test": X_test}

EXAMPLE = lambda: make(0, 6, 3, 2)
""",
    tests="""
TESTS = [
    lambda: make(1, 40, 10, 3),
    lambda: make(2, 300, 100, 8),
    Test(lambda: make(3, 5, 1, 4), "single test row"),
]

def check(got, exp, inputs):
    if not isinstance(got, tuple) or len(got) != 3:
        fail("Return a tuple (X_train_scaled, X_test_scaled, scaler)")
    msg = compare(got[:2], exp[:2], path="(X_train_scaled, X_test_scaled)")
    if msg:
        return msg
    scaler = got[2]
    if type(scaler).__name__ != "StandardScaler":
        fail(f"third element should be the fitted StandardScaler, got {type(scaler).__name__}")
    if not np.allclose(scaler.mean_, inputs["X_train"].mean(axis=0)):
        fail("scaler.mean_ is not the training-set mean: the scaler saw data other than X_train (leakage)")
""",
    hint1="`StandardScaler().fit(X_train)`, then `.transform()` both sets (or `fit_transform` on train only).",
    hint2="scaler = StandardScaler().fit(X_train)\nscaler.transform(X_train), scaler.transform(X_test)",
    solution="""
from sklearn.preprocessing import StandardScaler

def solve(X_train, X_test):
    scaler = StandardScaler().fit(X_train)
    return scaler.transform(X_train), scaler.transform(X_test), scaler
""",
    explanation="""
Fit on the training data only: the test set stands in for future data you have not seen. Fitting on train + test (or refitting on test) leaks test statistics into preprocessing and makes scores optimistic. Inside cross-validation, put the scaler in a `Pipeline` so each fold refits it.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html",
          "https://scikit-learn.org/stable/common_pitfalls.html#data-leakage"],
    wrong_solutions=[
        dict(code="""
from sklearn.preprocessing import StandardScaler
import numpy as np

def solve(X_train, X_test):
    scaler = StandardScaler().fit(np.vstack([X_train, X_test]))
    return scaler.transform(X_train), scaler.transform(X_test), scaler
""", why="fit on all data (leakage)"),
        dict(code="""
from sklearn.preprocessing import StandardScaler

def solve(X_train, X_test):
    scaler = StandardScaler()
    Xtr = scaler.fit_transform(X_train)
    Xte = scaler.fit_transform(X_test)
    return Xtr, Xte, scaler
""", why="refit on the test set"),
    ],
),
dict(
    id="sk-003",
    title="Impute with the training median",
    difficulty="Easy",
    tags=["preprocessing", "leakage"],
    signature="def solve(X_train: np.ndarray, X_test: np.ndarray) -> tuple:",
    statement="""
Both arrays contain NaNs. Fill them with each column's **median computed on the training set** using a `SimpleImputer`. Return `(X_train_filled, X_test_filled, imputer)` with the fitted imputer.
""",
    setup="""
def make(seed, n_train, n_test, k, holes=0.15):
    rng = np.random.default_rng(seed)
    A = rng.lognormal(3, 1, (n_train + n_test, k))
    A[rng.random(A.shape) < holes] = np.nan
    A[0] = rng.lognormal(3, 1, k)
    A[n_train] = A[n_train] * 50
    return {"X_train": A[:n_train], "X_test": A[n_train:]}

EXAMPLE = lambda: make(0, 6, 3, 2, holes=0.3)
""",
    tests="""
TESTS = [
    lambda: make(1, 50, 20, 3),
    lambda: make(2, 800, 200, 6),
    Test(lambda: make(3, 3, 1, 2, holes=0.0), "nothing missing"),
]

def check(got, exp, inputs):
    if not isinstance(got, tuple) or len(got) != 3:
        fail("return a tuple (X_train_filled, X_test_filled, imputer)")
    msg = compare(got[:2], exp[:2], path="(X_train_filled, X_test_filled)")
    if msg:
        return msg
    imp = got[2]
    if type(imp).__name__ != "SimpleImputer":
        fail(f"third element should be the fitted SimpleImputer, got {type(imp).__name__}")
    if not np.allclose(imp.statistics_, np.nanmedian(inputs["X_train"], axis=0)):
        fail("imputer.statistics_ are not the training medians (fitted on other data?)")
""",
    hint1="`SimpleImputer(strategy='median').fit(X_train)` and transform both.",
    hint2="imp = SimpleImputer(strategy='median').fit(X_train)\nimp.transform(X_train), imp.transform(X_test), imp",
    solution="""
from sklearn.impute import SimpleImputer

def solve(X_train, X_test):
    imp = SimpleImputer(strategy="median").fit(X_train)
    return imp.transform(X_train), imp.transform(X_test), imp
""",
    explanation="""
Imputation values are learned parameters, so fit them on train only (`statistics_` stores them). The default strategy is `'mean'`, which is sensitive to skew and outliers. Add `add_indicator=True` to keep "was missing" flags, which are often predictive themselves.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.impute.SimpleImputer.html"],
    wrong_solutions=[
        dict(code="from sklearn.impute import SimpleImputer\n\ndef solve(X_train, X_test):\n    imp = SimpleImputer().fit(X_train)\n    return imp.transform(X_train), imp.transform(X_test), imp", why="mean strategy"),
        dict(code="from sklearn.impute import SimpleImputer\nimport numpy as np\n\ndef solve(X_train, X_test):\n    imp = SimpleImputer(strategy='median').fit(np.vstack([X_train, X_test]))\n    return imp.transform(X_train), imp.transform(X_test), imp", why="fitted on all data"),
    ],
),
dict(
    id="sk-004",
    title="One-hot encoding that survives unseen categories",
    difficulty="Medium",
    tags=["encoding"],
    signature="def solve(train: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:",
    statement="""
`train` and `test` have categorical columns `contract` and `payment_method`; `test` contains a payment method never seen in training. Fit a `OneHotEncoder` on `train[['contract', 'payment_method']]` that encodes unseen categories as **all zeros** (instead of raising), and return the encoded **test** columns as a dense DataFrame whose columns are the encoder's output feature names (default index).
""",
    setup="""
def make(seed, n_train, n_test):
    tr = D.churn(seed=seed, n=n_train)[["contract", "payment_method"]]
    te = D.churn(seed=seed + 100, n=n_test)[["contract", "payment_method"]].reset_index(drop=True)
    te.loc[te.index[::4], "payment_method"] = "Crypto"
    return {"train": tr, "test": te}

EXAMPLE = lambda: make(0, 20, 5)
""",
    tests="""
TESTS = [
    lambda: make(1, 100, 30),
    lambda: make(2, 2000, 500),
    Test(lambda: make(3, 50, 1), "single unseen row"),
]
""",
    hint1="`OneHotEncoder(handle_unknown='ignore', sparse_output=False)`, then `pd.DataFrame(enc.transform(...), columns=enc.get_feature_names_out())`.",
    hint2="cols = ['contract', 'payment_method']\nenc = OneHotEncoder(handle_unknown='ignore', sparse_output=False).fit(train[cols])\npd.DataFrame(enc.transform(test[cols]), columns=enc.get_feature_names_out())",
    solution="""
from sklearn.preprocessing import OneHotEncoder

def solve(train, test):
    cols = ["contract", "payment_method"]
    enc = OneHotEncoder(handle_unknown="ignore", sparse_output=False).fit(train[cols])
    return pd.DataFrame(enc.transform(test[cols]), columns=enc.get_feature_names_out())
""",
    explanation="""
The encoder memorizes the training categories (`categories_`), so train and test always get the same columns, which `pd.get_dummies` can't guarantee. `handle_unknown='ignore'` maps unseen values to all zeros. `'infrequent_if_exist'` with `min_frequency=` also groups rare levels. `sparse_output=False` returns a dense array.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.OneHotEncoder.html"],
    wrong_solutions=[
        dict(code="""
from sklearn.preprocessing import OneHotEncoder

def solve(train, test):
    cols = ["contract", "payment_method"]
    enc = OneHotEncoder(sparse_output=False).fit(train[cols])
    return pd.DataFrame(enc.transform(test[cols]), columns=enc.get_feature_names_out())
""", why="unknown category raises"),
        dict(code="def solve(train, test):\n    return pd.get_dummies(test[['contract', 'payment_method']], dtype=float)", why="columns depend on the test data"),
    ],
),
dict(
    id="sk-005",
    title="Ordinal encoding with an explicit order",
    difficulty="Easy",
    tags=["encoding"],
    signature="def solve(hr: pd.DataFrame) -> np.ndarray:",
    statement="""
Encode `level` as numbers that respect the order `Junior < Mid < Senior < Lead` (0, 1, 2, 3) using an `OrdinalEncoder`, and return the encoded column as a 1-D float array.
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
    hint1="`OrdinalEncoder(categories=[[...]])`: one list per column; transform a 2-D selection `hr[['level']]` and `.ravel()`.",
    hint2="OrdinalEncoder(categories=[['Junior', 'Mid', 'Senior', 'Lead']]).fit_transform(hr[['level']]).ravel()",
    solution="""
from sklearn.preprocessing import OrdinalEncoder

def solve(hr):
    enc = OrdinalEncoder(categories=[["Junior", "Mid", "Senior", "Lead"]])
    return enc.fit_transform(hr[["level"]]).ravel()
""",
    explanation="""
Without `categories=`, the order is alphabetical (Junior, Lead, Mid, Senior), which scrambles the ranking a linear model would use. Transformers expect 2-D input, hence `hr[['level']]`, not `hr['level']`. Use ordinal codes for truly ordered features (or for tree models); otherwise one-hot.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.OrdinalEncoder.html"],
    wrong_solutions=[
        dict(code="from sklearn.preprocessing import OrdinalEncoder\n\ndef solve(hr):\n    return OrdinalEncoder().fit_transform(hr[['level']]).ravel()", why="alphabetical order"),
    ],
),
dict(
    id="sk-006",
    title="Preprocess columns by dtype",
    difficulty="Hard",
    tags=["preprocessing", "pipelines"],
    signature="def solve(X_train: pd.DataFrame, X_test: pd.DataFrame) -> pd.DataFrame:",
    statement="""
Build a `ColumnTransformer` with two transformers selected **by dtype** (not by listing column names):

* `"num"`: `StandardScaler` on every numeric column;
* `"cat"`: `OneHotEncoder(handle_unknown="ignore", sparse_output=False)` on every other column.

Fit it on `X_train`, transform `X_test`, and return the result as a **pandas DataFrame** (configure the transformer's pandas output), whose columns are the generated names such as `num__tenure`.
""",
    setup="""
def make(seed, n_train, n_test):
    cols = ["tenure", "contract", "internet", "monthly_charges", "support_calls", "payment_method"]
    return {"X_train": D.churn(seed=seed, n=n_train)[cols], "X_test": D.churn(seed=seed + 50, n=n_test)[cols]}

EXAMPLE = lambda: make(0, 30, 4)
""",
    tests="""
TESTS = [
    lambda: make(1, 200, 50),
    lambda: make(2, 2000, 500),
    Test(lambda: make(3, 40, 1), "single test row"),
]
""",
    hint1="`ColumnTransformer([(name, transformer, make_column_selector(dtype_include='number')), ...])` and `.set_output(transform='pandas')`.",
    hint2="ColumnTransformer([\n    ('num', StandardScaler(), make_column_selector(dtype_include='number')),\n    ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), make_column_selector(dtype_exclude='number')),\n]).set_output(transform='pandas')",
    solution="""
from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.preprocessing import OneHotEncoder, StandardScaler

def solve(X_train, X_test):
    ct = ColumnTransformer([
        ("num", StandardScaler(), make_column_selector(dtype_include="number")),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), make_column_selector(dtype_exclude="number")),
    ]).set_output(transform="pandas")
    return ct.fit(X_train).transform(X_test)
""",
    explanation="""
Dtype selectors keep the pipeline correct when columns are added. Select categoricals with `dtype_exclude='number'`. `dtype_include=object` misses pandas 3's new `str` dtype (it currently still matches, with a deprecation warning). `set_output(transform='pandas')` keeps column names and the index all the way through.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.compose.ColumnTransformer.html",
          "https://scikit-learn.org/stable/modules/generated/sklearn.compose.make_column_selector.html",
          "https://scikit-learn.org/stable/auto_examples/miscellaneous/plot_set_output.html"],
    wrong_solutions=[
        dict(code="""
from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.preprocessing import OneHotEncoder, StandardScaler

def solve(X_train, X_test):
    ct = ColumnTransformer([
        ("num", StandardScaler(), make_column_selector(dtype_include="number")),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), make_column_selector(dtype_exclude="number")),
    ]).set_output(transform="pandas")
    return ct.fit_transform(X_test)
""", why="fitted on the test set"),
        dict(code="""
from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.preprocessing import StandardScaler

def solve(X_train, X_test):
    ct = ColumnTransformer([("num", StandardScaler(), make_column_selector(dtype_include="number"))]).set_output(transform="pandas")
    return ct.fit(X_train).transform(X_test)
""", why="categorical columns dropped"),
    ],
),
dict(
    id="sk-007",
    title="Named pipeline steps and a nested parameter",
    difficulty="Medium",
    tags=["pipelines"],
    signature="def solve(X: pd.DataFrame, y: pd.Series):",
    statement="""
Build a `Pipeline` with two steps named `"scale"` (`StandardScaler`) and `"clf"` (`LogisticRegression(max_iter=1000)`). Set the classifier's `C` to `0.1` **through the pipeline** (the `step__param` naming), fit it on `(X, y)` and return the **fitted pipeline**.
""",
    setup=CLF + """
EXAMPLE = lambda: dict(zip(["X", "y"], clf_data(0, 60)))
""",
    tests="""
TESTS = [
    lambda: dict(zip(["X", "y"], clf_data(1, 200))),
    lambda: dict(zip(["X", "y"], clf_data(2, 1000, k=12))),
    Test(lambda: dict(zip(["X", "y"], clf_data(3, 30, k=3, informative=2))), "small"),
]

def check(got, exp, inputs):
    from sklearn.pipeline import Pipeline
    if not isinstance(got, Pipeline):
        fail(f"return the fitted Pipeline, got {type(got).__name__}")
    names = [n for n, _ in got.steps]
    if names != ["scale", "clf"]:
        fail(f"step names should be ['scale', 'clf'], got {names}")
    kinds = [type(s).__name__ for _, s in got.steps]
    if kinds != ["StandardScaler", "LogisticRegression"]:
        fail(f"steps should be StandardScaler then LogisticRegression, got {kinds}")
    if got.get_params()["clf__C"] != 0.1:
        fail(f"clf__C should be 0.1, got {got.get_params()['clf__C']}")
    try:
        p = got.predict_proba(inputs["X"])
    except Exception as e:
        fail(f"the pipeline can't predict ({type(e).__name__}): did you fit it?")
    if not np.allclose(p, exp.predict_proba(inputs["X"]), atol=1e-6):
        fail("predictions differ from Pipeline([scale, clf(C=0.1, max_iter=1000)]) fitted on (X, y)")
""",
    hint1="`Pipeline([('scale', ...), ('clf', ...)])`, then `pipe.set_params(clf__C=0.1)` and `.fit(X, y)`.",
    hint2="pipe = Pipeline([('scale', StandardScaler()), ('clf', LogisticRegression(max_iter=1000))])\npipe.set_params(clf__C=0.1).fit(X, y)",
    solution="""
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

def solve(X, y):
    pipe = Pipeline([("scale", StandardScaler()), ("clf", LogisticRegression(max_iter=1000))])
    return pipe.set_params(clf__C=0.1).fit(X, y)
""",
    explanation="""
`<step>__<param>` reaches into nested estimators. It's the same naming you use in `GridSearchCV` grids (`{'clf__C': [...]}`) and in `get_params()`. `make_pipeline` auto-names steps after the class (`'logisticregression'`); explicit names are shorter to type in grids. `fit` returns the estimator itself, so it chains.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.pipeline.Pipeline.html",
          "https://scikit-learn.org/stable/modules/compose.html#pipeline"],
    wrong_solutions=[
        dict(code="""
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

def solve(X, y):
    return make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=1000)).fit(X, y)
""", why="auto-generated step names"),
        dict(code="""
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

def solve(X, y):
    return Pipeline([("scale", StandardScaler()), ("clf", LogisticRegression(max_iter=1000))]).fit(X, y)
""", why="C left at 1.0"),
    ],
),
dict(
    id="sk-008",
    title="Logistic-regression coefficients by feature name",
    difficulty="Hard",
    tags=["model inspection", "pipelines"],
    signature="def solve(X: pd.DataFrame, y: pd.Series) -> pd.Series:",
    statement="""
Fit this pipeline on `(X, y)`:

1. a `ColumnTransformer` with `"num"`: `StandardScaler` on the numeric columns and `"cat"`: `OneHotEncoder(drop="first")` on the others (select by dtype);
2. `LogisticRegression(max_iter=1000)`.

Return the fitted coefficients as a Series indexed by the **transformed feature names** (as the preprocessing step names them, e.g. `num__tenure`, `cat__contract_One year`), sorted by **absolute** value, largest first.
""",
    setup="""
def make(seed, n):
    df = D.churn(seed=seed, n=n)
    X = df[["tenure", "monthly_charges", "support_calls", "contract", "internet", "payment_method"]]
    return {"X": X, "y": df["churned"]}

EXAMPLE = lambda: make(0, 200)
""",
    tests="""
TESTS = [
    lambda: make(1, 500),
    lambda: make(2, 3000),
    Test(lambda: make(3, 120), "small"),
]
""",
    compare=dict(rtol=1e-4, atol=1e-6),
    hint1="After fitting, `pipe[:-1].get_feature_names_out()` names the model's inputs and `pipe[-1].coef_[0]` holds the weights; sort with `reindex(s.abs().sort_values(ascending=False).index)`.",
    hint2="coef = pd.Series(pipe[-1].coef_[0], index=pipe[:-1].get_feature_names_out())\ncoef.reindex(coef.abs().sort_values(ascending=False).index)",
    solution="""
from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

def solve(X, y):
    pre = ColumnTransformer([("num", StandardScaler(), make_column_selector(dtype_include="number")),
                             ("cat", OneHotEncoder(drop="first"), make_column_selector(dtype_exclude="number"))])
    pipe = make_pipeline(pre, LogisticRegression(max_iter=1000)).fit(X, y)
    coef = pd.Series(pipe[-1].coef_[0], index=pipe[:-1].get_feature_names_out())
    return coef.reindex(coef.abs().sort_values(ascending=False).index)
""",
    explanation="""
After one-hot encoding, the model's inputs no longer match `X.columns`, so take the names from the fitted preprocessor (`get_feature_names_out`). Slicing a pipeline (`pipe[:-1]`) gives the preprocessing part. On standardized features, coefficient magnitudes are comparable (log-odds per standard deviation). One-hot coefficients are relative to the dropped level.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.compose.ColumnTransformer.html#sklearn.compose.ColumnTransformer.get_feature_names_out",
          "https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html"],
    wrong_solutions=[
        dict(code="""
from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

def solve(X, y):
    pre = ColumnTransformer([("num", StandardScaler(), make_column_selector(dtype_include="number")),
                             ("cat", OneHotEncoder(drop="first"), make_column_selector(dtype_exclude="number"))])
    pipe = make_pipeline(pre, LogisticRegression(max_iter=1000)).fit(X, y)
    return pd.Series(pipe[-1].coef_[0], index=pipe[:-1].get_feature_names_out()).sort_values(ascending=False)
""", why="sorted by signed value"),
        dict(code="""
from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder

def solve(X, y):
    pre = ColumnTransformer([("num", "passthrough", make_column_selector(dtype_include="number")),
                             ("cat", OneHotEncoder(drop="first"), make_column_selector(dtype_exclude="number"))])
    pipe = make_pipeline(pre, LogisticRegression(max_iter=1000)).fit(X, y)
    coef = pd.Series(pipe[-1].coef_[0], index=pipe[:-1].get_feature_names_out())
    return coef.reindex(coef.abs().sort_values(ascending=False).index)
""", why="numeric features not scaled"),
    ],
),
# ------------------------------------------------------------------ models
dict(
    id="sk-009",
    title="The baseline to beat",
    difficulty="Easy",
    tags=["baselines"],
    signature="def solve(X_train, y_train, X_test, y_test) -> float:",
    statement="""
Before any model, measure a baseline: return the **test accuracy** of a classifier that always predicts the **most frequent class of the training labels**.
""",
    setup=CLF + """
def make(seed, n, w):
    X, y = clf_data(seed, n, weights=[w])
    Xtr, Xte, ytr, yte = split(X, y, seed)
    return {"X_train": Xtr, "y_train": ytr, "X_test": Xte, "y_test": yte}

EXAMPLE = lambda: make(0, 50, 0.7)
""",
    tests="""
TESTS = [
    lambda: make(1, 200, 0.8),
    lambda: make(2, 2000, 0.6),
    Test(lambda: make(3, 40, 0.35), "majority class is 1"),
    Test(lambda: {"X_train": np.zeros((10, 2)), "y_train": np.array([0] * 7 + [1] * 3),
                  "X_test": np.zeros((5, 2)), "y_test": np.array([1, 1, 1, 0, 1])}, "test majority differs"),
]
""",
    hint1="`DummyClassifier(strategy='most_frequent').fit(X_train, y_train).score(X_test, y_test)`.",
    hint2="DummyClassifier(strategy='most_frequent').fit(X_train, y_train).score(X_test, y_test)",
    solution="""
from sklearn.dummy import DummyClassifier

def solve(X_train, y_train, X_test, y_test):
    return DummyClassifier(strategy="most_frequent").fit(X_train, y_train).score(X_test, y_test)
""",
    explanation="""
With 80% negatives, "always no" scores 80% accuracy. Report every model against this number, or use a metric that isn't fooled by imbalance (ROC AUC, balanced accuracy, F1). `DummyRegressor(strategy='mean')` is the regression analogue (R² = 0 by construction on train).
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.dummy.DummyClassifier.html"],
    wrong_solutions=[
        dict(code="from sklearn.dummy import DummyClassifier\n\ndef solve(X_train, y_train, X_test, y_test):\n    return DummyClassifier(strategy='most_frequent').fit(X_test, y_test).score(X_test, y_test)", why="fitted on test labels"),
        dict(code="from sklearn.dummy import DummyClassifier\n\ndef solve(X_train, y_train, X_test, y_test):\n    return DummyClassifier(strategy='stratified', random_state=0).fit(X_train, y_train).score(X_test, y_test)", why="random baseline"),
    ],
),
dict(
    id="sk-010",
    title="Linear regression coefficients with the intercept",
    difficulty="Easy",
    tags=["linear models"],
    signature="def solve(X: pd.DataFrame, y: pd.Series) -> pd.Series:",
    statement="""
Fit a `LinearRegression` of `y` on `X` and return its coefficients as a Series indexed by the feature names, followed by one more entry labelled `"intercept"`.
""",
    setup="""
def make(seed, n):
    hr = D.hr(seed=seed, n=n).dropna(subset=["salary"])
    X = hr[["years_experience", "performance"]].assign(remote=hr["remote"].astype(int))
    return {"X": X, "y": hr["salary"]}

EXAMPLE = lambda: make(0, 20)
""",
    tests="""
TESTS = [
    lambda: make(1, 100),
    lambda: make(2, 3000),
    Test(lambda: make(3, 8), "few rows"),
]
""",
    compare=dict(rtol=1e-6, atol=1e-6),
    hint1="After `fit`, use `model.coef_` (one per column) and `model.intercept_`.",
    hint2="m = LinearRegression().fit(X, y)\npd.concat([pd.Series(m.coef_, index=X.columns), pd.Series({'intercept': m.intercept_})])",
    solution="""
from sklearn.linear_model import LinearRegression

def solve(X, y):
    m = LinearRegression().fit(X, y)
    return pd.concat([pd.Series(m.coef_, index=X.columns), pd.Series({"intercept": m.intercept_})])
""",
    explanation="""
Fitted attributes end with an underscore (`coef_`, `intercept_`, `feature_names_in_`). Each coefficient is the change in `y` per unit of that feature, holding the others fixed, so it depends on the units: compare magnitudes only after standardizing. For p-values and confidence intervals use statsmodels.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LinearRegression.html"],
    wrong_solutions=[
        dict(code="from sklearn.linear_model import LinearRegression\n\ndef solve(X, y):\n    m = LinearRegression().fit(X, y)\n    return pd.Series(m.coef_, index=X.columns)", why="no intercept entry"),
        dict(code="from sklearn.linear_model import LinearRegression\n\ndef solve(X, y):\n    m = LinearRegression(fit_intercept=False).fit(X, y)\n    return pd.concat([pd.Series(m.coef_, index=X.columns), pd.Series({'intercept': m.intercept_})])", why="no intercept fitted"),
    ],
),
dict(
    id="sk-011",
    title="Which features does the Lasso drop?",
    difficulty="Medium",
    tags=["linear models"],
    signature="def solve(X: pd.DataFrame, y: pd.Series, alpha: float) -> list:",
    statement="""
Standardize the features and fit a `Lasso(alpha=alpha)` (in a pipeline). Return the list of feature names whose coefficient is **exactly zero**, in column order.
""",
    setup="""
def diabetes(alpha):
    from sklearn.datasets import load_diabetes
    d = load_diabetes(as_frame=True)
    return {"X": d.data, "y": d.target, "alpha": alpha}

def make(seed, n, k, informative, alpha):
    from sklearn.datasets import make_regression
    X, y = make_regression(n_samples=n, n_features=k, n_informative=informative, noise=20, random_state=seed)
    X = X * np.random.default_rng(seed).uniform(0.1, 50, k)
    return {"X": pd.DataFrame(X, columns=[f"f{i}" for i in range(k)]), "y": pd.Series(y, name="y"), "alpha": alpha}

EXAMPLE = lambda: make(0, 100, 6, 2, 5.0)
""",
    tests="""
TESTS = [
    lambda: make(1, 200, 10, 4, 3.0),
    lambda: make(2, 1000, 25, 5, 8.0),
    Test(lambda: make(3, 80, 4, 4, 0.5), "everything informative"),
    Test(lambda: diabetes(1.0), "sklearn's diabetes"),
]
""",
    hint1="`make_pipeline(StandardScaler(), Lasso(alpha=alpha))`, then the last step's `coef_ == 0`.",
    hint2="pipe = make_pipeline(StandardScaler(), Lasso(alpha=alpha)).fit(X, y)\nlist(X.columns[pipe[-1].coef_ == 0])",
    solution="""
from sklearn.linear_model import Lasso
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

def solve(X, y, alpha):
    pipe = make_pipeline(StandardScaler(), Lasso(alpha=alpha)).fit(X, y)
    return list(X.columns[pipe[-1].coef_ == 0])
""",
    explanation="""
The L1 penalty drives some coefficients exactly to zero (feature selection); Ridge's L2 penalty only shrinks them. Penalties are scale-dependent, so standardize first, or features with large units get penalized less. Choose `alpha` by cross-validation (`LassoCV`).
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Lasso.html",
          "https://scikit-learn.org/stable/modules/linear_model.html#lasso"],
    wrong_solutions=[
        dict(code="from sklearn.linear_model import Lasso\n\ndef solve(X, y, alpha):\n    m = Lasso(alpha=alpha).fit(X, y)\n    return list(X.columns[m.coef_ == 0])", why="not standardized"),
        dict(code="from sklearn.linear_model import Ridge\nfrom sklearn.pipeline import make_pipeline\nfrom sklearn.preprocessing import StandardScaler\n\ndef solve(X, y, alpha):\n    pipe = make_pipeline(StandardScaler(), Ridge(alpha=alpha)).fit(X, y)\n    return list(X.columns[pipe[-1].coef_ == 0])", why="Ridge never zeroes coefficients"),
    ],
),
dict(
    id="sk-012",
    title="Probability of the positive class",
    difficulty="Easy",
    tags=["classification"],
    signature="def solve(X_train, y_train, X_test) -> np.ndarray:",
    statement="""
Fit `LogisticRegression(max_iter=1000)` on the training data and return the predicted **probability of class 1** for each row of `X_test`, as a 1-D array.
""",
    setup=CLF + """
def make(seed, n):
    X, y = clf_data(seed, n)
    Xtr, Xte, ytr, yte = split(X, y, seed)
    return {"X_train": Xtr, "y_train": ytr, "X_test": Xte}

EXAMPLE = lambda: make(0, 40)
""",
    tests="""
TESTS = [
    lambda: make(1, 200),
    lambda: make(2, 3000),
    Test(lambda: make(3, 20), "small"),
]
""",
    compare=dict(rtol=1e-5, atol=1e-7),
    hint1="`model.predict_proba(X)` returns one column per class, ordered like `model.classes_`; take column 1.",
    hint2="LogisticRegression(max_iter=1000).fit(X_train, y_train).predict_proba(X_test)[:, 1]",
    solution="""
from sklearn.linear_model import LogisticRegression

def solve(X_train, y_train, X_test):
    return LogisticRegression(max_iter=1000).fit(X_train, y_train).predict_proba(X_test)[:, 1]
""",
    explanation="""
`predict` thresholds at 0.5; `predict_proba` gives the scores you need for ROC AUC, log loss, calibration and custom thresholds. Columns follow `classes_` (sorted labels), so check it when labels aren't 0/1. Raise `max_iter` if you see a ConvergenceWarning, and scale features.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html#sklearn.linear_model.LogisticRegression.predict_proba"],
    wrong_solutions=[
        dict(code="from sklearn.linear_model import LogisticRegression\n\ndef solve(X_train, y_train, X_test):\n    return LogisticRegression(max_iter=1000).fit(X_train, y_train).predict(X_test)", why="hard labels"),
        dict(code="from sklearn.linear_model import LogisticRegression\n\ndef solve(X_train, y_train, X_test):\n    return LogisticRegression(max_iter=1000).fit(X_train, y_train).predict_proba(X_test)[:, 0]", why="probability of class 0"),
    ],
),
dict(
    id="sk-013",
    title="Pick a threshold for a target precision",
    difficulty="Hard",
    tags=["thresholds", "metrics"],
    signature="def solve(y_true: np.ndarray, scores: np.ndarray, target: float) -> float:",
    statement="""
A fraud team will only review alerts if at least `target` of them are real. Among the thresholds of the precision-recall curve, choose the one that gives **precision >= target** with the **highest recall**; if several thresholds tie on that recall, return the **smallest**. Return it as a float.
""",
    setup="""
def make(seed, n, pos=0.2, signal=1.5, target=0.8):
    rng = np.random.default_rng(seed)
    y = (rng.random(n) < pos).astype(int)
    return {"y_true": y, "scores": np.round(signal * y + rng.normal(0, 1, n), 3), "target": target}

EXAMPLE = lambda: make(0, 40, target=0.75)
""",
    tests="""
TESTS = [
    lambda: make(1, 300),
    lambda: make(2, 5000, pos=0.05, signal=2.5, target=0.6),
    Test(lambda: make(3, 200, signal=4.0, target=0.95), "very separable"),
]
""",
    hint1="`p, r, t = precision_recall_curve(y, s)`: `p` and `r` have one more element than `t`, so compare with `p[:-1]` and `r[:-1]`.",
    hint2="p, r, t = precision_recall_curve(y_true, scores)\nok = p[:-1] >= target\nbest = r[:-1][ok].max()\nt[ok & (r[:-1] == best)].min()",
    solution="""
from sklearn.metrics import precision_recall_curve

def solve(y_true, scores, target):
    p, r, t = precision_recall_curve(y_true, scores)
    ok = p[:-1] >= target
    best = r[:-1][ok].max()
    return float(t[ok & (r[:-1] == best)].min())
""",
    explanation="""
`precision_recall_curve` returns one more precision/recall value than thresholds: the final point (precision 1, recall 0) has no threshold. Drop it before indexing. Business constraints ("at least 80% precision") are usually met by moving the threshold, not by changing the model, and you should choose it on validation data, never on test.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_recall_curve.html",
          "https://scikit-learn.org/stable/modules/classification_threshold.html"],
    wrong_solutions=[
        dict(code="""
from sklearn.metrics import precision_recall_curve

def solve(y_true, scores, target):
    p, r, t = precision_recall_curve(y_true, scores)
    ok = p[1:] >= target
    best = r[1:][ok].max()
    return float(t[ok & (r[1:] == best)].min())
""", why="off by one"),
        dict(code="""
from sklearn.metrics import precision_recall_curve

def solve(y_true, scores, target):
    p, r, t = precision_recall_curve(y_true, scores)
    return float(t[p[:-1] >= target].max())
""", why="highest threshold, lowest recall"),
    ],
),
# ------------------------------------------------------------------ metrics
dict(
    id="sk-014",
    title="Precision, recall and F1",
    difficulty="Easy",
    tags=["metrics"],
    signature="def solve(y_true: np.ndarray, y_pred: np.ndarray) -> dict:",
    statement="""
For binary labels (positive class `1`), return a dict with keys `"accuracy"`, `"precision"`, `"recall"` and `"f1"` (floats).
""",
    setup="""
def make(seed, n, pos=0.3, acc=0.8):
    rng = np.random.default_rng(seed)
    y = (rng.random(n) < pos).astype(int)
    pred = np.where(rng.random(n) < acc, y, 1 - y)
    return {"y_true": y, "y_pred": pred}

EXAMPLE = lambda: {"y_true": np.array([1, 0, 1, 1, 0, 0, 1, 0]), "y_pred": np.array([1, 0, 0, 1, 1, 0, 1, 0])}
""",
    tests="""
TESTS = [
    lambda: make(1, 50),
    lambda: make(2, 5000, pos=0.05),
    Test(lambda: make(3, 30, acc=0.5), "noisy"),
]
""",
    hint1="`accuracy_score`, `precision_score`, `recall_score`, `f1_score`, all called as `(y_true, y_pred)`.",
    hint2="{'accuracy': accuracy_score(y_true, y_pred), 'precision': precision_score(y_true, y_pred),\n 'recall': recall_score(y_true, y_pred), 'f1': f1_score(y_true, y_pred)}",
    solution="""
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

def solve(y_true, y_pred):
    return {"accuracy": accuracy_score(y_true, y_pred), "precision": precision_score(y_true, y_pred),
            "recall": recall_score(y_true, y_pred), "f1": f1_score(y_true, y_pred)}
""",
    explanation="""
Precision = TP / (TP + FP): how many alerts are right. Recall = TP / (TP + FN): how many positives you catch. F1 is their harmonic mean. Argument order matters: `(y_true, y_pred)`, and swapping them swaps precision and recall. For multiclass, choose `average=` ('macro', 'weighted', 'micro').
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_score.html",
          "https://scikit-learn.org/stable/modules/model_evaluation.html#precision-recall-f-measure-metrics"],
    wrong_solutions=[
        dict(code="""
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

def solve(y_true, y_pred):
    return {"accuracy": accuracy_score(y_true, y_pred), "precision": precision_score(y_pred, y_true),
            "recall": recall_score(y_pred, y_true), "f1": f1_score(y_true, y_pred)}
""", why="arguments swapped"),
        dict(code="""
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

def solve(y_true, y_pred):
    return {"accuracy": accuracy_score(y_true, y_pred), "precision": precision_score(y_true, y_pred),
            "recall": recall_score(y_true, y_pred), "f1": f1_score(y_true, y_pred, average="macro")}
""", why="macro F1"),
    ],
),
dict(
    id="sk-015",
    title="Classification report as a table",
    difficulty="Easy",
    tags=["metrics"],
    signature="def solve(y_true: np.ndarray, y_pred: np.ndarray) -> pd.DataFrame:",
    statement="""
Return scikit-learn's classification report as a DataFrame: one row per class (as strings, e.g. `'cat'`) followed by the rows `'accuracy'`, `'macro avg'` and `'weighted avg'`, with columns `precision`, `recall`, `f1-score`, `support`. (In the `accuracy` row every column holds the accuracy, as scikit-learn returns it.)
""",
    setup="""
def make(seed, n, classes=("cat", "dog", "fox")):
    rng = np.random.default_rng(seed)
    y = rng.choice(list(classes), n)
    return {"y_true": y, "y_pred": np.where(rng.random(n) < 0.7, y, rng.choice(list(classes), n))}

EXAMPLE = lambda: make(0, 30)
""",
    tests="""
TESTS = [
    lambda: make(1, 100),
    lambda: make(2, 3000, ("a", "b", "c", "d")),
    Test(lambda: make(3, 20, ("no", "yes")), "binary"),
]
""",
    hint1="`classification_report(y_true, y_pred, output_dict=True)` returns a nested dict; build a DataFrame and transpose it.",
    hint2="pd.DataFrame(classification_report(y_true, y_pred, output_dict=True)).T",
    solution="""
from sklearn.metrics import classification_report

def solve(y_true, y_pred):
    return pd.DataFrame(classification_report(y_true, y_pred, output_dict=True)).T
""",
    explanation="""
`output_dict=True` makes the report machine-readable, which is handy for logging and comparing models. Macro average weights classes equally (sensitive to rare-class performance); weighted average weights by support. `zero_division=0` silences warnings when a class is never predicted.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.metrics.classification_report.html"],
    wrong_solutions=[
        dict(code="from sklearn.metrics import classification_report\n\ndef solve(y_true, y_pred):\n    return pd.DataFrame(classification_report(y_true, y_pred, output_dict=True))", why="not transposed"),
    ],
),
dict(
    id="sk-016",
    title="ROC AUC and log loss from probabilities",
    difficulty="Easy",
    tags=["metrics"],
    signature="def solve(y_true: np.ndarray, proba: np.ndarray) -> tuple:",
    statement="""
Given true binary labels and the predicted probabilities of class 1, return `(roc_auc, log_loss)` as floats.
""",
    setup="""
def make(seed, n, signal=1.5):
    rng = np.random.default_rng(seed)
    y = (rng.random(n) < 0.3).astype(int)
    z = signal * (2 * y - 1) + rng.normal(0, 1.5, n)
    return {"y_true": y, "proba": 1 / (1 + np.exp(-z))}

EXAMPLE = lambda: make(0, 20)
""",
    tests="""
TESTS = [
    lambda: make(1, 200),
    lambda: make(2, 5000, signal=0.5),
    Test(lambda: make(3, 12, signal=3.0), "small"),
]
""",
    hint1="`roc_auc_score(y_true, proba)` and `log_loss(y_true, proba)`.",
    hint2="roc_auc_score(y_true, proba), log_loss(y_true, proba)",
    solution="""
from sklearn.metrics import log_loss, roc_auc_score

def solve(y_true, proba):
    return float(roc_auc_score(y_true, proba)), float(log_loss(y_true, proba))
""",
    explanation="""
Both need probabilities, not hard predictions. AUC only cares about the **ranking** (the probability that a random positive scores above a random negative); log loss also punishes miscalibrated, overconfident probabilities. Report both: a model can rank well and still be badly calibrated.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.metrics.roc_auc_score.html",
          "https://scikit-learn.org/stable/modules/generated/sklearn.metrics.log_loss.html"],
    wrong_solutions=[
        dict(code="from sklearn.metrics import log_loss, roc_auc_score\n\ndef solve(y_true, proba):\n    pred = (proba > 0.5).astype(int)\n    return roc_auc_score(y_true, pred), log_loss(y_true, proba)", why="AUC of hard labels"),
        dict(code="from sklearn.metrics import log_loss, roc_auc_score\n\ndef solve(y_true, proba):\n    return roc_auc_score(y_true, proba), log_loss(y_true, 1 - proba)", why="probability of the wrong class"),
    ],
),
dict(
    id="sk-017",
    title="Confusion matrix normalized per true class",
    difficulty="Easy",
    tags=["metrics"],
    signature="def solve(y_true: np.ndarray, y_pred: np.ndarray, labels: list) -> np.ndarray:",
    statement="""
Return the confusion matrix with rows = true classes and columns = predicted classes, both in the order given by `labels`, **normalized over each true class** (every row sums to 1).
""",
    setup="""
def make(seed, n, labels):
    rng = np.random.default_rng(seed)
    y = rng.choice(labels, n)
    return {"y_true": y, "y_pred": np.where(rng.random(n) < 0.6, y, rng.choice(labels, n)), "labels": labels}

EXAMPLE = lambda: make(0, 30, ["low", "mid", "high"])
""",
    tests="""
TESTS = [
    lambda: make(1, 100, ["c", "b", "a"]),
    lambda: make(2, 4000, ["x1", "x2", "x3", "x4", "x5"]),
    Test(lambda: make(3, 25, ["yes", "no"]), "binary, non-alphabetical order"),
]
""",
    hint1="`confusion_matrix(y_true, y_pred, labels=labels, normalize='true')`.",
    hint2="confusion_matrix(y_true, y_pred, labels=labels, normalize='true')",
    solution="""
from sklearn.metrics import confusion_matrix

def solve(y_true, y_pred, labels):
    return confusion_matrix(y_true, y_pred, labels=labels, normalize="true")
""",
    explanation="""
`normalize='true'` divides by row (true-class) totals, so the diagonal holds per-class recall; `'pred'` gives per-class precision and `'all'` shares of the total. `labels=` fixes the order (default: sorted labels) and keeps classes that never appear in the batch.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.metrics.confusion_matrix.html"],
    wrong_solutions=[
        dict(code="from sklearn.metrics import confusion_matrix\n\ndef solve(y_true, y_pred, labels):\n    return confusion_matrix(y_true, y_pred, labels=labels, normalize='pred')", why="normalized by predicted class"),
        dict(code="from sklearn.metrics import confusion_matrix\n\ndef solve(y_true, y_pred, labels):\n    return confusion_matrix(y_true, y_pred, normalize='true')", why="sorted label order"),
    ],
),
dict(
    id="sk-018",
    title="Regression metrics: MAE, RMSE, R²",
    difficulty="Easy",
    tags=["metrics"],
    signature="def solve(y_true: np.ndarray, y_pred: np.ndarray) -> dict:",
    statement="""
Return a dict `{"mae": ..., "rmse": ..., "r2": ...}` (floats) for the given true values and predictions.
""",
    setup="""
def make(seed, n, noise=10.0):
    rng = np.random.default_rng(seed)
    y = rng.normal(100, 30, n)
    return {"y_true": y, "y_pred": y + rng.normal(0, noise, n)}

EXAMPLE = lambda: {"y_true": np.array([3.0, 5.0, 2.5, 7.0]), "y_pred": np.array([2.5, 5.0, 3.0, 8.0])}
""",
    tests="""
TESTS = [
    lambda: make(1, 50),
    lambda: make(2, 5000, noise=40.0),
    Test(lambda: make(3, 3, noise=1.0), "three points"),
]
""",
    hint1="`mean_absolute_error`, `root_mean_squared_error` (scikit-learn >= 1.4) and `r2_score`, called as `(y_true, y_pred)`.",
    hint2="{'mae': mean_absolute_error(y_true, y_pred), 'rmse': root_mean_squared_error(y_true, y_pred), 'r2': r2_score(y_true, y_pred)}",
    solution="""
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error

def solve(y_true, y_pred):
    return {"mae": mean_absolute_error(y_true, y_pred), "rmse": root_mean_squared_error(y_true, y_pred),
            "r2": r2_score(y_true, y_pred)}
""",
    explanation="""
`mean_squared_error(..., squared=False)` was removed in scikit-learn 1.6: use `root_mean_squared_error` (or `np.sqrt` of the MSE on older machines). R² is **not** symmetric, so `r2_score(y_pred, y_true)` is a different, wrong number. RMSE punishes large errors more than MAE.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.metrics.root_mean_squared_error.html",
          "https://scikit-learn.org/stable/modules/generated/sklearn.metrics.r2_score.html"],
    wrong_solutions=[
        dict(code="from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score\n\ndef solve(y_true, y_pred):\n    return {'mae': mean_absolute_error(y_true, y_pred), 'rmse': mean_squared_error(y_true, y_pred), 'r2': r2_score(y_true, y_pred)}", why="MSE, not RMSE"),
        dict(code="from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score\n\ndef solve(y_true, y_pred):\n    return {'mae': mean_absolute_error(y_true, y_pred), 'rmse': root_mean_squared_error(y_true, y_pred), 'r2': r2_score(y_pred, y_true)}", why="R² arguments swapped"),
    ],
),
# ------------------------------------------------------------------ cross-validation & tuning
dict(
    id="sk-019",
    title="Cross-validated ROC AUC",
    difficulty="Medium",
    tags=["cross-validation"],
    signature="def solve(X: pd.DataFrame, y: pd.Series) -> tuple:",
    statement="""
Estimate the ROC AUC of `make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))` with **5-fold stratified** cross-validation, shuffling with `random_state=0`. Return `(mean, std)` of the 5 fold scores.
""",
    setup=CLF + """
EXAMPLE = lambda: dict(zip(["X", "y"], clf_data(0, 100)))
""",
    tests="""
TESTS = [
    lambda: dict(zip(["X", "y"], clf_data(1, 300, weights=[0.8]))),
    lambda: dict(zip(["X", "y"], clf_data(2, 2000, k=15, sep=0.5))),
    Test(lambda: dict(zip(["X", "y"], clf_data(3, 50, k=4))), "small"),
]
""",
    hint1="`cross_val_score(pipe, X, y, cv=StratifiedKFold(5, shuffle=True, random_state=0), scoring='roc_auc')`.",
    hint2="cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)\nscores = cross_val_score(pipe, X, y, cv=cv, scoring='roc_auc')\nscores.mean(), scores.std()",
    solution="""
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

def solve(X, y):
    pipe = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
    scores = cross_val_score(pipe, X, y, cv=cv, scoring="roc_auc")
    return float(scores.mean()), float(scores.std())
""",
    explanation="""
Pass the whole pipeline so the scaler is refitted inside each fold (no leakage). `cv=5` uses StratifiedKFold **without** shuffling for classifiers, which is risky if the rows are ordered. The default scoring is accuracy, so ask for `'roc_auc'` explicitly. Report the spread, not just the mean.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.cross_val_score.html",
          "https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.StratifiedKFold.html"],
    wrong_solutions=[
        dict(code="""
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

def solve(X, y):
    scores = cross_val_score(make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)), X, y, cv=5, scoring="roc_auc")
    return float(scores.mean()), float(scores.std())
""", why="no shuffling"),
        dict(code="""
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

def solve(X, y):
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
    scores = cross_val_score(make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)), X, y, cv=cv)
    return float(scores.mean()), float(scores.std())
""", why="accuracy, the default scoring"),
    ],
),
dict(
    id="sk-020",
    title="Train and test scores for several metrics",
    difficulty="Medium",
    tags=["cross-validation", "diagnostics"],
    signature="def solve(X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:",
    statement="""
Evaluate `DecisionTreeClassifier(max_depth=6, random_state=0)` with `StratifiedKFold(5, shuffle=True, random_state=0)` on **both** `accuracy` and `roc_auc`, also collecting the **training** scores. Return a DataFrame with index `['accuracy', 'roc_auc']` and columns `['train', 'test']` holding the mean scores across folds.
""",
    setup=CLF + """
EXAMPLE = lambda: dict(zip(["X", "y"], clf_data(0, 150)))
""",
    tests="""
TESTS = [
    lambda: dict(zip(["X", "y"], clf_data(1, 400, sep=0.6))),
    lambda: dict(zip(["X", "y"], clf_data(2, 2000, k=12))),
    Test(lambda: dict(zip(["X", "y"], clf_data(3, 60, k=4))), "small"),
]
""",
    hint1="`cross_validate(model, X, y, cv=cv, scoring=['accuracy', 'roc_auc'], return_train_score=True)` returns a dict of arrays such as `'test_accuracy'` and `'train_roc_auc'`.",
    hint2="res = cross_validate(model, X, y, cv=cv, scoring=['accuracy', 'roc_auc'], return_train_score=True)\npd.DataFrame({s: {m: res[f'{s}_{m}'].mean() for m in ['accuracy', 'roc_auc']} for s in ['train', 'test']})",
    solution="""
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.tree import DecisionTreeClassifier

def solve(X, y):
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
    res = cross_validate(DecisionTreeClassifier(max_depth=6, random_state=0), X, y, cv=cv,
                         scoring=["accuracy", "roc_auc"], return_train_score=True)
    return pd.DataFrame({s: {m: res[f"{s}_{m}"].mean() for m in ["accuracy", "roc_auc"]}
                         for s in ["train", "test"]})
""",
    explanation="""
`cross_validate` computes several metrics in one pass and can return training scores. A large train/test gap means overfitting, while low scores on both mean underfitting. Keys are `test_<metric>` / `train_<metric>`, plus `fit_time` and `score_time`.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.cross_validate.html"],
    wrong_solutions=[
        dict(code="""
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.tree import DecisionTreeClassifier

def solve(X, y):
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
    res = cross_validate(DecisionTreeClassifier(max_depth=6, random_state=0), X, y, cv=cv, scoring=["accuracy", "roc_auc"], return_train_score=True)
    return pd.DataFrame({s: {m: res[f"{s}_{m}"].mean() for m in ["accuracy", "roc_auc"]} for s in ["test", "train"]})
""", why="columns in the wrong order"),
        dict(code="""
from sklearn.model_selection import cross_validate
from sklearn.tree import DecisionTreeClassifier

def solve(X, y):
    res = cross_validate(DecisionTreeClassifier(max_depth=6, random_state=0), X, y, cv=5, scoring=["accuracy", "roc_auc"], return_train_score=True)
    return pd.DataFrame({s: {m: res[f"{s}_{m}"].mean() for m in ["accuracy", "roc_auc"]} for s in ["train", "test"]})
""", why="unshuffled folds"),
    ],
),
dict(
    id="sk-021",
    title="Folds that keep each user on one side",
    difficulty="Medium",
    tags=["cross-validation", "leakage"],
    signature="def solve(X: np.ndarray, y: np.ndarray, groups: np.ndarray) -> list:",
    statement="""
Each user contributes several rows (`groups` holds the user id of each row). Create **4** cross-validation folds such that no user ever appears in both the training and the test part of a fold, and every row is in exactly one test fold. Return the list of `(train_idx, test_idx)` index arrays.
""",
    setup="""
def make(seed, n, n_users):
    rng = np.random.default_rng(seed)
    g = rng.integers(0, n_users, n)
    return {"X": rng.normal(size=(n, 3)), "y": rng.integers(0, 2, n), "groups": g}

EXAMPLE = lambda: make(0, 20, 6)
""",
    tests="""
TESTS = [
    lambda: make(1, 100, 15),
    lambda: make(2, 3000, 200),
    Test(lambda: make(3, 12, 4), "exactly four users"),
]

def check(got, exp, inputs):
    g = np.asarray(inputs["groups"])
    n = len(g)
    folds = list(got)
    if len(folds) != 4:
        fail(f"expected 4 folds, got {len(folds)}")
    seen = np.zeros(n, dtype=int)
    for k, fold in enumerate(folds):
        tr, te = (np.asarray(a) for a in fold)
        if set(g[tr].tolist()) & set(g[te].tolist()):
            fail(f"fold {k}: some user appears in both train and test")
        if len(np.intersect1d(tr, te)) or len(tr) + len(te) != n:
            fail(f"fold {k}: train and test must split all rows")
        seen[te] += 1
    if not (seen == 1).all():
        fail("every row must appear in exactly one test fold")
""",
    hint1="`GroupKFold(n_splits=4).split(X, y, groups)`.",
    hint2="list(GroupKFold(n_splits=4).split(X, y, groups))",
    solution="""
from sklearn.model_selection import GroupKFold

def solve(X, y, groups):
    return list(GroupKFold(n_splits=4).split(X, y, groups))
""",
    explanation="""
If the same customer or patient sits on both sides of a split, the model can memorize individuals and the CV score overstates performance on new ones. Group-aware splitters (`GroupKFold`, `StratifiedGroupKFold`, `GroupShuffleSplit`) take `groups=`; pass it to `cross_val_score(..., groups=g)` too.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html",
          "https://scikit-learn.org/stable/modules/cross_validation.html#group-k-fold"],
    wrong_solutions=[
        dict(code="from sklearn.model_selection import KFold\n\ndef solve(X, y, groups):\n    return list(KFold(n_splits=4, shuffle=True, random_state=0).split(X))", why="users leak across folds"),
        dict(code="from sklearn.model_selection import GroupKFold\n\ndef solve(X, y, groups):\n    return list(GroupKFold(n_splits=5).split(X, y, groups))", why="five folds"),
    ],
),
dict(
    id="sk-022",
    title="Expanding-window folds for time series",
    difficulty="Medium",
    tags=["cross-validation", "leakage"],
    signature="def solve(n: int) -> list:",
    statement="""
Rows `0..n-1` are in time order. Build **5** forward-chaining splits, as scikit-learn's time-series splitter does by default: each test block has `n // 6` rows, the 5 test blocks are the last `5 * (n // 6)` rows in order, and each training set is **every row before** its test block. Return the list of `(train_idx, test_idx)` integer arrays.
""",
    setup="""
EXAMPLE = lambda: {"n": 12}
""",
    tests="""
TESTS = [
    lambda: {"n": 60},
    lambda: {"n": 1000},
    Test(lambda: {"n": 23}, "n not divisible by 6"),
]
""",
    hint1="`TimeSeriesSplit(n_splits=5).split(np.arange(n))`.",
    hint2="list(TimeSeriesSplit(n_splits=5).split(np.arange(n)))",
    solution="""
from sklearn.model_selection import TimeSeriesSplit

def solve(n):
    return list(TimeSeriesSplit(n_splits=5).split(np.arange(n)))
""",
    explanation="""
With time-ordered data, shuffled K-fold trains on the future to predict the past, which is optimistic and impossible in production. `TimeSeriesSplit` always tests on rows after the training window; use `gap=` to leave an embargo between them (e.g. when labels look `h` days ahead) and `max_train_size=` for a rolling window.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html"],
    wrong_solutions=[
        dict(code="from sklearn.model_selection import KFold\n\ndef solve(n):\n    return list(KFold(n_splits=5).split(np.arange(n)))", why="trains on the future"),
        dict(code="from sklearn.model_selection import TimeSeriesSplit\n\ndef solve(n):\n    return list(TimeSeriesSplit(n_splits=5, gap=1).split(np.arange(n)))", why="gap not requested"),
    ],
),
dict(
    id="sk-023",
    title="Grid search over a pipeline",
    difficulty="Hard",
    tags=["tuning", "pipelines"],
    signature="def solve(X: pd.DataFrame, y: pd.Series) -> tuple:",
    statement="""
Tune `C` in `[0.01, 0.1, 1, 10]` for the classifier in

`Pipeline([("scale", StandardScaler()), ("clf", LogisticRegression(max_iter=1000))])`

with a grid search using `StratifiedKFold(5, shuffle=True, random_state=0)` and ROC AUC scoring. Return `(best_C, best_mean_cv_score)`.
""",
    setup=CLF + """
EXAMPLE = lambda: dict(zip(["X", "y"], clf_data(0, 120, k=10, informative=3)))
""",
    tests="""
TESTS = [
    lambda: dict(zip(["X", "y"], clf_data(1, 300, k=20, informative=3, sep=0.6))),
    lambda: dict(zip(["X", "y"], clf_data(2, 1500, k=12))),
    Test(lambda: dict(zip(["X", "y"], clf_data(3, 60, k=30, informative=2))), "many features, few rows"),
]
""",
    hint1="`GridSearchCV(pipe, {'clf__C': [...]}, cv=cv, scoring='roc_auc').fit(X, y)`, then `best_params_` and `best_score_`.",
    hint2="gs = GridSearchCV(pipe, {'clf__C': [0.01, 0.1, 1, 10]}, cv=cv, scoring='roc_auc').fit(X, y)\ngs.best_params_['clf__C'], gs.best_score_",
    solution="""
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

def solve(X, y):
    pipe = Pipeline([("scale", StandardScaler()), ("clf", LogisticRegression(max_iter=1000))])
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
    gs = GridSearchCV(pipe, {"clf__C": [0.01, 0.1, 1, 10]}, cv=cv, scoring="roc_auc").fit(X, y)
    return gs.best_params_["clf__C"], float(gs.best_score_)
""",
    explanation="""
Grid keys use the `step__param` names. `best_score_` is the best mean **CV** score: it's optimistically biased because you selected on it, so confirm on a held-out test set (or use nested CV). After fitting, `gs.best_estimator_` is refitted on all of `X` (`refit=True`).
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GridSearchCV.html",
          "https://scikit-learn.org/stable/modules/grid_search.html"],
    wrong_solutions=[
        dict(code="""
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

def solve(X, y):
    pipe = Pipeline([("scale", StandardScaler()), ("clf", LogisticRegression(max_iter=1000))])
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
    gs = GridSearchCV(pipe, {"clf__C": [0.01, 0.1, 1, 10]}, cv=cv).fit(X, y)
    return gs.best_params_["clf__C"], float(gs.best_score_)
""", why="accuracy scoring"),
        dict(code="""
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

def solve(X, y):
    pipe = Pipeline([("scale", StandardScaler()), ("clf", LogisticRegression(max_iter=1000))])
    gs = GridSearchCV(pipe, {"clf__C": [0.01, 0.1, 1, 10]}, cv=5, scoring="roc_auc").fit(X, y)
    return gs.best_params_["clf__C"], float(gs.best_score_)
""", why="unshuffled folds"),
    ],
),
dict(
    id="sk-024",
    title="Randomized search over tree depth and leaf size",
    difficulty="Medium",
    tags=["tuning"],
    signature="def solve(X: pd.DataFrame, y: pd.Series) -> dict:",
    statement="""
Tune a `DecisionTreeClassifier(random_state=0)` with a **randomized** search: 10 draws (`random_state=0`) of `max_depth` from `scipy.stats.randint(2, 10)` and `min_samples_leaf` from `scipy.stats.randint(1, 20)`, `StratifiedKFold(3, shuffle=True, random_state=0)`, accuracy scoring. Return the best parameters dict.
""",
    setup=CLF + """
EXAMPLE = lambda: dict(zip(["X", "y"], clf_data(0, 150)))
""",
    tests="""
TESTS = [
    lambda: dict(zip(["X", "y"], clf_data(1, 300, sep=0.7))),
    lambda: dict(zip(["X", "y"], clf_data(2, 600, k=12))),
    Test(lambda: dict(zip(["X", "y"], clf_data(3, 80, k=4))), "small"),
]
""",
    hint1="`RandomizedSearchCV(model, {'max_depth': randint(2, 10), ...}, n_iter=10, cv=cv, random_state=0)`.",
    hint2="from scipy.stats import randint\nrs = RandomizedSearchCV(DecisionTreeClassifier(random_state=0),\n                        {'max_depth': randint(2, 10), 'min_samples_leaf': randint(1, 20)},\n                        n_iter=10, cv=cv, random_state=0).fit(X, y)\nrs.best_params_",
    solution="""
from scipy.stats import randint
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold
from sklearn.tree import DecisionTreeClassifier

def solve(X, y):
    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=0)
    space = {"max_depth": randint(2, 10), "min_samples_leaf": randint(1, 20)}
    rs = RandomizedSearchCV(DecisionTreeClassifier(random_state=0), space, n_iter=10, cv=cv,
                            scoring="accuracy", random_state=0).fit(X, y)
    return rs.best_params_
""",
    explanation="""
Random search samples `n_iter` points from distributions; it scales to many hyper-parameters far better than a full grid. Use `scipy.stats.loguniform` for scale parameters such as `C` or a learning rate. Note `randint(a, b)` excludes `b`. Seed `random_state` for reproducible draws.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.RandomizedSearchCV.html",
          "https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.randint.html"],
    wrong_solutions=[
        dict(code="""
from scipy.stats import randint
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold
from sklearn.tree import DecisionTreeClassifier

def solve(X, y):
    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=0)
    rs = RandomizedSearchCV(DecisionTreeClassifier(random_state=0), {"max_depth": randint(2, 10), "min_samples_leaf": randint(1, 20)}, n_iter=3, cv=cv, random_state=0).fit(X, y)
    return rs.best_params_
""", why="only 3 draws"),
    ],
),
# ------------------------------------------------------------------ ensembles & inspection
dict(
    id="sk-025",
    title="Random-forest top-5 importances",
    difficulty="Medium",
    tags=["ensembles", "model inspection"],
    signature="def solve(X: pd.DataFrame, y: pd.Series) -> pd.Series:",
    statement="""
Fit `RandomForestClassifier(n_estimators=30, max_depth=6, random_state=0)` on `(X, y)` and return its **5 largest** impurity-based feature importances as a Series indexed by feature name, largest first.
""",
    setup=CLF + """
EXAMPLE = lambda: dict(zip(["X", "y"], clf_data(0, 150, k=8, informative=3)))
""",
    tests="""
TESTS = [
    lambda: dict(zip(["X", "y"], clf_data(1, 300, k=10))),
    lambda: dict(zip(["X", "y"], clf_data(2, 1200, k=20, informative=6))),
    Test(lambda: dict(zip(["X", "y"], clf_data(3, 60, k=5, informative=2))), "five features"),
]
""",
    hint1="`pd.Series(model.feature_importances_, index=X.columns).nlargest(5)`.",
    hint2="rf = RandomForestClassifier(n_estimators=30, max_depth=6, random_state=0).fit(X, y)\npd.Series(rf.feature_importances_, index=X.columns).nlargest(5)",
    solution="""
from sklearn.ensemble import RandomForestClassifier

def solve(X, y):
    rf = RandomForestClassifier(n_estimators=30, max_depth=6, random_state=0).fit(X, y)
    return pd.Series(rf.feature_importances_, index=X.columns).nlargest(5)
""",
    explanation="""
`feature_importances_` (mean decrease in impurity) is computed on the **training** data and is biased towards continuous and high-cardinality features; the values sum to 1. Use permutation importance on held-out data for a more honest ranking. Set `random_state` for reproducibility.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html",
          "https://scikit-learn.org/stable/auto_examples/ensemble/plot_forest_importances.html"],
    wrong_solutions=[
        dict(code="from sklearn.ensemble import RandomForestClassifier\n\ndef solve(X, y):\n    rf = RandomForestClassifier(n_estimators=30, max_depth=6, random_state=0).fit(X, y)\n    return pd.Series(rf.feature_importances_, index=X.columns).nsmallest(5)", why="least important"),
        dict(code="from sklearn.ensemble import RandomForestClassifier\n\ndef solve(X, y):\n    rf = RandomForestClassifier(n_estimators=30, max_depth=6, random_state=0).fit(X, y)\n    return pd.Series(rf.feature_importances_, index=X.columns).head(5)", why="first five columns"),
    ],
),
dict(
    id="sk-026",
    title="Gradient boosting that handles NaN natively",
    difficulty="Medium",
    tags=["boosting", "ensembles"],
    signature="def solve(X_train, y_train, X_test) -> np.ndarray:",
    statement="""
The features contain NaNs, and **missingness itself is informative**. Fit `HistGradientBoostingClassifier(max_iter=50, random_state=0)` **directly** on the data with NaNs (no imputation) and return the predicted probabilities of class 1 for `X_test`.
""",
    setup=CLF + """
def make(seed, n):
    X, y = clf_data(seed, n, k=6, informative=3)
    rng = np.random.default_rng(seed)
    X = X.copy()
    X.loc[rng.random(n) < 0.2, "x0"] = np.nan
    X.loc[(y == 1) & (rng.random(n) < 0.4), "x1"] = np.nan
    Xtr, Xte, ytr, yte = split(X, y, seed)
    return {"X_train": Xtr, "y_train": ytr, "X_test": Xte}

EXAMPLE = lambda: make(0, 80)
""",
    tests="""
TESTS = [
    lambda: make(1, 300),
    lambda: make(2, 1500),
    Test(lambda: make(3, 60), "small"),
]
""",
    compare=dict(rtol=1e-5, atol=1e-7),
    hint1="`HistGradientBoostingClassifier` learns at each split which side missing values go to; just `fit` and `predict_proba`.",
    hint2="HistGradientBoostingClassifier(max_iter=50, random_state=0).fit(X_train, y_train).predict_proba(X_test)[:, 1]",
    solution="""
from sklearn.ensemble import HistGradientBoostingClassifier

def solve(X_train, y_train, X_test):
    model = HistGradientBoostingClassifier(max_iter=50, random_state=0).fit(X_train, y_train)
    return model.predict_proba(X_test)[:, 1]
""",
    explanation="""
Histogram gradient boosting (like LightGBM, which inspired it) supports NaN natively: it learns whether missing values go left or right at every split, so "missing" can itself carry signal. Imputing with a constant destroys that signal (here `x1` is missing more often for positives). It also handles categorical features via `categorical_features=`.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingClassifier.html",
          "https://scikit-learn.org/stable/modules/ensemble.html#missing-values-support"],
    wrong_solutions=[
        dict(code="from sklearn.ensemble import HistGradientBoostingClassifier\n\ndef solve(X_train, y_train, X_test):\n    m = HistGradientBoostingClassifier(max_iter=50, random_state=0).fit(X_train.fillna(0), y_train)\n    return m.predict_proba(X_test.fillna(0))[:, 1]", why="imputed with 0"),
        dict(code="from sklearn.ensemble import HistGradientBoostingClassifier\n\ndef solve(X_train, y_train, X_test):\n    m = HistGradientBoostingClassifier(max_iter=50, random_state=0).fit(X_train, y_train)\n    return m.predict(X_test)", why="hard labels"),
    ],
),
dict(
    id="sk-027",
    title="Class weights for a rare class",
    difficulty="Medium",
    tags=["imbalance", "classification"],
    signature="def solve(X_train, y_train, X_test, y_test) -> tuple:",
    statement="""
Positives are rare (about 5%). Fit two `LogisticRegression(max_iter=1000)` models: a plain one, and one whose class weights are **inversely proportional to the class frequencies**. Return `(recall_plain, recall_weighted)`, the test recall of the positive class for each.
""",
    setup=CLF + """
def make(seed, n, w=0.95):
    X, y = clf_data(seed, n, k=6, informative=3, weights=[w], sep=0.8)
    Xtr, Xte, ytr, yte = split(X, y, seed)
    return {"X_train": Xtr, "y_train": ytr, "X_test": Xte, "y_test": yte}

EXAMPLE = lambda: make(0, 400)
""",
    tests="""
TESTS = [
    lambda: make(1, 1000),
    lambda: make(2, 3000, w=0.97),
    Test(lambda: make(3, 600, w=0.9), "10% positives"),
]
""",
    hint1="`LogisticRegression(class_weight='balanced', ...)` reweights the loss by `n_samples / (n_classes * count(class))`; compare with `recall_score`.",
    hint2="plain = LogisticRegression(max_iter=1000).fit(X_train, y_train)\nweighted = LogisticRegression(max_iter=1000, class_weight='balanced').fit(X_train, y_train)\nrecall_score(y_test, plain.predict(X_test)), recall_score(y_test, weighted.predict(X_test))",
    solution="""
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import recall_score

def solve(X_train, y_train, X_test, y_test):
    plain = LogisticRegression(max_iter=1000).fit(X_train, y_train)
    weighted = LogisticRegression(max_iter=1000, class_weight="balanced").fit(X_train, y_train)
    return recall_score(y_test, plain.predict(X_test)), recall_score(y_test, weighted.predict(X_test))
""",
    explanation="""
With 5% positives, minimizing plain log loss favours predicting "negative"; `class_weight='balanced'` makes each class contribute equally, which raises recall at the cost of precision. It shifts the effective threshold, so an alternative is to keep the plain model and lower the decision threshold. Evaluate with PR-AUC or recall at fixed precision, not accuracy.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html",
          "https://scikit-learn.org/stable/modules/generated/sklearn.utils.class_weight.compute_class_weight.html"],
    wrong_solutions=[
        dict(code="""
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import recall_score

def solve(X_train, y_train, X_test, y_test):
    plain = LogisticRegression(max_iter=1000).fit(X_train, y_train)
    weighted = LogisticRegression(max_iter=1000, class_weight={0: 1, 1: 2}).fit(X_train, y_train)
    return recall_score(y_test, plain.predict(X_test)), recall_score(y_test, weighted.predict(X_test))
""", why="arbitrary weights"),
        dict(code="""
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_score

def solve(X_train, y_train, X_test, y_test):
    plain = LogisticRegression(max_iter=1000).fit(X_train, y_train)
    weighted = LogisticRegression(max_iter=1000, class_weight="balanced").fit(X_train, y_train)
    return precision_score(y_test, plain.predict(X_test), zero_division=0), precision_score(y_test, weighted.predict(X_test), zero_division=0)
""", why="precision, not recall"),
    ],
),
dict(
    id="sk-028",
    title="Polynomial features for a curved target",
    difficulty="Medium",
    tags=["feature engineering", "linear models"],
    signature="def solve(X_train, y_train, X_test, y_test) -> tuple:",
    statement="""
The target depends on squares and products of the features. Compare the **test R²** of a `LinearRegression` on the raw features with a pipeline that first adds degree-2 polynomial features (`PolynomialFeatures(degree=2, include_bias=False)`). Return `(r2_linear, r2_poly)`.
""",
    setup="""
def make(seed, n):
    rng = np.random.default_rng(seed)
    X = rng.uniform(-2, 2, (n, 3))
    y = 1 + X[:, 0] - 2 * X[:, 1] ** 2 + 1.5 * X[:, 0] * X[:, 2] + rng.normal(0, 0.3, n)
    k = int(n * 0.7)
    return {"X_train": X[:k], "y_train": y[:k], "X_test": X[k:], "y_test": y[k:]}

EXAMPLE = lambda: make(0, 60)
""",
    tests="""
TESTS = [
    lambda: make(1, 200),
    lambda: make(2, 3000),
    Test(lambda: make(3, 30), "small"),
]
""",
    hint1="`make_pipeline(PolynomialFeatures(degree=2, include_bias=False), LinearRegression())`; `.score(X, y)` returns R².",
    hint2="lin = LinearRegression().fit(X_train, y_train)\npoly = make_pipeline(PolynomialFeatures(degree=2, include_bias=False), LinearRegression()).fit(X_train, y_train)\nlin.score(X_test, y_test), poly.score(X_test, y_test)",
    solution="""
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures

def solve(X_train, y_train, X_test, y_test):
    lin = LinearRegression().fit(X_train, y_train)
    poly = make_pipeline(PolynomialFeatures(degree=2, include_bias=False), LinearRegression()).fit(X_train, y_train)
    return lin.score(X_test, y_test), poly.score(X_test, y_test)
""",
    explanation="""
A linear model is linear in its **features**, so adding squares and interactions lets it fit curves. The number of features grows quickly with degree (overfitting risk), so pair high degrees with regularization (`Ridge`) and scaling. For regressors, `score` is R² on the given data.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.PolynomialFeatures.html"],
    wrong_solutions=[
        dict(code="""
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures

def solve(X_train, y_train, X_test, y_test):
    lin = LinearRegression().fit(X_train, y_train)
    poly = make_pipeline(PolynomialFeatures(degree=2, include_bias=False), LinearRegression()).fit(X_train, y_train)
    return lin.score(X_train, y_train), poly.score(X_train, y_train)
""", why="training R²"),
        dict(code="""
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures

def solve(X_train, y_train, X_test, y_test):
    lin = LinearRegression().fit(X_train, y_train)
    poly = make_pipeline(PolynomialFeatures(degree=2, interaction_only=True, include_bias=False), LinearRegression()).fit(X_train, y_train)
    return lin.score(X_test, y_test), poly.score(X_test, y_test)
""", why="interactions only, no squares"),
    ],
),
dict(
    id="sk-029",
    title="Permutation importance on held-out data",
    difficulty="Hard",
    tags=["model inspection"],
    signature="def solve(X_train, y_train, X_test, y_test) -> pd.Series:",
    statement="""
Fit `RandomForestRegressor(n_estimators=20, random_state=0)` on the training data, then compute **permutation importance on the test set** (`n_repeats=5`, `random_state=0`, the default R² scoring). Return the mean importances as a Series indexed by feature name, sorted from most to least important.
""",
    setup="""
def make(seed, n):
    rng = np.random.default_rng(seed)
    X = pd.DataFrame(rng.normal(size=(n, 6)), columns=["income", "age", "tenure", "noise_a", "noise_b", "id_hash"])
    X["id_hash"] = rng.permutation(n) / n
    y = 3 * X["income"] + X["age"] ** 2 - 2 * X["tenure"] + rng.normal(0, 1, n)
    k = int(n * 0.7)
    return {"X_train": X.iloc[:k], "y_train": y.iloc[:k], "X_test": X.iloc[k:], "y_test": y.iloc[k:]}

EXAMPLE = lambda: make(0, 150)
""",
    tests="""
TESTS = [
    lambda: make(1, 300),
    lambda: make(2, 1000),
    Test(lambda: make(3, 80), "small"),
]
""",
    compare=dict(rtol=1e-4, atol=1e-6),
    hint1="`permutation_importance(model, X_test, y_test, n_repeats=5, random_state=0).importances_mean`.",
    hint2="r = permutation_importance(model, X_test, y_test, n_repeats=5, random_state=0)\npd.Series(r.importances_mean, index=X_test.columns).sort_values(ascending=False)",
    solution="""
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance

def solve(X_train, y_train, X_test, y_test):
    model = RandomForestRegressor(n_estimators=20, random_state=0).fit(X_train, y_train)
    r = permutation_importance(model, X_test, y_test, n_repeats=5, random_state=0)
    return pd.Series(r.importances_mean, index=X_test.columns).sort_values(ascending=False)
""",
    explanation="""
Permutation importance is the drop in score when one feature is shuffled, measured on **held-out** data, so features the model merely memorized (like the random `id_hash`) score about 0. Impurity importances would rank `id_hash` well. Correlated features share credit: shuffling one leaves its twin.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.inspection.permutation_importance.html",
          "https://scikit-learn.org/stable/modules/permutation_importance.html"],
    wrong_solutions=[
        dict(code="""
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance

def solve(X_train, y_train, X_test, y_test):
    model = RandomForestRegressor(n_estimators=20, random_state=0).fit(X_train, y_train)
    r = permutation_importance(model, X_train, y_train, n_repeats=5, random_state=0)
    return pd.Series(r.importances_mean, index=X_test.columns).sort_values(ascending=False)
""", why="computed on the training set"),
        dict(code="""
from sklearn.ensemble import RandomForestRegressor

def solve(X_train, y_train, X_test, y_test):
    model = RandomForestRegressor(n_estimators=20, random_state=0).fit(X_train, y_train)
    return pd.Series(model.feature_importances_, index=X_test.columns).sort_values(ascending=False)
""", why="impurity importances"),
    ],
),
dict(
    id="sk-030",
    title="Validation curve: choose the tree depth",
    difficulty="Medium",
    tags=["diagnostics", "tuning"],
    signature="def solve(X: pd.DataFrame, y: pd.Series) -> tuple:",
    statement="""
Use a validation curve for `DecisionTreeClassifier(random_state=0)` over `max_depth` = 1, 2, ..., 8 with `StratifiedKFold(3, shuffle=True, random_state=0)` and accuracy. Let `best_depth` maximize the **mean validation** score (smallest depth on ties). Return `(best_depth, mean_train_score, mean_validation_score)` at that depth.
""",
    setup=CLF + """
EXAMPLE = lambda: dict(zip(["X", "y"], clf_data(0, 200, sep=0.6)))
""",
    tests="""
TESTS = [
    lambda: dict(zip(["X", "y"], clf_data(1, 300, sep=0.5))),
    lambda: dict(zip(["X", "y"], clf_data(2, 600, k=10, sep=0.8))),
    Test(lambda: dict(zip(["X", "y"], clf_data(3, 80, k=4))), "small"),
]
""",
    hint1="`validation_curve(model, X, y, param_name='max_depth', param_range=depths, cv=cv)` returns `(train_scores, val_scores)` of shape `(n_params, n_folds)`; average over axis 1 and `argmax`.",
    hint2="depths = np.arange(1, 9)\ntr, va = validation_curve(DecisionTreeClassifier(random_state=0), X, y, param_name='max_depth', param_range=depths, cv=cv)\ni = va.mean(axis=1).argmax()",
    solution="""
from sklearn.model_selection import StratifiedKFold, validation_curve
from sklearn.tree import DecisionTreeClassifier

def solve(X, y):
    depths = np.arange(1, 9)
    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=0)
    tr, va = validation_curve(DecisionTreeClassifier(random_state=0), X, y, param_name="max_depth",
                              param_range=depths, cv=cv)
    i = va.mean(axis=1).argmax()
    return int(depths[i]), float(tr.mean(axis=1)[i]), float(va.mean(axis=1)[i])
""",
    explanation="""
Training accuracy keeps rising with depth; validation accuracy peaks and then falls: that is the overfitting point. A low depth with low train *and* validation scores is underfitting. Pick on the validation curve, never the training one (which always prefers the deepest tree).
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.validation_curve.html",
          "https://scikit-learn.org/stable/modules/learning_curve.html"],
    wrong_solutions=[
        dict(code="""
from sklearn.model_selection import StratifiedKFold, validation_curve
from sklearn.tree import DecisionTreeClassifier

def solve(X, y):
    depths = np.arange(1, 9)
    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=0)
    tr, va = validation_curve(DecisionTreeClassifier(random_state=0), X, y, param_name="max_depth", param_range=depths, cv=cv)
    i = tr.mean(axis=1).argmax()
    return int(depths[i]), float(tr.mean(axis=1)[i]), float(va.mean(axis=1)[i])
""", why="chosen on training scores"),
    ],
),
dict(
    id="sk-031",
    title="Learning curve",
    difficulty="Medium",
    tags=["diagnostics"],
    signature="def solve(X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:",
    statement="""
Compute a learning curve for `LogisticRegression(max_iter=1000)` with training-set fractions `[0.1, 0.3, 0.55, 0.8, 1.0]`, `StratifiedKFold(5, shuffle=True, random_state=0)` and accuracy. Return a DataFrame indexed by the **absolute** number of training samples, with columns `train` and `validation` (mean scores over folds).
""",
    setup=CLF + """
EXAMPLE = lambda: dict(zip(["X", "y"], clf_data(0, 200)))
""",
    tests="""
TESTS = [
    lambda: dict(zip(["X", "y"], clf_data(1, 500, sep=0.6))),
    lambda: dict(zip(["X", "y"], clf_data(2, 2000, k=15))),
    Test(lambda: dict(zip(["X", "y"], clf_data(3, 100, k=4))), "small"),
]
""",
    hint1="`sizes, tr, va = learning_curve(model, X, y, train_sizes=[...], cv=cv)`; average the score arrays over axis 1.",
    hint2="sizes, tr, va = learning_curve(LogisticRegression(max_iter=1000), X, y, train_sizes=[0.1, 0.3, 0.55, 0.8, 1.0], cv=cv)\npd.DataFrame({'train': tr.mean(axis=1), 'validation': va.mean(axis=1)}, index=sizes)",
    solution="""
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, learning_curve

def solve(X, y):
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
    sizes, tr, va = learning_curve(LogisticRegression(max_iter=1000), X, y,
                                   train_sizes=[0.1, 0.3, 0.55, 0.8, 1.0], cv=cv)
    return pd.DataFrame({"train": tr.mean(axis=1), "validation": va.mean(axis=1)}, index=sizes)
""",
    explanation="""
If the validation curve is still rising at full size, more data will help. If train and validation have converged at a low score, the model is too simple (high bias), so add features or capacity. Fractions refer to the training part of each fold, which is why the absolute sizes are below `len(X)`.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.learning_curve.html"],
    wrong_solutions=[
        dict(code="""
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, learning_curve

def solve(X, y):
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
    sizes, tr, va = learning_curve(LogisticRegression(max_iter=1000), X, y, cv=cv)
    return pd.DataFrame({"train": tr.mean(axis=1), "validation": va.mean(axis=1)}, index=sizes)
""", why="default train sizes"),
        dict(code="""
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, learning_curve

def solve(X, y):
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
    sizes, tr, va = learning_curve(LogisticRegression(max_iter=1000), X, y, train_sizes=[0.1, 0.3, 0.55, 0.8, 1.0], cv=cv)
    return pd.DataFrame({"train": tr.mean(axis=1), "validation": va.mean(axis=1)}, index=[0.1, 0.3, 0.55, 0.8, 1.0])
""", why="fractions as the index"),
    ],
),
# ------------------------------------------------------------------ unsupervised
dict(
    id="sk-032",
    title="Choose k: inertia and silhouette",
    difficulty="Medium",
    tags=["clustering"],
    signature="def solve(X: np.ndarray) -> pd.DataFrame:",
    statement="""
Standardize `X`, then for k = 2..6 fit `KMeans(n_clusters=k, n_init=5, random_state=0)` on the standardized data and record the inertia and the **silhouette score**. Return a DataFrame indexed by k (2..6) with columns `inertia` and `silhouette`.
""",
    setup="""
def make(seed, n, centers, scale=(1, 100)):
    from sklearn.datasets import make_blobs
    X, _ = make_blobs(n_samples=n, centers=centers, n_features=3, cluster_std=1.2, random_state=seed)
    return {"X": X * np.array([scale[0], scale[1], 1.0])}

def iris():
    from sklearn.datasets import load_iris
    return load_iris().data

EXAMPLE = lambda: make(0, 120, 3)
""",
    tests="""
TESTS = [
    lambda: make(1, 200, 4),
    lambda: make(2, 1000, 2, scale=(50, 1)),
    Test(lambda: make(3, 40, 5), "small"),
    Test(lambda: {"X": iris()}, "sklearn's iris"),
]
""",
    compare=dict(rtol=1e-4, atol=1e-6),
    hint1="`silhouette_score(Xs, km.labels_)` with `km = KMeans(...).fit(Xs)` and `Xs = StandardScaler().fit_transform(X)`.",
    hint2="Xs = StandardScaler().fit_transform(X)\nfor k in range(2, 7):\n    km = KMeans(n_clusters=k, n_init=5, random_state=0).fit(Xs)\n    rows[k] = {'inertia': km.inertia_, 'silhouette': silhouette_score(Xs, km.labels_)}",
    solution="""
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

def solve(X):
    Xs = StandardScaler().fit_transform(X)
    rows = {}
    for k in range(2, 7):
        km = KMeans(n_clusters=k, n_init=5, random_state=0).fit(Xs)
        rows[k] = {"inertia": km.inertia_, "silhouette": silhouette_score(Xs, km.labels_)}
    return pd.DataFrame.from_dict(rows, orient="index")
""",
    explanation="""
Inertia always falls as k grows; the silhouette (cohesion vs separation, from -1 to 1) has a maximum, so it's a better automatic choice of k. Both are distance-based: without scaling, the feature measured in the largest units decides the clusters on its own.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.metrics.silhouette_score.html",
          "https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html"],
    wrong_solutions=[
        dict(code="""
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

def solve(X):
    rows = {}
    for k in range(2, 7):
        km = KMeans(n_clusters=k, n_init=5, random_state=0).fit(X)
        rows[k] = {"inertia": km.inertia_, "silhouette": silhouette_score(X, km.labels_)}
    return pd.DataFrame.from_dict(rows, orient="index")
""", why="not standardized"),
    ],
),
dict(
    id="sk-033",
    title="How many components for 95% of the variance?",
    difficulty="Medium",
    tags=["dimensionality reduction"],
    signature="def solve(X: np.ndarray) -> tuple:",
    statement="""
Standardize `X` and fit a `PCA` with all components. Return `(k, ratio)`: the **smallest** number of components whose cumulative explained variance ratio reaches **0.95**, and that cumulative ratio.
""",
    setup="""
def make(seed, n, d, rank):
    rng = np.random.default_rng(seed)
    Z = rng.normal(size=(n, rank)) @ rng.normal(size=(rank, d))
    return {"X": (Z + rng.normal(0, 0.3, (n, d))) * rng.uniform(1, 100, d)}

def wine():
    from sklearn.datasets import load_wine
    return {"X": load_wine().data}

def digits():
    from sklearn.datasets import load_digits
    return {"X": load_digits().data[:600]}

EXAMPLE = lambda: make(0, 100, 6, 2)
""",
    tests="""
TESTS = [
    lambda: make(1, 300, 10, 3),
    Test(lambda: wine(), "sklearn's wine dataset"),
    Test(lambda: digits(), "sklearn's digits (64 pixel features)"),
    Test(lambda: make(3, 50, 4, 4), "full rank"),
]
""",
    hint1="`cum = PCA().fit(Xs).explained_variance_ratio_.cumsum()`; `k = np.searchsorted(cum, 0.95) + 1` (or `argmax(cum >= 0.95) + 1`).",
    hint2="cum = PCA().fit(StandardScaler().fit_transform(X)).explained_variance_ratio_.cumsum()\nk = int(np.argmax(cum >= 0.95)) + 1\nk, cum[k - 1]",
    solution="""
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

def solve(X):
    cum = PCA().fit(StandardScaler().fit_transform(X)).explained_variance_ratio_.cumsum()
    k = int(np.argmax(cum >= 0.95)) + 1
    return k, float(cum[k - 1])
""",
    explanation="""
`argmax` on a boolean array returns the first True position (0-based), so add 1 to get a count of components. `PCA(n_components=0.95)` does the same selection for you (`.n_components_`). Standardize first unless the features share units.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.PCA.html"],
    wrong_solutions=[
        dict(code="""
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

def solve(X):
    cum = PCA().fit(StandardScaler().fit_transform(X)).explained_variance_ratio_.cumsum()
    k = int(np.argmax(cum >= 0.95))
    return k, float(cum[k])
""", why="0-based index returned as the count"),
        dict(code="""
from sklearn.decomposition import PCA

def solve(X):
    cum = PCA().fit(X).explained_variance_ratio_.cumsum()
    k = int(np.argmax(cum >= 0.95)) + 1
    return k, float(cum[k - 1])
""", why="not standardized"),
    ],
),
dict(
    id="sk-034",
    title="Feature selection without leakage",
    difficulty="Hard",
    tags=["leakage", "pipelines"],
    signature="def solve(X: np.ndarray, y: np.ndarray) -> float:",
    statement="""
`X` has hundreds of features but few rows (and possibly no real signal at all). Estimate the mean accuracy, over `StratifiedKFold(5, shuffle=True, random_state=0)`, of: keep the 10 best features by univariate ANOVA F-test (`SelectKBest(f_classif, k=10)`), then `LogisticRegression(max_iter=1000)`, with the selection performed **inside** cross-validation (fitted on each training fold only).
""",
    setup="""
def make(seed, n, d, signal=0.0):
    rng = np.random.default_rng(seed)
    y = rng.integers(0, 2, n)
    X = rng.normal(size=(n, d))
    X[:, :3] += signal * (2 * y[:, None] - 1)
    return {"X": X, "y": y}

EXAMPLE = lambda: make(0, 60, 500)
""",
    tests="""
TESTS = [
    Test(lambda: make(1, 80, 1000), "pure noise"),
    lambda: make(2, 120, 600, signal=0.8),
    lambda: make(3, 60, 300, signal=0.4),
]
""",
    hint1="Put the selector in the pipeline: `make_pipeline(SelectKBest(f_classif, k=10), LogisticRegression(...))` and cross-validate the whole thing.",
    hint2="pipe = make_pipeline(SelectKBest(f_classif, k=10), LogisticRegression(max_iter=1000))\ncross_val_score(pipe, X, y, cv=cv).mean()",
    solution="""
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline

def solve(X, y):
    pipe = make_pipeline(SelectKBest(f_classif, k=10), LogisticRegression(max_iter=1000))
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
    return float(cross_val_score(pipe, X, y, cv=cv).mean())
""",
    explanation="""
Selecting features on the full data before CV lets the selector see the test folds' labels. On pure noise the leaky version reports roughly 75-90% accuracy, the honest one about 50%. Every step that learns from data (scaling, imputation, selection, target encoding, resampling) must live inside the pipeline that gets cross-validated.
""",
    docs=["https://scikit-learn.org/stable/common_pitfalls.html#data-leakage-during-pre-processing",
          "https://scikit-learn.org/stable/modules/generated/sklearn.feature_selection.SelectKBest.html"],
    wrong_solutions=[
        dict(code="""
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score

def solve(X, y):
    Xs = SelectKBest(f_classif, k=10).fit_transform(X, y)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
    return float(cross_val_score(LogisticRegression(max_iter=1000), Xs, y, cv=cv).mean())
""", why="selection on all data (leakage)"),
    ],
),
# ------------------------------------------------------------------ LightGBM
dict(
    id="sk-035",
    title="LightGBM classifier with the scikit-learn API",
    difficulty="Medium",
    tags=["boosting"],
    signature="def solve(X_train, y_train, X_test, y_test) -> float:",
    statement="""
Train `lightgbm.LGBMClassifier(n_estimators=100, learning_rate=0.05, num_leaves=15, random_state=0, verbose=-1)` and return its **test ROC AUC**.
""",
    setup=CLF + """
def make(seed, n):
    X, y = clf_data(seed, n, k=10, informative=5, sep=0.6)
    Xtr, Xte, ytr, yte = split(X, y, seed)
    return {"X_train": Xtr, "y_train": ytr, "X_test": Xte, "y_test": yte}

EXAMPLE = lambda: make(0, 300)
""",
    tests="""
TESTS = [
    lambda: make(1, 600),
    lambda: make(2, 2000),
    Test(lambda: make(3, 150), "small"),
]
""",
    compare=dict(rtol=1e-4, atol=1e-6),
    hint1="`LGBMClassifier(...)` works like any scikit-learn classifier: `fit`, then `predict_proba(X)[:, 1]` into `roc_auc_score`.",
    hint2="from lightgbm import LGBMClassifier\nm = LGBMClassifier(n_estimators=100, learning_rate=0.05, num_leaves=15, random_state=0, verbose=-1).fit(X_train, y_train)\nroc_auc_score(y_test, m.predict_proba(X_test)[:, 1])",
    solution="""
from lightgbm import LGBMClassifier
from sklearn.metrics import roc_auc_score

def solve(X_train, y_train, X_test, y_test):
    m = LGBMClassifier(n_estimators=100, learning_rate=0.05, num_leaves=15, random_state=0, verbose=-1)
    m.fit(X_train, y_train)
    return float(roc_auc_score(y_test, m.predict_proba(X_test)[:, 1]))
""",
    explanation="""
LightGBM's scikit-learn wrapper plugs into pipelines, CV and grid search. `num_leaves` (not depth) controls tree complexity; `verbose=-1` silences its logging. AUC needs the probability column, not `predict`. In the browser it runs single-threaded; on a laptop it uses all cores by default.
""",
    docs=["https://lightgbm.readthedocs.io/en/stable/pythonapi/lightgbm.LGBMClassifier.html"],
    wrong_solutions=[
        dict(code="""
from lightgbm import LGBMClassifier
from sklearn.metrics import roc_auc_score

def solve(X_train, y_train, X_test, y_test):
    m = LGBMClassifier(n_estimators=100, learning_rate=0.05, num_leaves=15, random_state=0, verbose=-1).fit(X_train, y_train)
    return float(roc_auc_score(y_test, m.predict(X_test)))
""", why="AUC of hard labels"),
    ],
),
dict(
    id="sk-036",
    title="LightGBM with early stopping",
    difficulty="Hard",
    tags=["boosting", "tuning"],
    signature="def solve(X_train, y_train, X_valid, y_valid) -> tuple:",
    statement="""
Fit `LGBMClassifier(n_estimators=1000, learning_rate=0.05, random_state=0, verbose=-1)` with **early stopping on the validation set**: monitor the binary log loss and stop after 20 rounds without improvement. Return `(best_iteration, best_validation_log_loss)`.
""",
    setup=CLF + """
def make(seed, n, sep=0.6):
    X, y = clf_data(seed, n, k=10, informative=4, sep=sep)
    Xtr, Xva, ytr, yva = split(X, y, seed)
    return {"X_train": Xtr, "y_train": ytr, "X_valid": Xva, "y_valid": yva}

EXAMPLE = lambda: make(0, 400)
""",
    tests="""
TESTS = [
    lambda: make(1, 800),
    lambda: make(2, 2000, sep=0.4),
    Test(lambda: make(3, 200, sep=1.5), "easy problem: stops early"),
]
""",
    compare=dict(rtol=1e-4, atol=1e-6),
    hint1="Pass `eval_set=[(X_valid, y_valid)]`, `eval_metric='binary_logloss'` and `callbacks=[lightgbm.early_stopping(20)]` to `fit`; read `best_iteration_` and `best_score_['valid_0']['binary_logloss']`.",
    hint2="m.fit(X_train, y_train, eval_set=[(X_valid, y_valid)], eval_metric='binary_logloss',\n      callbacks=[lgb.early_stopping(20, verbose=False)])\nm.best_iteration_, m.best_score_['valid_0']['binary_logloss']",
    solution="""
import lightgbm as lgb

def solve(X_train, y_train, X_valid, y_valid):
    m = lgb.LGBMClassifier(n_estimators=1000, learning_rate=0.05, random_state=0, verbose=-1)
    m.fit(X_train, y_train, eval_set=[(X_valid, y_valid)], eval_metric="binary_logloss",
          callbacks=[lgb.early_stopping(20, verbose=False)])
    return m.best_iteration_, float(m.best_score_["valid_0"]["binary_logloss"])
""",
    explanation="""
Early stopping picks the number of trees on a validation set; `predict` then uses `best_iteration_` automatically. LightGBM 4 removed the `early_stopping_rounds=` fit argument: use the callback. Keep a separate **test** set, because the validation set has now been used for tuning.
""",
    docs=["https://lightgbm.readthedocs.io/en/stable/pythonapi/lightgbm.early_stopping.html",
          "https://lightgbm.readthedocs.io/en/stable/pythonapi/lightgbm.LGBMClassifier.html#lightgbm.LGBMClassifier.fit"],
    wrong_solutions=[
        dict(code="""
import lightgbm as lgb

def solve(X_train, y_train, X_valid, y_valid):
    m = lgb.LGBMClassifier(n_estimators=1000, learning_rate=0.05, random_state=0, verbose=-1)
    m.fit(X_train, y_train, eval_set=[(X_valid, y_valid)], eval_metric="binary_logloss")
    return m.best_iteration_, float(m.best_score_["valid_0"]["binary_logloss"])
""", why="no early-stopping callback: all 1000 trees"),
        dict(code="""
import lightgbm as lgb

def solve(X_train, y_train, X_valid, y_valid):
    m = lgb.LGBMClassifier(n_estimators=1000, learning_rate=0.05, random_state=0, verbose=-1)
    m.fit(X_train, y_train, eval_set=[(X_train, y_train)], eval_metric="binary_logloss", callbacks=[lgb.early_stopping(20, verbose=False)])
    return m.best_iteration_, float(m.best_score_["valid_0"]["binary_logloss"])
""", why="early stopping on the training set"),
    ],
),
]
