// Run runtime/validate.py inside Pyodide under Node (the same runtime the
// browser uses). Usage (build.py calls this):
//   node tools/run_pyodide.mjs <project root> <jobs.json> <results.json>
// One-time setup: cd tools && npm install
import { loadPyodide } from "pyodide";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const [, , root, jobs, out] = process.argv;
const here = path.dirname(fileURLToPath(import.meta.url));
const pkg = JSON.parse(readFileSync(path.join(here, "package.json"), "utf8"));
const seaborn = pkg.config && pkg.config.seaborn ? pkg.config.seaborn : "0.13.2";

const t0 = Date.now();
const py = await loadPyodide({ stdout: (s) => console.log(s), stderr: (s) => console.error(s) });
await py.loadPackage(["numpy", "pandas", "matplotlib", "scipy", "scikit-learn", "statsmodels",
  "lightgbm", "micropip"], { messageCallback: () => {} });
await py.runPythonAsync(`import micropip\nawait micropip.install("seaborn==${seaborn}")`);
console.log(`pyodide ${py.version} ready in ${((Date.now() - t0) / 1000).toFixed(1)}s`);

py.FS.mkdirTree("/proj");
py.FS.mount(py.FS.filesystems.NODEFS, { root: path.resolve(root) }, "/proj");
py.globals.set("_jobs", "/proj/" + jobs);
py.globals.set("_out", "/proj/" + out);
await py.runPythonAsync(`
import os, sys
os.environ["MPLBACKEND"] = "Agg"
sys.path.insert(0, "/proj/runtime")
import validate
validate.main(_jobs, _out)
`);
console.log(`done in ${((Date.now() - t0) / 1000).toFixed(1)}s`);
