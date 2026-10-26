"""Shared dataset generators for LeetStats.

Every generator is deterministic for a given (seed, size) and uses only
np.random.default_rng, so results are identical in CPython and Pyodide.
Problems call these as D.<name>(seed=..., n=...). Keep them fast (< 50 ms
at default sizes) and never change existing behaviour: problems and saved
progress depend on it. Add new generators or new keyword options instead.
"""
import io

import numpy as np
import pandas as pd

REGIONS = ["North", "South", "East", "West"]
CATEGORIES = ["Electronics", "Clothing", "Home", "Sports", "Books"]
SEGMENTS = ["Consumer", "Corporate", "Small Business"]
DEPARTMENTS = ["Engineering", "Sales", "Marketing", "Finance", "HR"]
LEVELS = ["Junior", "Mid", "Senior", "Lead"]
CITIES = ["London", "Paris", "Berlin", "New York"]
CONTRACTS = ["Month-to-month", "One year", "Two year"]
INTERNET = ["DSL", "Fiber optic", "None"]
PAYMENTS = ["Electronic check", "Mailed check", "Bank transfer", "Credit card"]
TICKERS = ["ALFA", "BRVO", "CHRL", "DLTA", "ECHO", "FXTR", "GOLF", "HTLX",
           "INDG", "JULT", "KILO", "LIMA", "MIKE", "NOVA", "OSCR", "PAPA",
           "QBEC", "ROMO", "SIER", "TANG", "UNIF", "VICT", "WHSK", "XRAY",
           "YANK", "ZULU"]


def _rng(seed, salt=0):
    return np.random.default_rng([int(seed), int(salt)])


def _messy_case(rng, values, share=0.25):
    """Randomly lower/upper-case or pad a share of string values."""
    values = np.asarray(values, dtype=object).copy()
    pick = rng.random(len(values)) < share
    style = rng.integers(0, 4, len(values))
    for i in np.flatnonzero(pick):
        v = values[i]
        values[i] = [v.lower(), v.upper(), " " + v, v + " "][style[i]]
    return values


# --------------------------------------------------------------------------
# Retail: customers + orders
# --------------------------------------------------------------------------
def customers(seed=0, n=40):
    """customer_id (C001..), name, region, segment, signup_date, age."""
    rng = _rng(seed, 1)
    first = np.array(["Ana", "Ben", "Chloe", "Dev", "Eva", "Femi", "Gus", "Hana",
                      "Ivan", "Jade", "Kofi", "Lea", "Mo", "Nina", "Omar", "Pia"])
    last = np.array(["Smith", "Garcia", "Chen", "Patel", "Muller", "Rossi",
                     "Kim", "Silva", "Novak", "Dubois", "Okafor", "Berg"])
    return pd.DataFrame({
        "customer_id": [f"C{i:03d}" for i in range(1, n + 1)],
        "name": [f"{a} {b}" for a, b in zip(rng.choice(first, n), rng.choice(last, n))],
        "region": rng.choice(REGIONS, n, p=[0.3, 0.25, 0.25, 0.2]),
        "segment": rng.choice(SEGMENTS, n, p=[0.6, 0.25, 0.15]),
        "signup_date": pd.Timestamp("2022-01-01")
        + pd.to_timedelta(rng.integers(0, 730, n), unit="D"),
        "age": rng.integers(18, 76, n),
    })


def orders(seed=0, n=200, n_customers=40, unknown_share=0.03):
    """One row per order, sorted by order_id (dates increase with order_id).

    Columns: order_id, customer_id, order_date, region, category, quantity,
    unit_price, revenue. Region is the customer's region. About
    `unknown_share` of orders reference customers missing from
    customers(seed, n_customers) (ids above the range) to exercise joins.
    """
    rng = _rng(seed, 2)
    cust = customers(seed, n_customers)
    # Customers differ in how often they buy (heavy-tailed activity).
    activity = rng.gamma(0.8, 1.0, n_customers)
    cid_idx = rng.choice(n_customers, n, p=activity / activity.sum())
    cid = cust["customer_id"].to_numpy()[cid_idx].astype(object)
    region = cust["region"].to_numpy()[cid_idx].astype(object)
    unknown = rng.random(n) < unknown_share
    k = int(unknown.sum())
    cid[unknown] = [f"C{n_customers + 1 + j:03d}" for j in rng.integers(0, 5, k)]
    region[unknown] = rng.choice(REGIONS, k)
    category = rng.choice(CATEGORIES, n, p=[0.25, 0.25, 0.2, 0.15, 0.15])
    base = pd.Series(category).map({"Electronics": 180.0, "Clothing": 40.0, "Home": 70.0,
                                    "Sports": 55.0, "Books": 15.0}).to_numpy()
    unit_price = np.round(base * rng.lognormal(0, 0.35, n), 2)
    quantity = rng.poisson(1.3, n) + 1
    offsets = np.sort(rng.integers(0, 366, n))
    df = pd.DataFrame({
        "order_id": np.arange(1001, 1001 + n),
        "customer_id": cid.astype(str),
        "order_date": pd.Timestamp("2024-01-01") + pd.to_timedelta(offsets, unit="D"),
        "region": region.astype(str),
        "category": category,
        "quantity": quantity.astype("int64"),
        "unit_price": unit_price,
    })
    df["revenue"] = np.round(df["quantity"] * df["unit_price"], 2)
    return df


def orders_raw(seed=0, n=200, n_customers=40, dup_share=0.04):
    """A messy export of orders(): string dates, numbers as text, spelling
    variants, exact duplicate rows and a discount column with NaNs.

    Columns (all text except order_id and discount): order_id, customer_id,
    order_date ('YYYY-MM-DD'), region (case/whitespace variants), category,
    quantity (digits or 'unknown'), unit_price ('$1,234.50'), discount.
    """
    rng = _rng(seed, 3)
    df = orders(seed, n, n_customers)
    out = pd.DataFrame({
        "order_id": df["order_id"],
        "customer_id": df["customer_id"],
        "order_date": df["order_date"].dt.strftime("%Y-%m-%d"),
        "region": _messy_case(rng, df["region"].to_numpy(), 0.25).astype(str),
        "category": df["category"],
    })
    qty = df["quantity"].astype(str).to_numpy().astype(object)
    qty[rng.random(n) < 0.04] = "unknown"
    out["quantity"] = qty.astype(str)
    out["unit_price"] = ["${:,.2f}".format(v) for v in df["unit_price"]]
    disc = rng.choice([0.0, 0.05, 0.1, 0.2], n, p=[0.55, 0.2, 0.15, 0.1])
    disc[rng.random(n) < 0.1] = np.nan
    out["discount"] = disc
    k = max(1, int(round(n * dup_share))) if (n >= 5 and dup_share > 0) else 0
    if k:
        dups = out.iloc[rng.choice(n, k, replace=False)]
        out = pd.concat([out, dups]).sort_values("order_id", kind="stable").reset_index(drop=True)
    return out


def orders_csv(seed=0, n=12, sep=",", decimal=".", na="n/a"):
    """orders_raw() written as CSV text. With decimal=',' the discount column
    uses a comma decimal separator (sep should then be ';')."""
    df = orders_raw(seed, n, dup_share=0)
    return df.to_csv(index=False, sep=sep, decimal=decimal, na_rep=na)


# --------------------------------------------------------------------------
# HR / salary table
# --------------------------------------------------------------------------
def hr(seed=0, n=150, missing_share=0.06):
    """Employees: employee_id, department, level, city, remote, hire_date,
    years_experience, performance (1-5), salary (some NaN), bonus (NaN when
    no bonus). Salary depends on department, level, experience and city."""
    rng = _rng(seed, 4)
    dept = rng.choice(DEPARTMENTS, n, p=[0.3, 0.25, 0.15, 0.15, 0.15])
    level_idx = rng.choice(4, n, p=[0.3, 0.35, 0.25, 0.1])
    level = np.array(LEVELS)[level_idx]
    exp_years = np.round(np.clip(level_idx * 3.5 + rng.gamma(2.0, 1.2, n), 0.5, 35), 1)
    city = rng.choice(CITIES, n, p=[0.35, 0.25, 0.2, 0.2])
    remote = rng.random(n) < 0.3
    dept_base = pd.Series(dept).map({"Engineering": 62000, "Sales": 48000, "Marketing": 50000,
                                     "Finance": 58000, "HR": 45000}).to_numpy()
    city_mult = pd.Series(city).map({"London": 1.1, "Paris": 1.0, "Berlin": 0.95,
                                     "New York": 1.25}).to_numpy()
    salary = (dept_base * (1 + 0.28 * level_idx) + 1400 * exp_years) * city_mult
    salary = np.round(salary * rng.lognormal(0, 0.08, n), -2)
    perf = np.clip(np.round(rng.normal(3.2, 0.9, n)), 1, 5).astype("int64")
    bonus = np.round(salary * (0.02 * perf) * rng.uniform(0.6, 1.4, n), -1)
    bonus[rng.random(n) < 0.25] = np.nan
    salary = salary.astype(float)
    salary[rng.random(n) < missing_share] = np.nan
    hire = pd.Timestamp("2025-01-01") - pd.to_timedelta(
        np.round(np.minimum(exp_years, 14) * 365 * rng.uniform(0.2, 1.0, n)).astype("int64"), unit="D")
    return pd.DataFrame({
        "employee_id": np.arange(101, 101 + n),
        "department": dept,
        "level": level,
        "city": city,
        "remote": remote,
        "hire_date": hire.normalize(),
        "years_experience": exp_years,
        "performance": perf,
        "salary": salary,
        "bonus": bonus,
    })


def hr_raw(seed=0, n=150, dup_share=0.05):
    """A messy HR export: salary as text ('85,000', 'n/a'), department with
    case/whitespace variants, hire_date as 'DD/MM/YYYY' strings, and some
    employees appearing twice (an older and a newer record; the newer one
    has a later `updated` date)."""
    rng = _rng(seed, 5)
    df = hr(seed, n)
    out = df.copy()
    out["department"] = _messy_case(rng, df["department"].to_numpy(), 0.3).astype(str)
    sal = np.array(["{:,.0f}".format(v) if v == v else "n/a" for v in df["salary"]], dtype=object)
    out["salary"] = sal.astype(str)
    out["hire_date"] = df["hire_date"].dt.strftime("%d/%m/%Y")
    out["updated"] = pd.Timestamp("2025-06-01") - pd.to_timedelta(rng.integers(30, 120, n), unit="D")
    k = max(1, int(round(n * dup_share))) if (n >= 5 and dup_share > 0) else 0
    if k:
        old = out.iloc[rng.choice(n, k, replace=False)].copy()
        old["updated"] = old["updated"] - pd.to_timedelta(rng.integers(100, 400, k), unit="D")
        old_sal = df.loc[old.index, "salary"] * 0.95
        old["salary"] = ["{:,.0f}".format(v) if v == v else "n/a" for v in np.round(old_sal, -2)]
        out = pd.concat([out, old]).sample(frac=1, random_state=int(rng.integers(1 << 30))).reset_index(drop=True)
    return out.drop(columns=["bonus"])


# --------------------------------------------------------------------------
# Churn table (binary classification)
# --------------------------------------------------------------------------
def churn(seed=0, n=600, messy=False):
    """Telecom-style churn table, one row per customer.

    Columns: customer_id, tenure (months), contract, internet, payment_method,
    monthly_charges, total_charges, support_calls, senior (0/1), region,
    churned (0/1, about 25-30% positive).
    messy=True: total_charges stored as text (blank ' ' when tenure == 0),
    ~3% NaN in monthly_charges, contract spelling variants, ~2% duplicate rows.
    """
    rng = _rng(seed, 6)
    contract = rng.choice(CONTRACTS, n, p=[0.55, 0.25, 0.2])
    m2m = contract == "Month-to-month"
    tenure = np.where(m2m, rng.gamma(1.2, 12, n), rng.gamma(3.0, 12, n))
    tenure = np.clip(np.round(tenure), 0, 72).astype("int64")
    tenure[rng.random(n) < 0.02] = 0
    internet = rng.choice(INTERNET, n, p=[0.35, 0.45, 0.2])
    fiber = internet == "Fiber optic"
    base = np.select([internet == "DSL", fiber], [55.0, 85.0], 25.0)
    monthly = np.round(base + rng.normal(0, 8, n), 2)
    total = np.round(monthly * tenure * rng.uniform(0.95, 1.05, n), 2)
    payment = rng.choice(PAYMENTS, n, p=[0.35, 0.2, 0.22, 0.23])
    calls = rng.poisson(np.where(fiber, 1.8, 1.0))
    senior = (rng.random(n) < 0.16).astype("int64")
    logit = (-2.1 + 1.3 * m2m - 0.035 * tenure + 0.012 * (monthly - 60)
             + 0.35 * calls + 0.45 * fiber + 0.4 * (payment == "Electronic check")
             + 0.3 * senior)
    churned = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype("int64")
    df = pd.DataFrame({
        "customer_id": [f"K{seed % 100:02d}{i:04d}" for i in range(n)],
        "tenure": tenure,
        "contract": contract,
        "internet": internet,
        "payment_method": payment,
        "monthly_charges": monthly,
        "total_charges": np.where(tenure == 0, np.nan, total),
        "support_calls": calls.astype("int64"),
        "senior": senior,
        "region": rng.choice(REGIONS, n),
        "churned": churned,
    })
    if messy:
        df["total_charges"] = [" " if v != v else f"{v:.2f}" for v in df["total_charges"]]
        mc = df["monthly_charges"].to_numpy().copy()
        mc[rng.random(n) < 0.03] = np.nan
        df["monthly_charges"] = mc
        variants = {"Month-to-month": ["month-to-month", "Month to month"],
                    "One year": ["one year", "1 year"], "Two year": ["two year", "2 year"]}
        c = df["contract"].to_numpy().astype(object)
        for i in np.flatnonzero(rng.random(n) < 0.08):
            c[i] = variants[c[i]][rng.integers(0, 2)]
        df["contract"] = c.astype(str)
        k = int(round(n * 0.02))
        if k:
            df = pd.concat([df, df.iloc[rng.choice(n, k, replace=False)]], ignore_index=True)
    return df


# --------------------------------------------------------------------------
# Markets: daily price panel and monthly factor panel
# --------------------------------------------------------------------------
def prices(seed=0, n_days=250, n_tickers=20, start="2023-01-02", gaps=False):
    """Long daily panel sorted by (date, ticker): date, ticker, close, volume.

    Returns follow a one-factor model r = beta * market + noise, so tickers
    are correlated. gaps=True drops ~3% of rows at random (missing days).
    """
    rng = _rng(seed, 7)
    dates = pd.bdate_range(start, periods=n_days)
    tick = TICKERS[:n_tickers]
    mkt = rng.normal(0.0004, 0.011, n_days)
    beta = rng.uniform(0.5, 1.6, n_tickers)
    vol = rng.uniform(0.008, 0.022, n_tickers)
    drift = rng.normal(0.0002, 0.0004, n_tickers)
    r = drift + mkt[:, None] * beta + rng.normal(0, 1, (n_days, n_tickers)) * vol
    p0 = np.round(rng.uniform(20, 300, n_tickers), 2)
    close = np.round(p0 * np.cumprod(1 + r, axis=0), 2)
    volume = np.round(rng.lognormal(13, 0.5, (n_days, n_tickers)) / 100) * 100
    df = pd.DataFrame({
        "date": np.repeat(dates, n_tickers),
        "ticker": np.tile(tick, n_days),
        "close": close.ravel(),
        "volume": volume.ravel().astype("int64"),
    })
    if gaps:
        df = df[rng.random(len(df)) >= 0.03].reset_index(drop=True)
    return df


def prices_wide(seed=0, n_days=250, n_tickers=20, start="2023-01-02"):
    """Close prices as a wide DataFrame: DatetimeIndex 'date' x ticker columns."""
    df = prices(seed, n_days, n_tickers, start)
    wide = df.pivot(index="date", columns="ticker", values="close")
    wide.columns.name = None
    return wide


def market_returns(seed=0, n_days=500, beta=1.2, alpha=0.0002, idio=0.012):
    """(stock, market) daily simple returns as two Series on business days,
    with stock = alpha + beta * market + noise."""
    rng = _rng(seed, 8)
    idx = pd.bdate_range("2022-01-03", periods=n_days, name="date")
    m = rng.normal(0.0004, 0.01, n_days)
    s = alpha + beta * m + rng.normal(0, idio, n_days)
    return pd.Series(s, idx, name="stock"), pd.Series(m, idx, name="market")


def factor_panel(seed=0, n_dates=36, n_tickers=60, ic=0.08):
    """Monthly cross-sectional panel sorted by (date, ticker).

    Columns: date (month end), ticker, momentum, value, size, fwd_ret
    (next month's return). momentum carries a weak signal (rank IC ~ `ic`),
    signals have a few NaNs and fat-tailed outliers.
    """
    rng = _rng(seed, 9)
    dates = pd.date_range("2021-01-31", periods=n_dates, freq="ME")
    names = [f"S{i:03d}" for i in range(n_tickers)]
    shape = (n_dates, n_tickers)
    mom = rng.standard_t(4, shape)
    value = rng.normal(0, 1, shape)
    size = rng.normal(8, 1.5, shape)
    noise = rng.normal(0, 1, shape)
    fwd = 0.06 * (ic * mom / mom.std() + np.sqrt(1 - ic ** 2) * noise) + 0.005
    mom = mom.copy()
    mom[rng.random(shape) < 0.02] = np.nan
    value[rng.random(shape) < 0.02] = np.nan
    return pd.DataFrame({
        "date": np.repeat(dates, n_tickers),
        "ticker": np.tile(names, n_dates),
        "momentum": np.round(mom.ravel(), 4),
        "value": np.round(value.ravel(), 4),
        "size": np.round(size.ravel(), 3),
        "fwd_ret": np.round(fwd.ravel(), 5),
    })


# --------------------------------------------------------------------------
# IoT sensors
# --------------------------------------------------------------------------
def sensors(seed=0, n_sensors=3, days=2, freq="15min", drop_share=0.05, nan_share=0.03,
            spike_share=0.01):
    """Long table sorted by (sensor_id, timestamp): timestamp, sensor_id,
    temperature, humidity. Daily temperature cycle per sensor; random
    missing rows (gaps), NaN readings and occasional spikes (outliers)."""
    rng = _rng(seed, 10)
    ts = pd.date_range("2024-03-01", periods=int(days * pd.Timedelta("1D") / pd.Timedelta(freq)),
                       freq=freq)
    frames = []
    for k in range(n_sensors):
        hours = ((ts - ts[0]) / pd.Timedelta("1h")).to_numpy()
        temp = 20 + 2 * k + 4 * np.sin(2 * np.pi * (hours - 9) / 24) + rng.normal(0, 0.4, len(ts))
        hum = 55 - 1.5 * (temp - 20) + rng.normal(0, 2, len(ts))
        spikes = rng.random(len(ts)) < spike_share
        temp[spikes] += rng.choice([-1, 1], spikes.sum()) * rng.uniform(15, 25, spikes.sum())
        temp[rng.random(len(ts)) < nan_share] = np.nan
        f = pd.DataFrame({"timestamp": ts, "sensor_id": f"S{k + 1}",
                          "temperature": np.round(temp, 2), "humidity": np.round(hum, 1)})
        frames.append(f[rng.random(len(ts)) >= drop_share])
    return pd.concat(frames, ignore_index=True)


# --------------------------------------------------------------------------
# A/B test
# --------------------------------------------------------------------------
def ab_test(seed=0, n=2000, lift=0.02, base_rate=0.10):
    """One row per user: user_id, group ('A'/'B'), device, converted (0/1),
    revenue (0 when not converted), time_on_site (seconds)."""
    rng = _rng(seed, 11)
    group = rng.choice(["A", "B"], n)
    device = rng.choice(["desktop", "mobile", "tablet"], n, p=[0.45, 0.45, 0.1])
    p = base_rate + lift * (group == "B") - 0.02 * (device == "mobile")
    converted = (rng.random(n) < p).astype("int64")
    revenue = np.where(converted == 1, np.round(rng.lognormal(3.5, 0.6, n), 2), 0.0)
    tos = np.round(rng.gamma(2.0, 60, n) * (1 + 0.1 * (group == "B")), 1)
    return pd.DataFrame({"user_id": np.arange(1, n + 1), "group": group, "device": device,
                         "converted": converted, "revenue": revenue, "time_on_site": tos})


def to_csv_text(df, **kwargs):
    """DataFrame -> CSV string (index=False unless given)."""
    kwargs.setdefault("index", False)
    buf = io.StringIO()
    df.to_csv(buf, **kwargs)
    return buf.getvalue()


ALL = ["customers", "orders", "orders_raw", "orders_csv", "hr", "hr_raw", "churn",
       "prices", "prices_wide", "market_returns", "factor_panel", "sensors", "ab_test"]
