"""Section metadata and the topic-tag vocabulary.

Tags are topic-level and must never name the function the problem drills
(build.py rejects a tag that shares a word with a function named in Hint 1
or Hint 2). Add new tags here when a new topic appears.
"""

SECTIONS = [
    # key, id prefix, display title, packages the worker must load first
    ("numpy", "np", "NumPy", []),
    ("pandas", "pd", "pandas", []),
    ("plotting", "pl", "Plotting", ["matplotlib", "seaborn"]),
    ("sklearn", "sk", "scikit-learn", ["scikit-learn"]),
    ("stats", "st", "Statistics", ["scipy", "statsmodels"]),
    ("quant", "qt", "Quant research", []),
    ("chains", "ch", "Chains", ["scikit-learn"]),
    ("bugs", "bug", "Fix the bug", []),
]

TAGS = {
    "numpy": ["array creation", "dtypes", "reshaping", "views & copies", "indexing",
              "conditional logic", "broadcasting", "reductions", "sorting & ranking", "binning",
              "cumulative ops", "set operations", "random sampling", "missing data", "encoding",
              "window functions", "linear algebra", "statistics", "ML from scratch"],
    "pandas": ["io & parsing", "EDA", "construction", "type conversion", "selection", "sorting & ranking",
               "column ops", "conditional logic", "strings", "dates & times", "missing data", "duplicates",
               "categoricals", "binning", "aggregation", "group-wise ops", "reshaping", "joining",
               "time series", "window functions", "feature engineering", "outliers", "method chaining"],
    "plotting": ["figure basics", "time series", "relationships", "distributions", "categories",
                 "layout", "annotation", "axes & scales", "legends", "model diagnostics", "EDA figures"],
    "sklearn": ["splitting", "preprocessing", "encoding", "pipelines", "baselines", "linear models",
                "classification", "metrics", "thresholds", "cross-validation", "tuning", "ensembles",
                "imbalance", "feature engineering", "model inspection", "diagnostics", "clustering",
                "dimensionality reduction", "leakage", "boosting"],
    "stats": ["hypothesis testing", "correlation", "resampling", "regression", "time series"],
    "quant": ["returns", "risk", "performance", "cross-sectional", "labels & lookahead",
              "signal evaluation", "portfolio construction", "validation"],
    "chains": ["inspection", "cleaning", "feature engineering", "pipelines", "evaluation",
               "time series", "clustering", "dimensionality reduction", "visualization"],
    "bugs": ["leakage", "lookahead", "axes & shapes", "pandas semantics", "missing data",
             "annualization", "joins", "aggregation", "indexing", "validation"],
}

CHAINS = {
    "churn": "Churn classifier (classification)",
    "salary": "Salary model (regression)",
    "factor": "Momentum factor (time series, walk-forward)",
    "segments": "Customer segments (clustering + PCA)",
}

DOC_DOMAINS = ["numpy.org", "pandas.pydata.org", "matplotlib.org", "seaborn.pydata.org",
               "scikit-learn.org", "docs.scipy.org", "www.statsmodels.org", "lightgbm.readthedocs.io",
               "docs.python.org"]
