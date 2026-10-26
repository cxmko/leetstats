"""Build-time validation runner. build.py writes a jobs JSON file and runs
this module with CPython (`python runtime/validate.py jobs.json out.json`) or
inside Pyodide under Node (tools/run_pyodide.mjs). Both produce the same
results JSON, so validation can run in the exact browser runtime."""
import ast
import contextlib
import io
import json
import os
import platform
import sys
import time
import traceback
import warnings

os.environ.setdefault("MPLBACKEND", "Agg")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import harness as H  # noqa: E402


def versions():
    out = {"python": platform.python_version(), "platform": sys.platform}
    for mod in ["numpy", "pandas", "sklearn", "matplotlib", "seaborn", "scipy", "statsmodels", "lightgbm"]:
        try:
            out[mod] = __import__(mod).__version__
        except Exception as e:  # pragma: no cover - reported to build.py
            out[mod] = f"unavailable ({type(e).__name__})"
    return out


def _params(signature):
    tree = ast.parse(signature.strip() + "\n    pass\n")
    fn = tree.body[0]
    return [a.arg for a in fn.args.args]


def _first_failure(r):
    if r.get("compile_error"):
        return "compile error: " + r["compile_error"].splitlines()[-1]
    for c in r["cases"]:
        if not c["passed"]:
            return f"{c['name']}: " + (c["error"].splitlines()[-1] if c["error"] else c["diff"])
    return None


def validate_problem(prob, budget):
    errors, notes = [], []
    info = {"id": prob["id"]}
    try:
        P = H.load_problem(prob)
        example = P["EXAMPLE"]()
        params = _params(prob["signature"])
        if sorted(example) != sorted(params):
            errors.append(f"EXAMPLE keys {sorted(example)} != signature params {params}")
        if len(P["TESTS"]) < 3:
            errors.append(f"needs at least 3 hidden tests, has {len(P['TESTS'])}")
        ref_fn = H.compile_function(prob["solution"], f"<reference {prob['id']}>")

        # 1. reference passes every test, twice (deterministic), with no warnings
        times = []
        for rep in range(2):
            t0 = time.perf_counter()
            r = H.evaluate(prob, prob["solution"], "tests", details=False, png=False, ref_fn=ref_fn)
            times.append(time.perf_counter() - t0)
            if not r["passed"]:
                errors.append(f"reference fails (run {rep + 1}): {_first_failure(r)}")
                break
            if r["warnings"]:
                errors.append(f"reference emits warnings: {r['warnings'][:2]}")
                break
        rx = H.evaluate(prob, prob["solution"], "example", details=True, png=False, ref_fn=ref_fn)
        if not rx["passed"]:
            errors.append(f"reference fails on the example: {_first_failure(rx)}")
        info["submit_seconds"] = round(min(times), 3)
        if min(times) > budget and not prob.get("plot"):
            errors.append(f"submit takes {min(times):.2f}s > budget {budget}s")
        info["case_ref_times"] = [c["ref_time"] for c in r["cases"]]

        # 2. the blank starter fails
        starter = prob.get("starter") or (prob["signature"] + "\n    pass\n")
        r = H.evaluate(prob, starter, "tests", details=False, png=False, ref_fn=ref_fn)
        if r["passed"]:
            errors.append("the starter code passes all tests")

        # 3. every wrong solution fails
        caught = []
        for k, w in enumerate(prob.get("wrong_solutions") or []):
            code = w["code"] if isinstance(w, dict) else w
            r = H.evaluate(prob, code, "tests", details=False, png=False, ref_fn=ref_fn)
            if r["passed"]:
                why = w.get("why", "") if isinstance(w, dict) else ""
                errors.append(f"wrong solution {k + 1} passes all tests ({why})")
            else:
                caught.append(_first_failure(r))
        info["wrong_caught_by"] = caught

        # 4. artifacts for the page: example inputs/expected output previews
        inputs = P["EXAMPLE"]()
        info["example_inputs"] = {k: H.preview(v) for k, v in inputs.items()}
        H._close_figures()
        exp = ref_fn(**P["EXAMPLE"]())
        if H.is_plot(exp):
            info["target_image"] = H.figure_png(exp, dpi=60)
            info["example_expected"] = {"kind": "figure", "type": type(exp).__name__}
            H._close_figures()
            pre = H.expected_plot_infos(prob, ref_fn)
            # the precomputed structures must reproduce a live reference run
            for which in ("example", "tests"):
                r2 = H.evaluate({**prob, "expected_plots": pre}, prob["solution"], which, details=False,
                                png=False, ref_fn=ref_fn)
                if not r2["passed"]:
                    errors.append(f"precomputed plot structure does not match the reference: {_first_failure(r2)}")
            t0 = time.perf_counter()
            H.evaluate({**prob, "expected_plots": pre}, prob["solution"], "tests", details=False, png=False, ref_fn=ref_fn)
            info["submit_seconds"] = round(time.perf_counter() - t0, 3)
            if info["submit_seconds"] > budget:
                errors.append(f"submit takes {info['submit_seconds']:.2f}s > budget {budget}s")
            info["expected_plots"] = pre
        else:
            if exp is None:
                errors.append("reference returns None on the example")
            info["example_expected"] = H.preview(exp)
        H._close_figures()
    except Exception:
        errors.append("problem definition error:\n" + traceback.format_exc(limit=6))
    info["errors"] = errors
    info["notes"] = notes
    info["ok"] = not errors
    return info


def run_snippet(code):
    """Predict-the-output cards: run like a REPL cell and capture what it shows."""
    ns = H.user_namespace()
    with H.capture() as (buf, w):
        try:
            val = H.run_cell(code, ns, "<snippet>")
            if val is not None:
                print(repr(val))
        except Exception as exc:
            print(f"{type(exc).__name__}: {exc}")
    H._close_figures()
    return {"output": buf.getvalue().rstrip("\n"), "warnings": H._warning_lines(w)}


def run_walkthrough(steps):
    H.playground_reset()
    ns = H._PLAYGROUND
    t0 = time.perf_counter()
    for i, step in enumerate(steps):
        code = step.get("code")
        if not code:
            continue
        with H.capture() as (_buf, w):
            try:
                H.run_cell(code, ns, f"<walkthrough step {i + 1}>")
            except Exception:
                return {"ok": False, "error": f"step {i + 1}:\n" + traceback.format_exc(limit=4)}
        H._close_figures()
        warns = [x for x in H._warning_lines(w) if "ConvergenceWarning" not in x]
        if warns:
            return {"ok": False, "error": f"step {i + 1} emits warnings: {warns[:2]}"}
    return {"ok": True, "seconds": round(time.perf_counter() - t0, 2)}


def _json_default(o):
    if hasattr(o, "item"):          # numpy scalars
        return o.item()
    if hasattr(o, "tolist"):
        return o.tolist()
    return str(o)


def main(jobs_path, out_path):
    with open(jobs_path, encoding="utf-8") as f:
        jobs = json.load(f)
    H.SOLUTIONS.update(jobs.get("solutions", {}))
    budget = jobs.get("budget", 3.0)
    out = {"versions": versions(), "problems": {}, "snippets": {}, "walkthroughs": {}}
    total = len(jobs.get("problems", []))
    for i, prob in enumerate(jobs.get("problems", []), 1):
        t0 = time.perf_counter()
        res = validate_problem(prob, budget)
        out["problems"][prob["id"]] = res
        status = "ok" if res["ok"] else "FAIL"
        print(f"[{i}/{total}] {prob['id']} {status} ({time.perf_counter() - t0:.1f}s)", flush=True)
        for e in res["errors"]:
            print("    - " + e.replace("\n", "\n      "), flush=True)
    for sid, code in jobs.get("snippets", {}).items():
        out["snippets"][sid] = run_snippet(code)
    for wid, steps in jobs.get("walkthroughs", {}).items():
        out["walkthroughs"][wid] = run_walkthrough(steps)
        print(f"walkthrough {wid}: {out['walkthroughs'][wid]}", flush=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, default=_json_default)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
