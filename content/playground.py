"""Open-ended Playground / Mock-interview prompts with reference walkthroughs.

Each walkthrough step's `code` runs at build time, in order, in one fresh
playground namespace (all datasets preloaded, see PLAYGROUND_PRELOAD in
runtime/harness.py; np, pd, plt, sns available). A prompt whose walkthrough
fails (error or warning) is dropped from the page.
"""

PROMPTS = [
dict(
    id="pg-01",
    title="Churn: explore, model, explain",
    datasets=["churn_raw"],
    minutes=45,
    prompt="""
`churn_raw` is a telecom customer table (one row per customer, target `churned`). Explore it, clean what needs cleaning, build a model, and report its **cross-validated ROC AUC** against a baseline, plus the **top 3 drivers** of churn. Finish with one plot you'd show a product manager.
""",
    steps=[
        dict(md="**1. Inspect**: shape, dtypes, missing values, duplicates, target balance. Note `total_charges` is text and `contract` has spelling variants.",
             code="""
df = churn_raw
print(df.shape, "| duplicates:", df.duplicated().sum())
print(df.dtypes.to_string())
print(df.isna().sum()[lambda s: s > 0])
print(df["contract"].value_counts().head(8))
df["churned"].mean()
"""),
        dict(md="**2. Clean**: drop duplicates, parse `total_charges` (blank = new customer = 0), canonicalize `contract`, impute `monthly_charges` by internet type.",
             code="""
CONTRACT = {"month-to-month": "Month-to-month", "month to month": "Month-to-month", "one year": "One year",
            "1 year": "One year", "two year": "Two year", "2 year": "Two year"}
df = churn_raw.drop_duplicates().reset_index(drop=True)
df["total_charges"] = pd.to_numeric(df["total_charges"], errors="coerce").fillna(0.0)
df["contract"] = df["contract"].str.strip().str.lower().map(CONTRACT)
df["monthly_charges"] = df["monthly_charges"].fillna(df.groupby("internet")["monthly_charges"].transform("median"))
X, y = df.drop(columns=["customer_id", "churned"]), df["churned"]
X.dtypes.value_counts()
"""),
        dict(md="**3. Model vs baseline** with stratified, shuffled 5-fold CV. The pipeline refits the preprocessing inside every fold, so there is no leakage.",
             code="""
from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

pre = ColumnTransformer([("num", StandardScaler(), make_column_selector(dtype_include="number")),
                         ("cat", OneHotEncoder(handle_unknown="ignore", drop="if_binary"), make_column_selector(dtype_exclude="number"))])
model = make_pipeline(pre, LogisticRegression(max_iter=1000))
cv = StratifiedKFold(5, shuffle=True, random_state=0)
auc = cross_val_score(model, X, y, cv=cv, scoring="roc_auc")
base = cross_val_score(DummyClassifier(), X, y, cv=cv, scoring="roc_auc")
print(f"logistic AUC {auc.mean():.3f} +/- {auc.std():.3f} | baseline {base.mean():.3f}")
"""),
        dict(md="**4. Drivers**: coefficients on standardized / one-hot features (log-odds per SD or vs the reference level). Cross-check with permutation importance on held-out data if time allows.",
             code="""
model.fit(X, y)
coef = pd.Series(model[-1].coef_[0], index=model[:-1].get_feature_names_out())
coef.reindex(coef.abs().sort_values(ascending=False).index).head(6).round(3)
"""),
        dict(md="**5. One plot for stakeholders**: churn rate by contract type and tenure band. Month-to-month, first-year customers churn the most.",
             code="""
band = pd.cut(df["tenure"], [0, 12, 24, 48, np.inf], right=False, labels=["0-11", "12-23", "24-47", "48+"])
rate = df.groupby(["contract", band], observed=True)["churned"].mean().unstack()
ax = rate.plot.bar(figsize=(7, 3.5), title="Churn rate by contract and tenure (months)")
ax.set_ylabel("churn rate")
rate.round(2)
"""),
        dict(md="**Say out loud**: the AUC vs baseline, the 3 drivers (contract type, tenure, fiber internet / charges), caveats (correlation is not causation; the next steps are calibration and choosing a threshold for a retention campaign)."),
    ],
),
dict(
    id="pg-02",
    title="Salary model: clean, predict, diagnose",
    datasets=["hr_raw"],
    minutes=45,
    prompt="""
`hr_raw` is a messy HR export. Clean it, build a model that predicts `salary`, and report its cross-validated **RMSE** against a mean baseline. Show a residual plot and say what you'd improve.
""",
    steps=[
        dict(md="**1. Clean**: keep each employee's latest record, parse salary text and day-first dates, normalize department spellings.",
             code="""
hr_c = (hr_raw.sort_values("updated").drop_duplicates("employee_id", keep="last")
        .assign(salary=lambda d: pd.to_numeric(d["salary"].str.replace(",", ""), errors="coerce"),
                department=lambda d: d["department"].str.strip().str.title(),
                hire_date=lambda d: pd.to_datetime(d["hire_date"], format="%d/%m/%Y"))
        .dropna(subset=["salary"]))
print(len(hr_raw), "->", len(hr_c), "rows")
hr_c["department"].value_counts()
"""),
        dict(md="**2. Features**: tenure from the hire date, remote as 0/1; keep the categoricals for one-hot encoding.",
             code="""
X = hr_c[["department", "level", "city", "years_experience", "performance"]].assign(
    remote=hr_c["remote"].astype(int),
    tenure_years=(pd.Timestamp("2025-06-01") - hr_c["hire_date"]).dt.days / 365.25)
y = hr_c["salary"]
X.head()
"""),
        dict(md="**3. Model vs baseline** with shuffled 5-fold CV. Ridge on scaled numerics + one-hot categoricals; a gradient-boosting model as a nonlinear comparison.",
             code="""
from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

pre = ColumnTransformer([("num", StandardScaler(), make_column_selector(dtype_include="number")),
                         ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), make_column_selector(dtype_exclude="number"))])
cv = KFold(5, shuffle=True, random_state=0)
for name, est in [("baseline", DummyRegressor()), ("ridge", make_pipeline(pre, Ridge(alpha=1.0))),
                  ("hgb", make_pipeline(pre, HistGradientBoostingRegressor(max_iter=200, random_state=0)))]:
    rmse = -cross_val_score(est, X, y, cv=cv, scoring="neg_root_mean_squared_error")
    print(f"{name:9s} RMSE {rmse.mean():8.0f} +/- {rmse.std():6.0f}")
"""),
        dict(md="**4. Diagnose** with out-of-fold predictions: residuals vs fitted. A funnel shape suggests modelling log(salary): salary effects are multiplicative (city and level multipliers).",
             code="""
from sklearn.model_selection import cross_val_predict
ridge = make_pipeline(pre, Ridge(alpha=1.0))
pred = cross_val_predict(ridge, X, y, cv=cv)
fig, ax = plt.subplots(figsize=(6, 3.5))
ax.scatter(pred, y - pred, s=8, alpha=0.5)
ax.axhline(0, color="gray", linestyle="--")
ax.set(xlabel="Fitted (out of fold)", ylabel="Residual", title="Ridge residuals")
float(np.sqrt(np.mean((y - pred) ** 2)))
"""),
        dict(md="**Next steps to mention**: a log target (`TransformedTargetRegressor`), level x department interactions, checking the error per department, and checking for leakage (no post-hire information in the features)."),
    ],
),
dict(
    id="pg-03",
    title="Retail: revenue trends and customer concentration",
    datasets=["orders", "customers"],
    minutes=40,
    prompt="""
Using `orders` and `customers`, answer: How is monthly revenue trending by region? How concentrated is revenue across customers (what share comes from the top 10%)? What share of customers buy again? Which customer segment is most valuable? Produce one chart.
""",
    steps=[
        dict(md="**1. Join and audit**: attach customer attributes and check for unmatched orders before trusting any segment numbers.",
             code="""
m = orders.merge(customers[["customer_id", "segment"]], on="customer_id", how="left", indicator=True)
print(m["_merge"].value_counts().to_dict())
m = m.drop(columns="_merge")
m.head(3)
"""),
        dict(md="**2. Monthly revenue by region**: a month x region table (`pd.Grouper` on the date) plus month-over-month growth.",
             code="""
monthly = m.pivot_table(index=pd.Grouper(key="order_date", freq="MS"), columns="region",
                        values="revenue", aggfunc="sum", fill_value=0)
ax = monthly.plot(figsize=(7, 3.5), title="Monthly revenue by region")
ax.set_ylabel("revenue")
monthly.sum(axis=1).pct_change().round(3).tail(4)
"""),
        dict(md="**3. Concentration**: the top-10% customers' share of revenue (Pareto).",
             code="""
per_cust = m.groupby("customer_id")["revenue"].sum().sort_values(ascending=False)
top = per_cust.head(int(np.ceil(0.1 * len(per_cust))))
round(top.sum() / per_cust.sum(), 3)
"""),
        dict(md="**4. Repeat rate and segment value**: share of customers with 2+ orders; revenue per customer by segment.",
             code="""
n_orders = m.groupby("customer_id").size()
print("repeat rate:", round((n_orders >= 2).mean(), 3))
(m.groupby("segment").agg(customers=("customer_id", "nunique"), revenue=("revenue", "sum"))
   .assign(rev_per_customer=lambda d: (d["revenue"] / d["customers"]).round(0))
   .sort_values("rev_per_customer", ascending=False))
"""),
        dict(md="**Takeaways to state**: the trend per region, how dependent the business is on a few customers (key-account risk), the repeat rate as a retention KPI, and the most valuable segment per customer."),
    ],
),
dict(
    id="pg-04",
    title="Momentum factor research",
    datasets=["prices", "prices_wide"],
    minutes=45,
    prompt="""
Using the daily price panel, test a **cross-sectional momentum** signal: each month-end, rank stocks by their past 60-day return skipping the most recent 5 days, and evaluate the next month's returns. Report the mean rank IC, a top-minus-bottom quintile spread and its annualized Sharpe ratio, without lookahead.
""",
    steps=[
        dict(md="**1. Signal at month ends**: past 60-day return ending 5 days ago, built from **past prices only**.",
             code="""
px = prices_wide
mom = px.shift(5) / px.shift(65) - 1
me = px.resample("ME").last().index
dates = px.index[px.index.searchsorted(me, side="right") - 1]    # last trading day of each month
signal = mom.loc[dates]
signal.dropna(how="all").shape
"""),
        dict(md="**2. Label**: next month's return from each rebalance date to the next one. Here the forward shift is correct, because it's the label.",
             code="""
month_px = px.loc[dates]
fwd = month_px.shift(-1) / month_px - 1
panel = pd.concat({"signal": signal.stack(), "fwd": fwd.stack()}, axis=1).dropna()
panel.index.names = ["date", "ticker"]
panel.groupby(level="date").size().tail(3)
"""),
        dict(md="**3. Rank IC per date** and its t-stat.",
             code="""
ic = panel.groupby(level="date")[["signal", "fwd"]].apply(lambda g: g["signal"].corr(g["fwd"], method="spearman"))
print(f"mean IC {ic.mean():.3f}, t-stat {ic.mean() / ic.std() * np.sqrt(len(ic)):.2f}, hit rate {(ic > 0).mean():.2f}")
ic.tail(3).round(3)
"""),
        dict(md="**4. Quintile long-short**: rank within each date, then top minus bottom quintile, annualized Sharpe (monthly data: x sqrt(12)).",
             code="""
q = panel.groupby(level="date")["signal"].transform(lambda s: pd.qcut(s.rank(method="first"), 5, labels=False))
ls = panel["fwd"].groupby([panel.index.get_level_values("date"), q]).mean().unstack()
spread = ls[4] - ls[0]
sharpe = spread.mean() / spread.std() * np.sqrt(12)
ax = (1 + spread).cumprod().plot(figsize=(6, 3), title="Momentum Q5 - Q1 (cumulative)")
round(float(sharpe), 2)
"""),
        dict(md="**Caveats to raise**: 20 tickers is a tiny cross-section (noisy quintiles), the backtest is short, no transaction costs, monthly labels overlap nothing here, and the data is simulated (no true momentum premium, so an IC near 0 is the honest answer)."),
    ],
),
dict(
    id="pg-05",
    title="Sensor anomalies",
    datasets=["sensors"],
    minutes=35,
    prompt="""
`sensors` holds 15-minute temperature and humidity readings from 4 sensors, with gaps, NaNs and spikes. Build a regular, gap-filled series per sensor, flag anomalous temperature spikes with a robust rule, and report how many each sensor had. Plot one sensor with its anomalies.
""",
    steps=[
        dict(md="**1. Regularize**: a wide sensor x 15-min grid (missing rows become NaN), then time interpolation for short gaps only.",
             code="""
wide = sensors.pivot(index="timestamp", columns="sensor_id", values="temperature").asfreq("15min")
print("missing cells:", int(wide.isna().sum().sum()))
filled = wide.interpolate(method="time", limit=4)
filled.isna().sum()
"""),
        dict(md="**2. Robust spike rule**: deviation from a centered rolling median, scaled by the rolling MAD. Centered is fine here: this is offline cleaning, not a trading signal.",
             code="""
med = filled.rolling(9, center=True, min_periods=5).median()
mad = (filled - med).abs().rolling(9, center=True, min_periods=5).median()
z = (filled - med) / (1.4826 * mad)
flags = z.abs() > 5
flags.sum()
"""),
        dict(md="**3. Plot one sensor** with its flagged points.",
             code="""
s, f = filled["S1"], flags["S1"]
fig, ax = plt.subplots(figsize=(8, 3))
ax.plot(s.index, s.values, lw=0.8)
ax.scatter(s.index[f], s[f], color="red", s=15, label="anomaly", zorder=3)
ax.set(title="Sensor S1 temperature", ylabel="°C")
ax.legend()
int(f.sum())
"""),
        dict(md="**Discuss**: why a robust rule (a mean/std z-score is inflated by the spikes themselves), the interpolation limit (don't invent long stretches), and replacing flagged spikes with NaN before any downstream aggregation."),
    ],
),
dict(
    id="pg-06",
    title="Customer segmentation",
    datasets=["orders"],
    minutes=40,
    prompt="""
Segment customers from their purchase behaviour in `orders`. Build features, choose the number of clusters with a justified criterion, describe each segment in business terms, and visualize them in 2-D.
""",
    steps=[
        dict(md="**1. RFM features** with a fixed snapshot date.",
             code="""
snap = orders["order_date"].max() + pd.Timedelta(days=1)
g = orders.groupby("customer_id")
rfm = pd.DataFrame({"recency": (snap - g["order_date"].max()).dt.days,
                    "frequency": g.size(), "monetary": g["revenue"].sum()})
rfm.describe().round(1)
"""),
        dict(md="**2. Transform and scale**: log the skewed counts and amounts, then standardize.",
             code="""
from sklearn.preprocessing import StandardScaler
Xs = pd.DataFrame(StandardScaler().fit_transform(rfm.assign(frequency=np.log1p(rfm["frequency"]),
                                                           monetary=np.log1p(rfm["monetary"]))),
                  index=rfm.index, columns=rfm.columns)
Xs.std().round(2)
"""),
        dict(md="**3. Choose k** by silhouette (inertia alone always prefers more clusters).",
             code="""
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
scores = {k: silhouette_score(Xs, KMeans(n_clusters=k, n_init=10, random_state=0).fit_predict(Xs)) for k in range(2, 7)}
best = max(scores, key=scores.get)
labels = pd.Series(KMeans(n_clusters=best, n_init=10, random_state=0).fit_predict(Xs), index=Xs.index, name="cluster")
print({k: round(v, 3) for k, v in scores.items()}, "-> k =", best)
"""),
        dict(md="**4. Profile in original units** and map with PCA.",
             code="""
from sklearn.decomposition import PCA
profile = rfm.groupby(labels).mean().round(1).assign(size=labels.value_counts())
coords = PCA(n_components=2).fit_transform(Xs)
fig, ax = plt.subplots(figsize=(5, 4))
sc = ax.scatter(coords[:, 0], coords[:, 1], c=labels, cmap="tab10", s=15)
ax.set(title="Customer segments (PCA)", xlabel="PC1", ylabel="PC2")
profile
"""),
        dict(md="**Name the segments** from the profile (for example 'recent high spenders', 'lapsed one-timers') and propose one action per segment. Mention the instability of k-means (seeds, k) and alternatives (GMM, hierarchical clustering)."),
    ],
),
dict(
    id="pg-07",
    title="A/B test readout",
    datasets=["ab"],
    minutes=35,
    prompt="""
`ab` is a two-arm experiment (group A = control, B = treatment). Did B improve **conversion**? Did it change **revenue per user**? Give effect sizes with confidence intervals, the tests you used and why, check for a device mix problem, and make a recommendation.
""",
    steps=[
        dict(md="**1. Sanity checks**: sample sizes per arm (sample ratio mismatch?) and device mix per arm.",
             code="""
print(ab["group"].value_counts().to_dict())
pd.crosstab(ab["group"], ab["device"], normalize="index").round(3)
"""),
        dict(md="**2. Conversion**: rates, absolute lift with a 95% normal-approximation CI, and a two-proportion z-test.",
             code="""
from statsmodels.stats.proportion import proportions_ztest
s = ab.groupby("group")["converted"].agg(["sum", "count", "mean"])
pa, pb = s.loc["A", "mean"], s.loc["B", "mean"]
se = np.sqrt(pa * (1 - pa) / s.loc["A", "count"] + pb * (1 - pb) / s.loc["B", "count"])
z, p = proportions_ztest(s["sum"].to_numpy(), s["count"].to_numpy())
print(f"A {pa:.4f}  B {pb:.4f}  lift {pb - pa:+.4f}  95% CI [{pb - pa - 1.96 * se:+.4f}, {pb - pa + 1.96 * se:+.4f}]  p={p:.4f}")
"""),
        dict(md="**3. Revenue per user**: heavy-tailed and zero-inflated, so use Welch's t-test plus a bootstrap CI for the difference in means.",
             code="""
from scipy import stats
ra, rb = ab.loc[ab["group"] == "A", "revenue"].to_numpy(), ab.loc[ab["group"] == "B", "revenue"].to_numpy()
t = stats.ttest_ind(rb, ra, equal_var=False)
rng = np.random.default_rng(0)
boot = [rng.choice(rb, len(rb)).mean() - rng.choice(ra, len(ra)).mean() for _ in range(2000)]
print(f"diff {rb.mean() - ra.mean():+.3f}  Welch p={t.pvalue:.4f}  bootstrap 95% CI {np.percentile(boot, [2.5, 97.5]).round(3)}")
"""),
        dict(md="**4. Segment check**: lift by device. Is the effect consistent across devices?",
             code="""
(ab.pivot_table(index="device", columns="group", values="converted", aggfunc="mean")
   .assign(lift=lambda d: d["B"] - d["A"]).round(4))
"""),
        dict(md="**Recommendation**: ship only if the conversion CI excludes 0 and is consistent across segments; mention the minimum detectable effect and power, avoiding peeking (a fixed horizon), and multiple-testing caution if you slice by many segments."),
    ],
),
dict(
    id="pg-08",
    title="Screening model with a recall target",
    datasets=["sklearn: load_breast_cancer"],
    minutes=45,
    prompt="""
Using scikit-learn's bundled `load_breast_cancer()` (malignant = class 0 in that dataset), build a classifier for **malignancy**, compare at least two model families with cross-validated ROC AUC, then choose a decision threshold that catches **at least 95% of malignant cases** (recall), and report the precision you get at that threshold, without tuning on the test data.
""",
    steps=[
        dict(md="**1. Load and frame the target**: make malignant the positive class (1).",
             code="""
from sklearn.datasets import load_breast_cancer
data = load_breast_cancer(as_frame=True)
X, y = data.data, (data.target == 0).astype(int)      # 1 = malignant
print(X.shape, "malignant share:", round(y.mean(), 3))
"""),
        dict(md="**2. Hold out a test set**, then compare model families with CV on the training part only.",
             code="""
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, stratify=y, random_state=0)
cv = StratifiedKFold(5, shuffle=True, random_state=0)
models = {"logreg": make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=2000)),
          "hgb": HistGradientBoostingClassifier(max_iter=100, random_state=0)}
for name, m in models.items():
    s = cross_val_score(m, X_tr, y_tr, cv=cv, scoring="roc_auc")
    print(f"{name:7s} AUC {s.mean():.4f} +/- {s.std():.4f}")
"""),
        dict(md="**3. Choose the threshold on out-of-fold training predictions** (never on the test set): the highest threshold that still gives recall >= 0.95.",
             code="""
from sklearn.metrics import precision_recall_curve
from sklearn.model_selection import cross_val_predict
best = models["logreg"]
oof = cross_val_predict(best, X_tr, y_tr, cv=cv, method="predict_proba")[:, 1]
p, r, t = precision_recall_curve(y_tr, oof)
thr = float(t[r[:-1] >= 0.95].max())
round(thr, 3)
"""),
        dict(md="**4. Final check on the untouched test set** at that threshold.",
             code="""
from sklearn.metrics import confusion_matrix, precision_score, recall_score
best.fit(X_tr, y_tr)
pred = (best.predict_proba(X_te)[:, 1] >= thr).astype(int)
print("recall", round(recall_score(y_te, pred), 3), "precision", round(precision_score(y_te, pred), 3))
confusion_matrix(y_te, pred)
"""),
        dict(md="**Discuss**: why recall drives the threshold (a missed cancer costs far more than a false alarm), why the threshold is picked out-of-fold, and why test recall can dip below 0.95 by chance on a small test set (report a CI or re-check with repeated CV)."),
    ],
),
]
