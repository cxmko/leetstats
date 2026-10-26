SECTION = "plotting"

PROBLEMS = [
dict(
    id="pl-001",
    title="Price line with a date axis",
    difficulty="Easy",
    tags=["figure basics", "time series"],
    signature="def solve(prices: pd.DataFrame, ticker: str) -> plt.Axes:",
    statement="""
`prices` is a long daily panel with columns `date` (datetime), `ticker`, `close`, `volume`.

Create a new figure and plot the closing price of `ticker` against `date` as a single line. Set the title to `"<ticker> close"` (e.g. `"ALFA close"`), the x-label to `"Date"` and the y-label to `"Price"`.

Return the **Axes**. The x-axis must be a real date axis (plot the datetimes, not row numbers).
""",
    setup="""
EXAMPLE = lambda: {"prices": D.prices(seed=0, n_days=120, n_tickers=4), "ticker": "ALFA"}
""",
    tests="""
TESTS = [
    lambda: {"prices": D.prices(seed=1, n_days=60, n_tickers=5), "ticker": "CHRL"},
    lambda: {"prices": D.prices(seed=2, n_days=250, n_tickers=20), "ticker": "TANG"},
    Test(lambda: {"prices": D.prices(seed=3, n_days=40, n_tickers=3, gaps=True), "ticker": "BRVO"}, "missing days"),
]
""",
    plot=dict(returns="Axes", checks=["type", "lines", "line_points", "title", "xlabel", "ylabel", "xdate"]),
    hint1="Use the object-oriented API: `fig, ax = plt.subplots()`, then `ax.plot(x, y)` and `ax.set(...)`.",
    hint2="fig, ax = plt.subplots(figsize=(8, 3))\nax.plot(s['date'], s['close'])\nax.set(title=f'{ticker} close', xlabel='Date', ylabel='Price')",
    solution="""
def solve(prices, ticker):
    s = prices[prices["ticker"] == ticker]
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.plot(s["date"], s["close"])
    ax.set(title=f"{ticker} close", xlabel="Date", ylabel="Price")
    return ax
""",
    explanation="""
`plt.subplots()` gives you explicit `fig` and `ax` handles; everything else is a method on `ax`, which scales to multi-panel figures (the `plt.plot` state machine does not). Passing datetimes as x makes matplotlib install a date locator/formatter; plotting `s['close'].to_numpy()` alone would put row numbers on the x-axis.
""",
    docs=["https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.subplots.html",
          "https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.plot.html",
          "https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.set.html"],
    wrong_solutions=[
        dict(code="""
def solve(prices, ticker):
    s = prices[prices["ticker"] == ticker]
    fig, ax = plt.subplots()
    ax.plot(s["close"].to_numpy())
    ax.set(title=f"{ticker} close", xlabel="Date", ylabel="Price")
    return ax
""", why="row numbers on the x-axis"),
        dict(code="""
def solve(prices, ticker):
    fig, ax = plt.subplots()
    ax.plot(prices["date"], prices["close"])
    ax.set(title=f"{ticker} close", xlabel="Date", ylabel="Price")
    return ax
""", why="forgot to filter the ticker"),
        dict(code="""
def solve(prices, ticker):
    s = prices[prices["ticker"] == ticker]
    fig, ax = plt.subplots()
    ax.plot(s["date"], s["close"])
    ax.set_title(ticker)
    return ax
""", why="wrong title and missing labels"),
    ],
),
dict(
    id="pl-002",
    title="Scatter coloured by group",
    difficulty="Easy",
    tags=["relationships", "legends"],
    signature="def solve(churn: pd.DataFrame) -> plt.Axes:",
    statement="""
Plot `monthly_charges` (y) against `tenure` (x) for the churn table as a scatter plot with **one scatter series per `contract` type**, each labelled with the contract name, and show a legend. Label the axes `"Tenure (months)"` and `"Monthly charges"`. Return the Axes.
""",
    setup="""
EXAMPLE = lambda: {"churn": D.churn(seed=0, n=300)}
""",
    tests="""
TESTS = [
    lambda: {"churn": D.churn(seed=1, n=100)},
    lambda: {"churn": D.churn(seed=2, n=2000)},
    Test(lambda: {"churn": D.churn(seed=3, n=200).query("contract != 'Two year'")}, "two groups"),
]
""",
    plot=dict(returns="Axes", checks=["type", "scatter_groups", "points", "legend", "xlabel", "ylabel"]),
    hint1="Loop over `df.groupby('contract')` and call `ax.scatter(x, y, label=name)` for each group, then `ax.legend()`.",
    hint2="fig, ax = plt.subplots()\nfor name, g in churn.groupby('contract'):\n    ax.scatter(g['tenure'], g['monthly_charges'], label=name, s=10)\nax.legend()",
    solution="""
def solve(churn):
    fig, ax = plt.subplots()
    for name, g in churn.groupby("contract"):
        ax.scatter(g["tenure"], g["monthly_charges"], label=name, s=10, alpha=0.6)
    ax.set(xlabel="Tenure (months)", ylabel="Monthly charges")
    ax.legend(title="Contract")
    return ax
""",
    explanation="""
One `scatter` call per group gives each group its own colour and legend entry; `label=` is what `legend()` picks up. A single call with `c=codes` colours points but produces no categorical legend. Seaborn's `scatterplot(hue=...)` does this in one line.
""",
    docs=["https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.scatter.html",
          "https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.legend.html"],
    wrong_solutions=[
        dict(code="""
def solve(churn):
    fig, ax = plt.subplots()
    ax.scatter(churn["tenure"], churn["monthly_charges"])
    ax.set(xlabel="Tenure (months)", ylabel="Monthly charges")
    return ax
""", why="one series, no legend"),
        dict(code="""
def solve(churn):
    fig, ax = plt.subplots()
    for name, g in churn.groupby("contract"):
        ax.scatter(g["tenure"], g["monthly_charges"], label=name)
    ax.set(xlabel="Tenure (months)", ylabel="Monthly charges")
    return ax
""", why="legend never drawn"),
    ],
),
dict(
    id="pl-003",
    title="Histogram of daily returns",
    difficulty="Easy",
    tags=["distributions"],
    signature="def solve(returns: pd.Series) -> plt.Axes:",
    statement="""
Plot a histogram of `returns` with exactly **50 bins**, titled `"Daily returns"`, with x-label `"Return"`. Return the Axes.
""",
    setup="""
def make(seed, n):
    rng = np.random.default_rng(seed)
    return {"returns": pd.Series(rng.standard_t(4, n) * 0.01, name="ret")}

EXAMPLE = lambda: make(0, 500)
""",
    tests="""
TESTS = [
    lambda: make(1, 100),
    lambda: make(2, 5000),
    Test(lambda: make(3, 20), "few observations"),
]
""",
    plot=dict(returns="Axes", checks=["type", "bars", "title", "xlabel"]),
    hint1="`ax.hist(values, bins=50)`.",
    hint2="fig, ax = plt.subplots()\nax.hist(returns, bins=50)\nax.set(title='Daily returns', xlabel='Return')",
    solution="""
def solve(returns):
    fig, ax = plt.subplots()
    ax.hist(returns, bins=50)
    ax.set(title="Daily returns", xlabel="Return")
    return ax
""",
    explanation="""
The default is 10 bins, too coarse to see fat tails. `bins` also accepts explicit edges (`np.linspace(-0.1, 0.1, 51)`) or rules like `'auto'`/`'fd'`. Use `density=True` to compare distributions of different sizes. Each bin is a bar patch.
""",
    docs=["https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.hist.html"],
    wrong_solutions=[
        dict(code="def solve(returns):\n    fig, ax = plt.subplots()\n    ax.hist(returns)\n    ax.set(title='Daily returns', xlabel='Return')\n    return ax", why="default 10 bins"),
        dict(code="def solve(returns):\n    fig, ax = plt.subplots()\n    ax.hist(returns, bins=50)\n    return ax", why="no title/label"),
    ],
),
dict(
    id="pl-004",
    title="Sorted horizontal bar chart",
    difficulty="Easy",
    tags=["categories"],
    signature="def solve(orders: pd.DataFrame) -> plt.Axes:",
    statement="""
Plot total revenue per `category` as **horizontal** bars, sorted so that the **largest bar is at the top**. Set the x-label to `"Revenue"`. Return the Axes.
""",
    setup="""
EXAMPLE = lambda: {"orders": D.orders(seed=0, n=200)}
""",
    tests="""
TESTS = [
    lambda: {"orders": D.orders(seed=1, n=50)},
    lambda: {"orders": D.orders(seed=2, n=3000)},
    Test(lambda: {"orders": D.orders(seed=3, n=6)}, "some categories missing"),
]
""",
    plot=dict(returns="Axes", checks=["type", "bars", "yticklabels", "xlabel"]),
    hint1="Aggregate, `sort_values()` **ascending** (barh draws the first bar at the bottom), then `ax.barh(labels, values)`.",
    hint2="s = orders.groupby('category')['revenue'].sum().sort_values()\nfig, ax = plt.subplots()\nax.barh(s.index, s.values)",
    solution="""
def solve(orders):
    s = orders.groupby("category")["revenue"].sum().sort_values()
    fig, ax = plt.subplots()
    ax.barh(s.index, s.values)
    ax.set_xlabel("Revenue")
    return ax
""",
    explanation="""
`barh` places the first item at y = 0, i.e. at the **bottom**, so sort ascending to put the biggest bar on top (or call `ax.invert_yaxis()`). Horizontal bars keep long category names readable. `s.plot.barh(ax=ax)` is the pandas shortcut.
""",
    docs=["https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.barh.html"],
    wrong_solutions=[
        dict(code="def solve(orders):\n    s = orders.groupby('category')['revenue'].sum().sort_values(ascending=False)\n    fig, ax = plt.subplots()\n    ax.barh(s.index, s.values)\n    ax.set_xlabel('Revenue')\n    return ax", why="largest at the bottom"),
        dict(code="def solve(orders):\n    s = orders.groupby('category')['revenue'].sum().sort_values()\n    fig, ax = plt.subplots()\n    ax.bar(s.index, s.values)\n    ax.set_xlabel('Revenue')\n    return ax", why="vertical bars"),
    ],
),
dict(
    id="pl-005",
    title="Box plot of salary per department",
    difficulty="Easy",
    tags=["distributions", "categories"],
    signature="def solve(hr: pd.DataFrame) -> plt.Axes:",
    statement="""
With matplotlib, draw one box-and-whisker box per department showing the distribution of `salary` (ignore missing salaries). Departments in alphabetical order along the x-axis, with their names as tick labels; y-label `"Salary"`. Return the Axes.
""",
    setup="""
EXAMPLE = lambda: {"hr": D.hr(seed=0, n=150)}
""",
    tests="""
TESTS = [
    lambda: {"hr": D.hr(seed=1, n=80, missing_share=0.2)},
    lambda: {"hr": D.hr(seed=2, n=2000)},
    Test(lambda: {"hr": D.hr(seed=3, n=150).query("department in ['HR', 'Sales']")}, "two departments"),
]
""",
    plot=dict(returns="Axes", checks=["type", "lines", "xticklabels", "ylabel"]),
    hint1="`ax.boxplot(list_of_arrays, tick_labels=names)` (the `labels=` argument was renamed `tick_labels` in Matplotlib 3.9).",
    hint2="groups = hr.dropna(subset=['salary']).groupby('department')['salary']\nax.boxplot([g.to_numpy() for _, g in groups], tick_labels=[k for k, _ in groups])",
    solution="""
def solve(hr):
    groups = hr.dropna(subset=["salary"]).groupby("department")["salary"]
    fig, ax = plt.subplots()
    ax.boxplot([g.to_numpy() for _, g in groups], tick_labels=[k for k, _ in groups])
    ax.set_ylabel("Salary")
    return ax
""",
    explanation="""
`ax.boxplot` takes a list of arrays, one box per element. NaNs must be removed first, or the whole box becomes NaN. Each box is drawn as several line artists (box, median, whiskers, caps, fliers). Seaborn's `sns.boxplot(data=hr, x='department', y='salary')` handles grouping and NaN for you.
""",
    docs=["https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.boxplot.html"],
    wrong_solutions=[
        dict(code="""
def solve(hr):
    groups = hr.groupby("department")["salary"]
    fig, ax = plt.subplots()
    ax.boxplot([g.to_numpy() for _, g in groups])
    ax.set_ylabel("Salary")
    return ax
""", why="no department labels"),
        dict(code="""
def solve(hr):
    fig, ax = plt.subplots()
    ax.boxplot(hr["salary"].dropna().to_numpy())
    ax.set_ylabel("Salary")
    return ax
""", why="one box for everybody"),
    ],
),
dict(
    id="pl-006",
    title="Grid of histograms with shared axes",
    difficulty="Medium",
    tags=["layout"],
    signature="def solve(orders: pd.DataFrame) -> plt.Figure:",
    statement="""
Create a **2 x 2** grid of subplots with **shared x and y axes**, one subplot per region (regions A to Z, filled row by row). Each subplot shows a 20-bin histogram of that region's order `revenue` and is titled with the region name. Return the **Figure**.
""",
    setup="""
EXAMPLE = lambda: {"orders": D.orders(seed=0, n=400)}
""",
    tests="""
TESTS = [
    lambda: {"orders": D.orders(seed=1, n=200)},
    lambda: {"orders": D.orders(seed=2, n=3000)},
    Test(lambda: {"orders": D.orders(seed=3, n=60)}, "small"),
]
""",
    plot=dict(returns="Figure", checks=["type", "n_axes", "shared_x", "shared_y", "title", "bars"]),
    hint1="`fig, axes = plt.subplots(2, 2, sharex=True, sharey=True)`, then loop over `zip(axes.flat, groups)`.",
    hint2="fig, axes = plt.subplots(2, 2, sharex=True, sharey=True)\nfor ax, (region, g) in zip(axes.flat, orders.groupby('region')):\n    ax.hist(g['revenue'], bins=20)\n    ax.set_title(region)",
    solution="""
def solve(orders):
    fig, axes = plt.subplots(2, 2, sharex=True, sharey=True, figsize=(8, 6))
    for ax, (region, g) in zip(axes.flat, orders.groupby("region")):
        ax.hist(g["revenue"], bins=20)
        ax.set_title(region)
    return fig
""",
    explanation="""
`plt.subplots(nrows, ncols)` returns an array of Axes; `axes.flat` iterates them row by row. Shared axes make panels directly comparable (the same scale everywhere) and hide the redundant inner tick labels. `fig.tight_layout()` or `layout='constrained'` fixes overlaps.
""",
    docs=["https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.subplots.html",
          "https://matplotlib.org/stable/gallery/subplots_axes_and_figures/shared_axis_demo.html"],
    wrong_solutions=[
        dict(code="""
def solve(orders):
    fig, axes = plt.subplots(2, 2)
    for ax, (region, g) in zip(axes.flat, orders.groupby("region")):
        ax.hist(g["revenue"], bins=20)
        ax.set_title(region)
    return fig
""", why="axes not shared"),
        dict(code="""
def solve(orders):
    fig, axes = plt.subplots(2, 2, sharex=True, sharey=True)
    for ax, (region, g) in zip(axes.flat, orders.groupby("region")):
        ax.hist(g["revenue"], bins=20)
    return fig
""", why="no titles"),
    ],
),
dict(
    id="pl-007",
    title="Price and volume on twin axes",
    difficulty="Medium",
    tags=["layout", "time series"],
    signature="def solve(prices: pd.DataFrame, ticker: str) -> plt.Figure:",
    statement="""
For `ticker`, plot the closing price as a **line on the left y-axis** and the volume as **bars on a second y-axis on the right** that shares the same x-axis (dates). Left y-label `"Close"`, right y-label `"Volume"`. Return the **Figure**.
""",
    setup="""
EXAMPLE = lambda: {"prices": D.prices(seed=0, n_days=60, n_tickers=3), "ticker": "ALFA"}
""",
    tests="""
TESTS = [
    lambda: {"prices": D.prices(seed=1, n_days=30, n_tickers=4), "ticker": "DLTA"},
    lambda: {"prices": D.prices(seed=2, n_days=250, n_tickers=10), "ticker": "GOLF"},
    Test(lambda: {"prices": D.prices(seed=3, n_days=5, n_tickers=2), "ticker": "BRVO"}, "a week"),
]
""",
    plot=dict(returns="Figure", checks=["type", "n_axes", "twin", "lines", "bars", "ylabel"]),
    hint1="`ax2 = ax.twinx()` creates a second y-axis that shares x; plot the line on `ax`, the bars on `ax2`.",
    hint2="fig, ax = plt.subplots()\nax.plot(s['date'], s['close'])\nax2 = ax.twinx()\nax2.bar(s['date'], s['volume'], alpha=0.3)",
    solution="""
def solve(prices, ticker):
    s = prices[prices["ticker"] == ticker]
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.plot(s["date"], s["close"])
    ax.set_ylabel("Close")
    ax2 = ax.twinx()
    ax2.bar(s["date"], s["volume"], alpha=0.3)
    ax2.set_ylabel("Volume")
    return fig
""",
    explanation="""
`twinx()` overlays a new Axes with an independent y-axis on the right and a shared x-axis, the standard way to show two series with different units. Use it sparingly: two scales invite misreading. Two stacked subplots with `sharex=True` are often clearer.
""",
    docs=["https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.twinx.html"],
    wrong_solutions=[
        dict(code="""
def solve(prices, ticker):
    s = prices[prices["ticker"] == ticker]
    fig, (ax, ax2) = plt.subplots(2, 1, sharex=True)
    ax.plot(s["date"], s["close"])
    ax.set_ylabel("Close")
    ax2.bar(s["date"], s["volume"])
    ax2.set_ylabel("Volume")
    return fig
""", why="two stacked subplots, not twin axes"),
        dict(code="""
def solve(prices, ticker):
    s = prices[prices["ticker"] == ticker]
    fig, ax = plt.subplots()
    ax.bar(s["date"], s["volume"])
    ax.set_ylabel("Volume")
    ax2 = ax.twinx()
    ax2.plot(s["date"], s["close"])
    ax2.set_ylabel("Close")
    return fig
""", why="sides swapped"),
    ],
),
dict(
    id="pl-008",
    title="Exponential growth on a log scale",
    difficulty="Easy",
    tags=["axes & scales"],
    signature="def solve(users: pd.Series) -> plt.Axes:",
    statement="""
`users` grows roughly exponentially over time (indexed by date). Plot it as a line with a **logarithmic y-axis** (the axis scale itself, not log-transformed values), titled `"Users (log scale)"`. Return the Axes.
""",
    setup="""
def make(seed, n):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2022-01-01", periods=n, freq="W")
    return {"users": pd.Series(np.round(100 * np.exp(np.cumsum(rng.normal(0.05, 0.03, n)))), index=idx, name="users")}

EXAMPLE = lambda: make(0, 100)
""",
    tests="""
TESTS = [
    lambda: make(1, 30),
    lambda: make(2, 300),
    Test(lambda: make(3, 3), "three points"),
]
""",
    plot=dict(returns="Axes", checks=["type", "lines", "yscale", "title"]),
    hint1="`ax.set_yscale('log')` (or `ax.semilogy(...)`).",
    hint2="fig, ax = plt.subplots()\nax.plot(users.index, users.values)\nax.set_yscale('log')",
    solution="""
def solve(users):
    fig, ax = plt.subplots()
    ax.plot(users.index, users.values)
    ax.set_yscale("log")
    ax.set_title("Users (log scale)")
    return ax
""",
    explanation="""
On a log axis, constant growth rates appear as straight lines, and the tick labels still show real values. Plotting `np.log(users)` on a linear axis gives the same shape but unreadable ticks. Use `'symlog'` when values cross zero.
""",
    docs=["https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.set_yscale.html"],
    wrong_solutions=[
        dict(code="def solve(users):\n    fig, ax = plt.subplots()\n    ax.plot(users.index, np.log(users.values))\n    ax.set_title('Users (log scale)')\n    return ax", why="log values on a linear axis"),
        dict(code="def solve(users):\n    fig, ax = plt.subplots()\n    ax.plot(users.index, users.values)\n    ax.set_xscale('log')\n    ax.set_title('Users (log scale)')\n    return ax", why="log x-axis"),
    ],
),
dict(
    id="pl-009",
    title="Annotated drawdown chart",
    difficulty="Medium",
    tags=["annotation"],
    signature="def solve(equity: pd.Series) -> plt.Axes:",
    statement="""
`equity` is a portfolio value series indexed by date. On one Axes:

1. plot `equity` as a line;
2. draw a **dashed horizontal line** at the starting value;
3. **shade** the area between the curve and its running maximum;
4. **annotate** the point of maximum drawdown (lowest `equity / running max`) with the text `"max drawdown"`.

Return the Axes.
""",
    setup="""
def make(seed, n):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2023-01-02", periods=n)
    return {"equity": pd.Series(1000 * np.cumprod(1 + rng.normal(0.0004, 0.012, n)), index=idx, name="equity")}

EXAMPLE = lambda: make(0, 250)
""",
    tests="""
TESTS = [
    lambda: make(1, 60),
    lambda: make(2, 1000),
    Test(lambda: make(3, 10), "short"),
]
""",
    plot=dict(returns="Axes", checks=["type", "lines", "flat_lines", "polys", "texts"]),
    hint1="`ax.axhline(y, linestyle='--')`, `ax.fill_between(x, y1, y2)` and `ax.annotate(text, xy=(x, y))`.",
    hint2="peak = equity.cummax()\nax.axhline(equity.iloc[0], linestyle='--')\nax.fill_between(equity.index, equity, peak, alpha=0.3)\nax.annotate('max drawdown', xy=(t, equity[t]))",
    solution="""
def solve(equity):
    peak = equity.cummax()
    t = (equity / peak).idxmin()
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.plot(equity.index, equity.values)
    ax.axhline(equity.iloc[0], linestyle="--", color="gray")
    ax.fill_between(equity.index, equity, peak, alpha=0.3)
    ax.annotate("max drawdown", xy=(t, equity[t]), xytext=(10, -20), textcoords="offset points")
    return ax
""",
    explanation="""
`axhline`/`axvline` span the whole axis in axes coordinates, whatever the data limits. `fill_between` shades between two curves, here the underwater area. `annotate` places text with an optional arrow; `xytext` with `textcoords='offset points'` offsets it in screen units, so it doesn't depend on the data scale.
""",
    docs=["https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.axhline.html",
          "https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.fill_between.html",
          "https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.annotate.html"],
    wrong_solutions=[
        dict(code="""
def solve(equity):
    peak = equity.cummax()
    t = (equity / peak).idxmin()
    fig, ax = plt.subplots()
    ax.plot(equity.index, equity.values)
    ax.axvline(t, linestyle="--")
    ax.fill_between(equity.index, equity, peak, alpha=0.3)
    ax.annotate("max drawdown", xy=(t, equity[t]))
    return ax
""", why="vertical line instead of horizontal"),
        dict(code="""
def solve(equity):
    peak = equity.cummax()
    t = (equity / peak).idxmin()
    fig, ax = plt.subplots()
    ax.plot(equity.index, equity.values)
    ax.plot(peak.index, peak.values)
    ax.axhline(equity.iloc[0], linestyle="--")
    ax.annotate("max drawdown", xy=(t, equity[t]))
    return ax
""", why="peak drawn as a line, no shading"),
    ],
),
dict(
    id="pl-010",
    title="Percent tick labels",
    difficulty="Medium",
    tags=["axes & scales"],
    signature="def solve(rate: pd.Series) -> plt.Axes:",
    statement="""
`rate` is a monthly churn rate stored as fractions (0.27 means 27%), indexed by month. Plot it as a line with markers and format the **y-axis tick labels as percentages** (`'27%'`) with a tick formatter, keeping the data as fractions. Return the Axes.
""",
    setup="""
def make(seed, n):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2023-01-01", periods=n, freq="MS")
    return {"rate": pd.Series(np.clip(0.25 + np.cumsum(rng.normal(0, 0.01, n)), 0.05, 0.6), index=idx, name="churn_rate")}

EXAMPLE = lambda: make(0, 18)
""",
    tests="""
TESTS = [
    lambda: make(1, 6),
    lambda: make(2, 60),
    Test(lambda: make(3, 1), "one month"),
]
""",
    plot=dict(returns="Axes", checks=["type", "lines", "yformatter"]),
    hint1="`from matplotlib.ticker import PercentFormatter`; `ax.yaxis.set_major_formatter(PercentFormatter(xmax=1))`.",
    hint2="ax.plot(rate.index, rate.values, marker='o')\nax.yaxis.set_major_formatter(PercentFormatter(xmax=1))",
    solution="""
from matplotlib.ticker import PercentFormatter

def solve(rate):
    fig, ax = plt.subplots()
    ax.plot(rate.index, rate.values, marker="o")
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=1))
    return ax
""",
    explanation="""
A formatter changes how ticks are **labelled** without touching the data, and it keeps working when the axis rescales. Hard-coding labels with `set_yticklabels` breaks as soon as the ticks move. `xmax=1` means "1.0 is 100%"; `ticker.StrMethodFormatter('{x:,.0f}')` handles thousands separators.
""",
    docs=["https://matplotlib.org/stable/api/ticker_api.html#matplotlib.ticker.PercentFormatter",
          "https://matplotlib.org/stable/api/_as_gen/matplotlib.axis.Axis.set_major_formatter.html"],
    wrong_solutions=[
        dict(code="def solve(rate):\n    fig, ax = plt.subplots()\n    ax.plot(rate.index, rate.values * 100, marker='o')\n    return ax", why="values scaled, ticks unformatted"),
        dict(code="""
def solve(rate):
    fig, ax = plt.subplots()
    ax.plot(rate.index, rate.values, marker="o")
    ticks = ax.get_yticks()
    ax.set_yticks(ticks)
    ax.set_yticklabels([f"{t:.0%}" for t in ticks])
    return ax
""", why="hard-coded labels"),
    ],
),
dict(
    id="pl-011",
    title="One line per column with pandas .plot",
    difficulty="Easy",
    tags=["figure basics", "time series"],
    signature="def solve(monthly: pd.DataFrame) -> plt.Axes:",
    statement="""
`monthly` is indexed by month (a `DatetimeIndex`) with one column of revenue per region. Using pandas' built-in plotting on an Axes you create, draw **one line per region** with a legend and the title `"Revenue by region"`. Return the Axes.
""",
    setup="""
def make(seed, n):
    o = D.orders(seed=seed, n=n)
    m = o.groupby([pd.Grouper(key="order_date", freq="MS"), "region"])["revenue"].sum().unstack(fill_value=0.0)
    m.columns.name = None
    return {"monthly": m}

EXAMPLE = lambda: make(0, 400)
""",
    tests="""
TESTS = [
    lambda: make(1, 200),
    lambda: make(2, 3000),
    Test(lambda: {"monthly": make(3, 500)["monthly"][["North", "South"]]}, "two regions"),
]
""",
    plot=dict(returns="Axes", checks=["type", "lines", "legend", "title"]),
    hint1="`df.plot(ax=ax, title=...)` draws every column as a line on the given Axes and returns it.",
    hint2="fig, ax = plt.subplots()\nmonthly.plot(ax=ax, title='Revenue by region')",
    solution="""
def solve(monthly):
    fig, ax = plt.subplots()
    monthly.plot(ax=ax, title="Revenue by region")
    return ax
""",
    explanation="""
`DataFrame.plot` uses the index as x and each column as a series, adding a legend automatically: the fastest way to eyeball wide data. Passing `ax=` lets it slot into your own figure layout. `kind=` (or `.plot.bar()`, `.plot.hist()`...) switches the chart type.
""",
    docs=["https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.plot.html",
          "https://pandas.pydata.org/docs/user_guide/visualization.html"],
    wrong_solutions=[
        dict(code="def solve(monthly):\n    fig, ax = plt.subplots()\n    monthly.T.plot(ax=ax, title='Revenue by region')\n    return ax", why="transposed: one line per month"),
        dict(code="def solve(monthly):\n    fig, ax = plt.subplots()\n    monthly.sum(axis=1).plot(ax=ax, title='Revenue by region')\n    return ax", why="total only"),
    ],
),
dict(
    id="pl-012",
    title="Overlaid histograms with seaborn",
    difficulty="Easy",
    tags=["distributions"],
    signature="def solve(churn: pd.DataFrame) -> plt.Axes:",
    statement="""
With seaborn, plot the distribution of `tenure` as overlaid histograms **split by `churned`** (one colour per class, with a legend), using **30 bins**. Return the Axes.
""",
    setup="""
EXAMPLE = lambda: {"churn": D.churn(seed=0, n=600)}
""",
    tests="""
TESTS = [
    lambda: {"churn": D.churn(seed=1, n=200)},
    lambda: {"churn": D.churn(seed=2, n=4000)},
    Test(lambda: {"churn": D.churn(seed=3, n=100)}, "small"),
]
""",
    plot=dict(returns="Axes", checks=["type", "bars", "legend", "xlabel"]),
    hint1="`sns.histplot(data=df, x='tenure', hue='churned', bins=30)`; it returns the Axes.",
    hint2="sns.histplot(data=churn, x='tenure', hue='churned', bins=30)",
    solution="""
def solve(churn):
    fig, ax = plt.subplots()
    sns.histplot(data=churn, x="tenure", hue="churned", bins=30, ax=ax)
    return ax
""",
    explanation="""
Seaborn's axes-level functions take a long DataFrame plus column names and handle the grouping, colours and legend. `stat='density', common_norm=False` normalizes each class separately, useful when classes are imbalanced (here about 27% churners).
""",
    docs=["https://seaborn.pydata.org/generated/seaborn.histplot.html"],
    wrong_solutions=[
        dict(code="def solve(churn):\n    fig, ax = plt.subplots()\n    sns.histplot(data=churn, x='tenure', bins=30, ax=ax)\n    return ax", why="no split by class"),
        dict(code="def solve(churn):\n    fig, ax = plt.subplots()\n    sns.histplot(data=churn, x='tenure', hue='churned', ax=ax)\n    return ax", why="default bins"),
    ],
),
dict(
    id="pl-013",
    title="Violin plot per category, in a fixed order",
    difficulty="Easy",
    tags=["categories", "distributions"],
    signature="def solve(churn: pd.DataFrame) -> plt.Axes:",
    statement="""
With seaborn, draw **violin plots** of `monthly_charges` for each `internet` type, with the categories on the x-axis in the order `DSL`, `Fiber optic`, `None`. Return the Axes.
""",
    setup="""
EXAMPLE = lambda: {"churn": D.churn(seed=0, n=400)}
""",
    tests="""
TESTS = [
    lambda: {"churn": D.churn(seed=1, n=150)},
    lambda: {"churn": D.churn(seed=2, n=3000)},
    Test(lambda: {"churn": D.churn(seed=4, n=60)}, "small"),
]
""",
    plot=dict(returns="Axes", checks=["type", "polys", "xticklabels"]),
    hint1="`sns.violinplot(data=df, x=..., y=..., order=[...])`.",
    hint2="sns.violinplot(data=churn, x='internet', y='monthly_charges', order=['DSL', 'Fiber optic', 'None'])",
    solution="""
def solve(churn):
    fig, ax = plt.subplots()
    sns.violinplot(data=churn, x="internet", y="monthly_charges", order=["DSL", "Fiber optic", "None"], ax=ax)
    return ax
""",
    explanation="""
Without `order=`, seaborn uses the order in which categories first appear in the data, so the plot changes between datasets. A violin is a mirrored KDE: it shows the shape (e.g. bimodality) that a box plot hides. Pass `inner='quart'` to draw quartiles inside.
""",
    docs=["https://seaborn.pydata.org/generated/seaborn.violinplot.html"],
    wrong_solutions=[
        dict(code="def solve(churn):\n    fig, ax = plt.subplots()\n    sns.violinplot(data=churn, x='internet', y='monthly_charges', ax=ax)\n    return ax", why="data order"),
        dict(code="def solve(churn):\n    fig, ax = plt.subplots()\n    sns.boxplot(data=churn, x='internet', y='monthly_charges', order=['DSL', 'Fiber optic', 'None'], ax=ax)\n    return ax", why="box plot"),
    ],
),
dict(
    id="pl-014",
    title="Annotated correlation heatmap",
    difficulty="Medium",
    tags=["EDA figures"],
    signature="def solve(df: pd.DataFrame) -> plt.Axes:",
    statement="""
Plot the correlation matrix of the **numeric** columns of `df` as a seaborn heatmap, **annotated** with the values (2 decimals), the colour scale fixed to [-1, 1], and a colorbar. Return the Axes.
""",
    setup="""
EXAMPLE = lambda: {"df": D.churn(seed=0, n=300)}
""",
    tests="""
TESTS = [
    lambda: {"df": D.hr(seed=1, n=200)},
    lambda: {"df": D.churn(seed=2, n=2000)},
    Test(lambda: {"df": D.orders(seed=3, n=50)[["quantity", "unit_price", "revenue"]]}, "three columns"),
]
""",
    plot=dict(returns="Axes", checks=["type", "meshes", "texts", "colorbar", "xticklabels"]),
    hint1="`sns.heatmap(corr, annot=True, fmt='.2f', vmin=-1, vmax=1, cmap='coolwarm')`.",
    hint2="corr = df.select_dtypes('number').corr()\nsns.heatmap(corr, annot=True, fmt='.2f', vmin=-1, vmax=1, cmap='coolwarm')",
    solution="""
def solve(df):
    corr = df.select_dtypes("number").corr()
    fig, ax = plt.subplots()
    sns.heatmap(corr, annot=True, fmt=".2f", vmin=-1, vmax=1, cmap="coolwarm", ax=ax)
    return ax
""",
    explanation="""
Fixing `vmin=-1, vmax=1` with a diverging colormap makes 0 the neutral colour, so heatmaps are comparable across datasets; otherwise the scale stretches to the observed range. `fmt='.2f'` controls the annotation format. Mask the upper triangle (`mask=np.triu(...)`) to halve the clutter.
""",
    docs=["https://seaborn.pydata.org/generated/seaborn.heatmap.html"],
    wrong_solutions=[
        dict(code="def solve(df):\n    fig, ax = plt.subplots()\n    sns.heatmap(df.select_dtypes('number').corr(), vmin=-1, vmax=1, ax=ax)\n    return ax", why="not annotated"),
        dict(code="def solve(df):\n    fig, ax = plt.subplots()\n    sns.heatmap(df.select_dtypes('number').corr(), annot=True, cbar=False, ax=ax)\n    return ax", why="no colorbar"),
    ],
),
dict(
    id="pl-015",
    title="Figure-level facets with relplot",
    difficulty="Medium",
    tags=["layout", "relationships"],
    signature="def solve(churn: pd.DataFrame):",
    statement="""
With seaborn's **figure-level** interface, draw scatter plots of `monthly_charges` (y) against `tenure` (x), with **one panel per `contract` type** laid out in columns in alphabetical order, and points coloured by `churned`. Return the object seaborn returns (a `FacetGrid`).
""",
    setup="""
EXAMPLE = lambda: {"churn": D.churn(seed=0, n=400)}
""",
    tests="""
TESTS = [
    lambda: {"churn": D.churn(seed=1, n=150)},
    lambda: {"churn": D.churn(seed=2, n=600)},
    Test(lambda: {"churn": D.churn(seed=3, n=300).query("contract != 'One year'")}, "two contracts"),
]
""",
    plot=dict(returns="FacetGrid", checks=["type", "n_axes", "points", "title"]),
    hint1="`sns.relplot(data=..., x=..., y=..., hue=..., col=..., col_order=sorted(...))` returns a FacetGrid.",
    hint2="sns.relplot(data=churn, x='tenure', y='monthly_charges', hue='churned', col='contract', col_order=sorted(churn['contract'].unique()))",
    solution="""
def solve(churn):
    return sns.relplot(data=churn, x="tenure", y="monthly_charges", hue="churned",
                       col="contract", col_order=sorted(churn["contract"].unique()), height=3)
""",
    explanation="""
Figure-level functions (`relplot`, `displot`, `catplot`) create their own figure and facet it with `row=`/`col=`; they return a FacetGrid (`g.axes`, `g.figure`), not an Axes, so they can't take `ax=`. Axes-level functions (`scatterplot`, `histplot`, `boxplot`) draw into one Axes you control.
""",
    docs=["https://seaborn.pydata.org/generated/seaborn.relplot.html",
          "https://seaborn.pydata.org/tutorial/function_overview.html#figure-level-vs-axes-level-functions"],
    wrong_solutions=[
        dict(code="def solve(churn):\n    return sns.scatterplot(data=churn, x='tenure', y='monthly_charges', hue='contract')", why="axes-level, no facets"),
        dict(code="def solve(churn):\n    return sns.relplot(data=churn, x='tenure', y='monthly_charges', hue='churned', col='contract')", why="panels in data order"),
    ],
),
dict(
    id="pl-016",
    title="ROC curve with AUC in the legend",
    difficulty="Medium",
    tags=["model diagnostics"],
    signature="def solve(y_true: np.ndarray, scores: np.ndarray) -> plt.Axes:",
    statement="""
Given binary labels `y_true` and predicted scores `scores`, plot the ROC curve (false positive rate on x, true positive rate on y) as a line labelled `"AUC = 0.87"` (the ROC AUC with 2 decimals), plus a dashed diagonal chance line **without** a legend entry. Axis labels `"False positive rate"` and `"True positive rate"`; show the legend. Return the Axes.
""",
    setup="""
def make(seed, n, signal=1.0):
    rng = np.random.default_rng(seed)
    y = (rng.random(n) < 0.3).astype(int)
    return {"y_true": y, "scores": np.round(signal * y + rng.normal(0, 1, n), 3)}

EXAMPLE = lambda: make(0, 300)
""",
    tests="""
TESTS = [
    lambda: make(1, 100, 2.0),
    lambda: make(2, 3000, 0.5),
    Test(lambda: make(3, 20, 3.0), "small, near perfect"),
]
""",
    plot=dict(returns="Axes", checks=["type", "lines", "legend_labels", "xlabel", "ylabel"]),
    hint1="`from sklearn.metrics import roc_curve, roc_auc_score`; `fpr, tpr, _ = roc_curve(y_true, scores)`; plot with `label=f'AUC = {auc:.2f}'`.",
    hint2="fpr, tpr, _ = roc_curve(y_true, scores)\nax.plot(fpr, tpr, label=f'AUC = {roc_auc_score(y_true, scores):.2f}')\nax.plot([0, 1], [0, 1], linestyle='--')",
    solution="""
from sklearn.metrics import roc_auc_score, roc_curve

def solve(y_true, scores):
    fpr, tpr, _ = roc_curve(y_true, scores)
    fig, ax = plt.subplots()
    ax.plot(fpr, tpr, label=f"AUC = {roc_auc_score(y_true, scores):.2f}")
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray")
    ax.set(xlabel="False positive rate", ylabel="True positive rate")
    ax.legend()
    return ax
""",
    explanation="""
`roc_curve` needs **scores** (probabilities or decision values), not hard 0/1 predictions, which would give a single-corner curve. Lines without a `label=` don't appear in the legend. `RocCurveDisplay.from_predictions(y, s)` draws the same plot in one call.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.metrics.roc_curve.html",
          "https://scikit-learn.org/stable/modules/generated/sklearn.metrics.RocCurveDisplay.html"],
    wrong_solutions=[
        dict(code="""
from sklearn.metrics import roc_auc_score, roc_curve

def solve(y_true, scores):
    fpr, tpr, _ = roc_curve(y_true, scores)
    fig, ax = plt.subplots()
    ax.plot(fpr, tpr, label=f"AUC = {roc_auc_score(y_true, scores):.2f}")
    ax.plot([0, 1], [0, 1], linestyle="--", label="chance")
    ax.set(xlabel="False positive rate", ylabel="True positive rate")
    ax.legend()
    return ax
""", why="diagonal in the legend"),
        dict(code="""
from sklearn.metrics import roc_auc_score, roc_curve

def solve(y_true, scores):
    fpr, tpr, _ = roc_curve(y_true, scores)
    fig, ax = plt.subplots()
    ax.plot(tpr, fpr, label=f"AUC = {roc_auc_score(y_true, scores):.3f}")
    ax.plot([0, 1], [0, 1], linestyle="--")
    ax.set(xlabel="False positive rate", ylabel="True positive rate")
    ax.legend()
    return ax
""", why="AUC with 3 decimals"),
    ],
),
dict(
    id="pl-017",
    title="Confusion-matrix heatmap",
    difficulty="Medium",
    tags=["model diagnostics"],
    signature="def solve(y_true: np.ndarray, y_pred: np.ndarray) -> plt.Axes:",
    statement="""
Compute the confusion matrix of `y_true` vs `y_pred` (string class labels; rows = actual, columns = predicted, classes in sorted order) and draw it as a seaborn heatmap **annotated with integer counts**, tick labels = class names, x-label `"Predicted"`, y-label `"Actual"`. Return the Axes.
""",
    setup="""
def make(seed, n, classes=("cat", "dog", "fox")):
    rng = np.random.default_rng(seed)
    y = rng.choice(list(classes), n)
    pred = np.where(rng.random(n) < 0.7, y, rng.choice(list(classes), n))
    return {"y_true": y, "y_pred": pred}

EXAMPLE = lambda: make(0, 60)
""",
    tests="""
TESTS = [
    lambda: make(1, 30),
    lambda: make(2, 2000, ("a", "b", "c", "d", "e")),
    Test(lambda: make(3, 40, ("no", "yes")), "binary"),
]
""",
    plot=dict(returns="Axes", checks=["type", "meshes", "texts", "xlabel", "ylabel", "xticklabels", "yticklabels"]),
    hint1="`confusion_matrix(y_true, y_pred, labels=labels)` with `labels = np.unique(...)`, then `sns.heatmap(cm, annot=True, fmt='d', xticklabels=labels, yticklabels=labels)`.",
    hint2="labels = np.unique(np.concatenate([y_true, y_pred]))\ncm = confusion_matrix(y_true, y_pred, labels=labels)\nsns.heatmap(cm, annot=True, fmt='d', xticklabels=labels, yticklabels=labels)",
    solution="""
from sklearn.metrics import confusion_matrix

def solve(y_true, y_pred):
    labels = np.unique(np.concatenate([y_true, y_pred]))
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    fig, ax = plt.subplots()
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=labels, yticklabels=labels, ax=ax)
    ax.set(xlabel="Predicted", ylabel="Actual")
    return ax
""",
    explanation="""
scikit-learn's convention is rows = true class, columns = predicted class; always label the axes, because people read it both ways. `fmt='d'` prints integers (the default `.2g` shows counts like `1.2e+03`). `ConfusionMatrixDisplay.from_predictions` is the built-in equivalent.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.metrics.confusion_matrix.html",
          "https://seaborn.pydata.org/generated/seaborn.heatmap.html"],
    wrong_solutions=[
        dict(code="""
from sklearn.metrics import confusion_matrix

def solve(y_true, y_pred):
    labels = np.unique(np.concatenate([y_true, y_pred]))
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    fig, ax = plt.subplots()
    sns.heatmap(cm, ax=ax)
    ax.set(xlabel="Predicted", ylabel="Actual")
    return ax
""", why="no annotations or class names"),
        dict(code="""
from sklearn.metrics import confusion_matrix

def solve(y_true, y_pred):
    labels = np.unique(np.concatenate([y_true, y_pred]))
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    fig, ax = plt.subplots()
    sns.heatmap(cm, annot=True, fmt="d", xticklabels=labels, yticklabels=labels, ax=ax)
    ax.set(xlabel="Actual", ylabel="Predicted")
    return ax
""", why="axis labels swapped"),
    ],
),
dict(
    id="pl-018",
    title="Residuals vs fitted values",
    difficulty="Medium",
    tags=["model diagnostics"],
    signature="def solve(X: np.ndarray, y: np.ndarray) -> plt.Axes:",
    statement="""
Fit a `LinearRegression` of `y` on `X`, then plot the **residuals** (`y - fitted`) against the **fitted values** as a scatter plot, with a horizontal reference line at 0. Axis labels `"Fitted"` (x) and `"Residual"` (y). Return the Axes.
""",
    setup="""
def make(seed, n, k=3, curve=0.0):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, k))
    y = X @ rng.normal(size=k) + curve * X[:, 0] ** 2 + rng.normal(0, 0.5, n)
    return {"X": X, "y": y}

EXAMPLE = lambda: make(0, 200, curve=0.8)
""",
    tests="""
TESTS = [
    lambda: make(1, 50),
    lambda: make(2, 2000, 5, curve=0.5),
    Test(lambda: make(3, 10, 1), "ten points"),
]
""",
    plot=dict(returns="Axes", checks=["type", "points", "flat_lines", "xlabel", "ylabel"]),
    allow_in_statement=["LinearRegression"],
    hint1="`fitted = LinearRegression().fit(X, y).predict(X)`; `ax.scatter(fitted, y - fitted)`; `ax.axhline(0)`.",
    hint2="fitted = LinearRegression().fit(X, y).predict(X)\nax.scatter(fitted, y - fitted, s=10)\nax.axhline(0, linestyle='--')",
    solution="""
from sklearn.linear_model import LinearRegression

def solve(X, y):
    fitted = LinearRegression().fit(X, y).predict(X)
    fig, ax = plt.subplots()
    ax.scatter(fitted, y - fitted, s=10)
    ax.axhline(0, color="gray", linestyle="--")
    ax.set(xlabel="Fitted", ylabel="Residual")
    return ax
""",
    explanation="""
Residuals vs fitted is the first regression diagnostic. You want a structureless band around 0. A curve means a missed nonlinearity (the example has one), a funnel means heteroscedasticity, and isolated points are outliers or leverage. On a held-out set, plot the test residuals.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LinearRegression.html",
          "https://scikit-learn.org/stable/modules/generated/sklearn.metrics.PredictionErrorDisplay.html"],
    wrong_solutions=[
        dict(code="""
from sklearn.linear_model import LinearRegression

def solve(X, y):
    fitted = LinearRegression().fit(X, y).predict(X)
    fig, ax = plt.subplots()
    ax.scatter(fitted, y)
    ax.set(xlabel="Fitted", ylabel="Residual")
    return ax
""", why="actual vs fitted, no zero line"),
        dict(code="""
from sklearn.linear_model import LinearRegression

def solve(X, y):
    fitted = LinearRegression().fit(X, y).predict(X)
    fig, ax = plt.subplots()
    ax.plot(fitted, y - fitted)
    ax.axhline(0)
    ax.set(xlabel="Fitted", ylabel="Residual")
    return ax
""", why="line plot instead of scatter"),
    ],
),
dict(
    id="pl-019",
    title="Top-10 feature importances",
    difficulty="Easy",
    tags=["model diagnostics"],
    signature="def solve(importances: pd.Series) -> plt.Axes:",
    statement="""
`importances` is a Series of feature importances indexed by feature name. Plot the **10 largest** as horizontal bars with the most important feature **at the top**, titled `"Top 10 features"`. Return the Axes.
""",
    setup="""
def make(seed, k):
    rng = np.random.default_rng(seed)
    v = rng.dirichlet(np.ones(k) * 0.5)
    return {"importances": pd.Series(v, index=[f"feat_{i:02d}" for i in range(k)], name="importance")}

EXAMPLE = lambda: make(0, 25)
""",
    tests="""
TESTS = [
    lambda: make(1, 12),
    lambda: make(2, 200),
    Test(lambda: make(3, 10), "exactly ten"),
]
""",
    plot=dict(returns="Axes", checks=["type", "bars", "yticklabels", "title"]),
    hint1="`importances.nlargest(10)`, reverse it (`[::-1]`) because `barh` draws from the bottom, then `ax.barh(...)`.",
    hint2="top = importances.nlargest(10)[::-1]\nax.barh(top.index, top.values)",
    solution="""
def solve(importances):
    top = importances.nlargest(10)[::-1]
    fig, ax = plt.subplots()
    ax.barh(top.index, top.values)
    ax.set_title("Top 10 features")
    return ax
""",
    explanation="""
`nlargest(10)` is sorted descending; `barh` puts the first bar at the bottom, so reverse it to put the winner on top. Remember that impurity-based importances favour high-cardinality features; permutation importance on held-out data is more trustworthy.
""",
    docs=["https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.barh.html",
          "https://pandas.pydata.org/docs/reference/api/pandas.Series.nlargest.html"],
    wrong_solutions=[
        dict(code="def solve(importances):\n    top = importances.nlargest(10)\n    fig, ax = plt.subplots()\n    ax.barh(top.index, top.values)\n    ax.set_title('Top 10 features')\n    return ax", why="most important at the bottom"),
        dict(code="def solve(importances):\n    top = importances.sort_values()\n    fig, ax = plt.subplots()\n    ax.barh(top.index, top.values)\n    ax.set_title('Top 10 features')\n    return ax", why="all features"),
    ],
),
dict(
    id="pl-020",
    title="Elbow curve for k-means",
    difficulty="Medium",
    tags=["model diagnostics"],
    signature="def solve(X: np.ndarray) -> plt.Axes:",
    statement="""
For each k from 1 to 8, fit `KMeans(n_clusters=k, n_init=3, random_state=0)` on `X` and record its inertia. Plot inertia against k as **one line with markers** (8 points), x-label `"k"`, y-label `"Inertia"`. Return the Axes.
""",
    setup="""
def make(seed, n, centers):
    from sklearn.datasets import make_blobs
    X, _ = make_blobs(n_samples=n, centers=centers, n_features=2, random_state=seed)
    return {"X": X}

EXAMPLE = lambda: make(0, 150, 3)
""",
    tests="""
TESTS = [
    lambda: make(1, 80, 2),
    lambda: make(2, 300, 5),
    Test(lambda: make(3, 40, 4), "small"),
]
""",
    plot=dict(returns="Axes", checks=["type", "lines", "line_points", "xlabel", "ylabel"]),
    allow_in_statement=["KMeans"],
    hint1="Loop `for k in range(1, 9)`, collect `KMeans(...).fit(X).inertia_`, then `ax.plot(ks, inertias, marker='o')`.",
    hint2="ks = range(1, 9)\ninertia = [KMeans(n_clusters=k, n_init=3, random_state=0).fit(X).inertia_ for k in ks]\nax.plot(ks, inertia, marker='o')",
    solution="""
from sklearn.cluster import KMeans

def solve(X):
    ks = list(range(1, 9))
    inertia = [KMeans(n_clusters=k, n_init=3, random_state=0).fit(X).inertia_ for k in ks]
    fig, ax = plt.subplots()
    ax.plot(ks, inertia, marker="o")
    ax.set(xlabel="k", ylabel="Inertia")
    return ax
""",
    explanation="""
Inertia (within-cluster sum of squares) always decreases with k, so look for the "elbow" where extra clusters stop helping much. It's a heuristic: cross-check with silhouette scores, and scale features first, because k-means uses Euclidean distance.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html"],
    wrong_solutions=[
        dict(code="""
from sklearn.cluster import KMeans

def solve(X):
    ks = list(range(2, 9))
    inertia = [KMeans(n_clusters=k, n_init=3, random_state=0).fit(X).inertia_ for k in ks]
    fig, ax = plt.subplots()
    ax.plot(ks, inertia, marker="o")
    ax.set(xlabel="k", ylabel="Inertia")
    return ax
""", why="k starts at 2"),
        dict(code="""
from sklearn.cluster import KMeans

def solve(X):
    ks = list(range(1, 9))
    inertia = [KMeans(n_clusters=k, n_init=3, random_state=0).fit(X).inertia_ for k in ks]
    fig, ax = plt.subplots()
    ax.bar(ks, inertia)
    ax.set(xlabel="k", ylabel="Inertia")
    return ax
""", why="bars instead of a line"),
    ],
),
dict(
    id="pl-021",
    title="Cumulative explained variance",
    difficulty="Medium",
    tags=["model diagnostics"],
    signature="def solve(X: np.ndarray) -> plt.Axes:",
    statement="""
Standardize `X`, fit a PCA with **all** components, and plot the **cumulative** explained variance ratio against the number of components (1, 2, ..., d) as a line with markers. Add a dashed horizontal line at 0.9. Axis labels `"Components"` and `"Cumulative explained variance"`. Return the Axes.
""",
    setup="""
def make(seed, n, d):
    rng = np.random.default_rng(seed)
    L = rng.normal(size=(d, d)) * rng.uniform(0.1, 2, d)
    return {"X": rng.normal(size=(n, d)) @ L * rng.uniform(1, 100, d)}

EXAMPLE = lambda: make(0, 200, 8)
""",
    tests="""
TESTS = [
    lambda: make(1, 60, 4),
    lambda: make(2, 1000, 20),
    Test(lambda: make(3, 30, 2), "two features"),
]
""",
    plot=dict(returns="Axes", checks=["type", "lines", "line_points", "flat_lines", "xlabel", "ylabel"]),
    hint1="`PCA().fit(StandardScaler().fit_transform(X)).explained_variance_ratio_.cumsum()`, plot against `np.arange(1, d + 1)`, then `ax.axhline(0.9, linestyle='--')`.",
    hint2="cum = PCA().fit(StandardScaler().fit_transform(X)).explained_variance_ratio_.cumsum()\nax.plot(np.arange(1, len(cum) + 1), cum, marker='o')\nax.axhline(0.9, linestyle='--')",
    solution="""
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

def solve(X):
    cum = PCA().fit(StandardScaler().fit_transform(X)).explained_variance_ratio_.cumsum()
    fig, ax = plt.subplots()
    ax.plot(np.arange(1, len(cum) + 1), cum, marker="o")
    ax.axhline(0.9, color="gray", linestyle="--")
    ax.set(xlabel="Components", ylabel="Cumulative explained variance")
    return ax
""",
    explanation="""
PCA is scale-sensitive: without standardizing, the feature with the largest units dominates the first component. The cumulative curve tells you how many components keep, say, 90% of the variance; `PCA(n_components=0.9)` picks that number for you.
""",
    docs=["https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.PCA.html"],
    wrong_solutions=[
        dict(code="""
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

def solve(X):
    r = PCA().fit(StandardScaler().fit_transform(X)).explained_variance_ratio_
    fig, ax = plt.subplots()
    ax.plot(np.arange(1, len(r) + 1), r, marker="o")
    ax.set(xlabel="Components", ylabel="Cumulative explained variance")
    return ax
""", why="not cumulative, no 0.9 line"),
    ],
),
dict(
    id="pl-022",
    title="Four-panel EDA figure",
    difficulty="Hard",
    tags=["EDA figures", "layout"],
    signature="def solve(churn: pd.DataFrame) -> plt.Figure:",
    statement="""
Build a 2 x 2 EDA figure for the churn table, with these panels and titles:

* top-left `"Tenure"`: histogram of `tenure`;
* top-right `"Charges by contract"`: seaborn box plot of `monthly_charges` per `contract`;
* bottom-left `"Charges vs tenure"`: scatter of `monthly_charges` against `tenure`;
* bottom-right `"Correlations"`: seaborn heatmap of the correlation matrix of the numeric columns, with a colorbar.

Return the **Figure**.
""",
    setup="""
EXAMPLE = lambda: {"churn": D.churn(seed=0, n=500)}
""",
    tests="""
TESTS = [
    lambda: {"churn": D.churn(seed=1, n=150)},
    lambda: {"churn": D.churn(seed=2, n=600)},
    Test(lambda: {"churn": D.churn(seed=3, n=60)}, "small"),
]
""",
    plot=dict(returns="Figure", checks=["type", "n_axes", "colorbar", "title"]),
    hint1="`fig, axes = plt.subplots(2, 2)`; pass each Axes to the plotting call with `ax=axes[r, c]` (seaborn) or call methods on it (matplotlib).",
    hint2="fig, axes = plt.subplots(2, 2, figsize=(10, 8))\naxes[0, 0].hist(churn['tenure'], bins=30)\nsns.boxplot(data=churn, x='contract', y='monthly_charges', ax=axes[0, 1])\naxes[1, 0].scatter(churn['tenure'], churn['monthly_charges'], s=5)\nsns.heatmap(churn.select_dtypes('number').corr(), ax=axes[1, 1])",
    solution="""
def solve(churn):
    fig, axes = plt.subplots(2, 2, figsize=(10, 8))
    axes[0, 0].hist(churn["tenure"], bins=30)
    sns.boxplot(data=churn, x="contract", y="monthly_charges", ax=axes[0, 1])
    axes[1, 0].scatter(churn["tenure"], churn["monthly_charges"], s=5)
    sns.heatmap(churn.select_dtypes("number").corr(), vmin=-1, vmax=1, cmap="coolwarm", ax=axes[1, 1])
    for ax, t in zip(axes.flat, ["Tenure", "Charges by contract", "Charges vs tenure", "Correlations"]):
        ax.set_title(t)
    return fig
""",
    explanation="""
Every seaborn axes-level function accepts `ax=`, so it composes with matplotlib grids; figure-level functions (`relplot`, `catplot`) don't. A one-figure EDA overview (distribution, groups, relationship, correlations) is a strong opening move in a live data interview.
""",
    docs=["https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.subplots.html",
          "https://seaborn.pydata.org/generated/seaborn.boxplot.html",
          "https://seaborn.pydata.org/generated/seaborn.heatmap.html"],
    wrong_solutions=[
        dict(code="""
def solve(churn):
    fig, axes = plt.subplots(2, 2)
    axes[0, 0].hist(churn["tenure"], bins=30)
    sns.boxplot(data=churn, x="contract", y="monthly_charges", ax=axes[0, 1])
    axes[1, 0].scatter(churn["tenure"], churn["monthly_charges"], s=5)
    sns.heatmap(churn.select_dtypes("number").corr(), ax=axes[1, 1])
    return fig
""", why="no titles"),
        dict(code="""
def solve(churn):
    fig, axes = plt.subplots(2, 2)
    axes[0, 0].hist(churn["tenure"], bins=30)
    sns.boxplot(data=churn, x="contract", y="monthly_charges", ax=axes[0, 1])
    axes[1, 0].scatter(churn["tenure"], churn["monthly_charges"], s=5)
    sns.heatmap(churn.select_dtypes("number").corr(), cbar=False, ax=axes[1, 1])
    for ax, t in zip(axes.flat, ["Tenure", "Charges by contract", "Charges vs tenure", "Correlations"]):
        ax.set_title(t)
    return fig
""", why="no colorbar"),
    ],
),
dict(
    id="pl-023",
    title="Scatter with a hue in seaborn",
    difficulty="Easy",
    tags=["relationships"],
    signature="def solve(churn: pd.DataFrame) -> plt.Axes:",
    statement="""
With seaborn, scatter `total_charges` (y) against `tenure` (x) for the churn table, coloured by `contract` with a legend. Keep seaborn's default axis labels (the column names). Return the Axes.
""",
    setup="""
EXAMPLE = lambda: {"churn": D.churn(seed=0, n=400)}
""",
    tests="""
TESTS = [
    lambda: {"churn": D.churn(seed=1, n=100)},
    lambda: {"churn": D.churn(seed=2, n=3000)},
    Test(lambda: {"churn": D.churn(seed=3, n=30)}, "small"),
]
""",
    plot=dict(returns="Axes", checks=["type", "points", "legend", "xlabel", "ylabel"]),
    hint1="`sns.scatterplot(data=df, x=..., y=..., hue=...)` returns the Axes.",
    hint2="sns.scatterplot(data=churn, x='tenure', y='total_charges', hue='contract')",
    solution="""
def solve(churn):
    fig, ax = plt.subplots()
    sns.scatterplot(data=churn, x="tenure", y="total_charges", hue="contract", s=12, ax=ax)
    return ax
""",
    explanation="""
`hue` maps a column to colour and adds the legend; `style=` and `size=` map more columns to marker shape and size. Rows with missing x or y (here `total_charges` for brand-new customers) are dropped silently, so check `isna()` if counts look off.
""",
    docs=["https://seaborn.pydata.org/generated/seaborn.scatterplot.html"],
    wrong_solutions=[
        dict(code="def solve(churn):\n    fig, ax = plt.subplots()\n    sns.scatterplot(data=churn, x='tenure', y='total_charges', ax=ax)\n    return ax", why="no hue"),
        dict(code="def solve(churn):\n    fig, ax = plt.subplots()\n    sns.scatterplot(data=churn, x='total_charges', y='tenure', hue='contract', ax=ax)\n    return ax", why="axes swapped"),
    ],
),
]
