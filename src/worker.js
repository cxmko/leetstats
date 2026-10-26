/* LeetStats Python worker. Created by the page from an inline Blob (file://
   pages cannot load worker scripts from disk).

   Pyodide 314 refuses to run in a "classic" worker (it probes
   importScripts), and Chromium blocks importScripts() in blob: workers of
   file:// pages anyway. Shadowing importScripts makes Pyodide use dynamic
   import(), which classic workers support. */
"use strict";
self.importScripts = function () { throw new Error("importScripts is disabled in this worker"); };

let py = null;
let harness = null;
let cfg = null;
const loading = {};          // package -> Promise
const BACKGROUND = ["matplotlib", "seaborn", "scipy", "scikit-learn", "statsmodels"];
const IMPORT_TO_PKG = { sklearn: "scikit-learn", scipy: "scipy", statsmodels: "statsmodels",
  lightgbm: "lightgbm", seaborn: "seaborn", matplotlib: "matplotlib" };
const WARMUP = {
  "matplotlib": "import matplotlib\nmatplotlib.use('Agg')\nimport matplotlib.pyplot as plt\nf = plt.figure(); f.canvas.draw(); plt.close('all')",
  "seaborn": "import seaborn",
  "scipy": "import scipy.stats",
  "scikit-learn": "import sklearn.linear_model, sklearn.preprocessing, sklearn.model_selection, sklearn.metrics, sklearn.pipeline, sklearn.compose, sklearn.ensemble, sklearn.impute",
  "statsmodels": "import statsmodels.api",
  "lightgbm": "import lightgbm",
};
const quiet = { messageCallback: () => {}, errorCallback: () => {} };
const post = (m) => self.postMessage(m);

function ensure(pkg) {
  if (loading[pkg]) return loading[pkg];
  loading[pkg] = (async () => {
    post({ type: "pkg", name: pkg, state: "loading" });
    try {
      if (pkg === "seaborn") {
        await ensure("matplotlib");
        await py.loadPackage(["micropip"], quiet);
        await py.runPythonAsync(`import micropip\nawait micropip.install("seaborn==${cfg.seaborn}")`);
      } else if (pkg !== "numpy" && pkg !== "pandas") {
        await py.loadPackage([pkg], quiet);
      }
      if (WARMUP[pkg]) py.runPython(WARMUP[pkg]);
      post({ type: "pkg", name: pkg, state: "loaded" });
    } catch (e) {
      delete loading[pkg];
      post({ type: "pkg", name: pkg, state: "error", error: String(e && e.message || e) });
      throw e;
    }
  })();
  return loading[pkg];
}

async function boot(c) {
  cfg = c;
  try {
    post({ type: "status", text: "Downloading Python…" });
    const mod = await import(c.indexURL + "pyodide.mjs");
    py = await mod.loadPyodide({ indexURL: c.indexURL, stdout: () => {}, stderr: () => {} });
    post({ type: "status", text: "Loading NumPy + pandas…" });
    await py.loadPackage(["numpy", "pandas"], quiet);
    py.FS.mkdirTree("/drill");
    for (const [name, src] of Object.entries(c.files)) py.FS.writeFile("/drill/" + name, src);
    py.runPython("import os, sys\nos.environ['MPLBACKEND'] = 'Agg'\nsys.path.insert(0, '/drill')\nimport json, harness");
    harness = py.pyimport("harness");
    py.globals.set("_solutions_json", JSON.stringify(c.solutions));
    py.runPython("harness.SOLUTIONS.update(json.loads(_solutions_json))\ndel _solutions_json");
    loading.numpy = loading.pandas = Promise.resolve();
    post({ type: "ready" });
  } catch (e) {
    post({ type: "fatal", error: String(e && e.message || e) });
    return;
  }
  for (const pkg of BACKGROUND) {
    try { await ensure(pkg); } catch (e) { /* reported via pkg message; retried on demand */ }
  }
  post({ type: "bg-done" });
}

function wantedPackages(job, needs) {
  const want = new Set(needs || []);
  const src = [job.code || "", job.problem ? job.problem.solution + "\n" + job.problem.setup : ""].join("\n");
  const re = /^\s*(?:from|import)\s+([A-Za-z_]\w*)/gm;
  let m;
  while ((m = re.exec(src))) if (IMPORT_TO_PKG[m[1]]) want.add(IMPORT_TO_PKG[m[1]]);
  if (/\b(plt|sns)\./.test(job.code || "")) { want.add("matplotlib"); want.add("seaborn"); }
  if (want.has("matplotlib")) want.add("seaborn");
  return [...want];
}

let chain = Promise.resolve();

async function runJob(m) {
  try {
    for (const pkg of wantedPackages(m.job, m.needs)) {
      if (!loading[pkg]) post({ type: "waiting", id: m.id, pkg });
      await ensure(pkg);
    }
  } catch (e) {
    post({ type: "result", id: m.id, result: { internal_error: "Could not load a package: " + e } });
    return;
  }
  post({ type: "started", id: m.id });
  let text;
  try {
    py.globals.set("_job_json", JSON.stringify(m.job));
    text = py.runPython("json.dumps(harness.run_job(json.loads(_job_json)), default=str)");
  } catch (e) {
    text = JSON.stringify({ internal_error: String(e && e.message || e) });
  }
  post({ type: "result", id: m.id, result: JSON.parse(text) });
}

self.onmessage = (e) => {
  const m = e.data;
  if (m.type === "init") boot(m);
  else if (m.type === "job") chain = chain.then(() => runJob(m));
  else if (m.type === "ensure") ensure(m.pkg).catch(() => {});
};
