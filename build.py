#!/usr/bin/env python3
"""Build LeetStats: validate problems, then generate index.html and COVERAGE.md.

    python build.py                 # validate new/changed problems, rebuild
    python build.py --all           # revalidate everything
    python build.py --only pd-047,pd-048
    python build.py --engine pyodide   # validate inside Pyodide (Node + tools/)
    python build.py --no-validate   # rebuild the page from cached results only

Validation (per problem): the reference passes every hidden test twice with
no warnings and within the time budget; the starter fails; every wrong
solution fails. Problems that fail validation are dropped from the page and
reported. See DEVELOPMENT.md / CLAUDE.md for the problem schema.
"""
import argparse
import ast
import datetime as dt
import hashlib
import html
import json
import os
import re
import runpy
import shutil
import subprocess
import sys
import textwrap

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "problems"))
from _meta import CHAINS, DOC_DOMAINS, SECTIONS, TAGS  # noqa: E402

PYODIDE_VERSION = "314.0.7"
PYODIDE_INDEX = f"https://cdn.jsdelivr.net/pyodide/v{PYODIDE_VERSION}/full/"
CODEMIRROR = "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.21/"
SEABORN_VERSION = "0.13.2"
# Library versions shipped by Pyodide 314.0.7 (pyodide-lock.json); CPython
# validation should use exactly these (see requirements-validate.txt).
PINS = {"python": "3.14.2", "numpy": "2.4.6", "pandas": "3.0.2", "sklearn": "1.8.0",
        "matplotlib": "3.10.8", "scipy": "1.18.0", "statsmodels": "0.14.6",
        "lightgbm": "4.6.0", "seaborn": SEABORN_VERSION}
BUDGET = {"cpython": 1.5, "pyodide": 3.0}   # seconds for a full Submit (reference + candidate)
CACHE = os.path.join(ROOT, ".build", "cache.json")
REQUIRED = ["id", "title", "difficulty", "tags", "statement", "signature", "setup", "tests",
            "hint1", "hint2", "solution", "explanation", "docs"]
DIFFS = ["Easy", "Medium", "Hard"]
PKG_FOR_IMPORT = {"sklearn": "scikit-learn", "scipy": "scipy", "statsmodels": "statsmodels",
                  "lightgbm": "lightgbm", "seaborn": "seaborn", "matplotlib": "matplotlib"}


# ---------------------------------------------------------------------------
# Loading content
# ---------------------------------------------------------------------------
def dedent(s):
    return textwrap.dedent(s or "").strip("\n") + "\n" if s else ""


def load_problems():
    problems = []
    for key, prefix, title, needs in SECTIONS:
        path = os.path.join(ROOT, "problems", f"{key}.py")
        if not os.path.exists(path):
            continue
        mod = runpy.run_path(path)
        if mod.get("SECTION") != key:
            raise SystemExit(f"{path}: SECTION must be {key!r}")
        for p in mod["PROBLEMS"]:
            p = dict(p)
            p.setdefault("section", key)
            for f in ("setup", "tests", "solution", "starter"):
                if p.get(f):
                    p[f] = dedent(p[f])
            p["statement"] = textwrap.dedent(p.get("statement", "")).strip()
            p["explanation"] = textwrap.dedent(p.get("explanation", "")).strip()
            p["hint2"] = textwrap.dedent(p.get("hint2", "")).strip()
            p["wrong_solutions"] = [w if isinstance(w, dict) else {"code": w}
                                    for w in p.get("wrong_solutions", [])]
            for w in p["wrong_solutions"]:
                w["code"] = dedent(w["code"])
            problems.append(p)
    return problems


def load_path(problems):
    path_file = os.path.join(ROOT, "problems", "path.txt")
    ids = []
    if os.path.exists(path_file):
        with open(path_file, encoding="utf-8") as f:
            for line in f:
                line = line.split("#", 1)[0].strip()
                if line:
                    ids.append(line)
    known = {p["id"] for p in problems}
    order = [i for i in ids if i in known]
    missing = [p["id"] for p in problems if p["id"] not in set(order)]
    return order + missing, [i for i in ids if i not in known], missing


def load_module(rel):
    path = os.path.join(ROOT, rel)
    return runpy.run_path(path) if os.path.exists(path) else {}


# ---------------------------------------------------------------------------
# Static checks
# ---------------------------------------------------------------------------
CODE_SPAN = re.compile(r"`([^`]+)`")
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def called_names(text):
    """Function/method names a hint drills: names that are called, foo( or .foo(,
    plus a trailing attribute access such as `.T` or `.dt` (module paths like
    np.random.default_rng contribute only default_rng)."""
    names = set()
    for m in re.finditer(r"([A-Za-z_][A-Za-z0-9_]*)\s*\(", text):
        names.add(m.group(1))
    for span in CODE_SPAN.findall(text) or [text]:
        m = re.search(r"\.([A-Za-z_][A-Za-z0-9_]*)\s*$", span.strip())
        if m:
            names.add(m.group(1))
    return {n for n in names if len(n) >= 2 and n not in ("def", "return", "lambda")}


# Constructors and builtins that appear in hints without being "the" brick.
GENERIC_NAMES = {"series", "dataframe", "array", "list", "dict", "len", "range", "float", "int", "str",
                 "print", "sum", "max", "min", "abs", "sorted", "zip", "enumerate", "tuple", "set", "round"}


def fn_params(code, name="solve"):
    tree = ast.parse(code)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return [a.arg for a in node.args.args]
    return None


def static_check(p, prefix):
    errs, warns = [], []
    for f in REQUIRED:
        if not p.get(f):
            errs.append(f"missing field {f!r}")
    if errs:
        return errs, warns
    if not re.fullmatch(rf"{prefix}-\d{{3}}", p["id"]):
        errs.append(f"id must look like {prefix}-NNN")
    if p["difficulty"] not in DIFFS:
        errs.append(f"difficulty must be one of {DIFFS}")
    vocab = TAGS[p["section"]]
    for t in p["tags"]:
        if t not in vocab:
            errs.append(f"tag {t!r} not in the {p['section']} vocabulary (problems/_meta.py)")
    hint_names = {n.lower() for n in called_names(p["hint1"] + "\n" + p["hint2"])} - GENERIC_NAMES
    for t in p["tags"]:
        clash = set(re.findall(r"[a-z0-9]+", t.lower())) & hint_names
        if clash:
            errs.append(f"tag {t!r} names the function {sorted(clash)} (spoils the hint)")
    if p["section"] not in ("sklearn", "chains"):
        spans = " ".join(CODE_SPAN.findall(p["statement"]))
        for n in called_names("\n".join(f"`{m}`" for m in CODE_SPAN.findall(p["hint1"]))):
            if n in p.get("allow_in_statement", []):
                continue
            if re.search(rf"(\.{n}\b|\b{n}\s*\()", spans):
                errs.append(f"statement mentions `{n}` from Hint 1 (say what to compute, not which function)")
    try:
        sig_params = fn_params(p["signature"] + "\n    pass\n")
    except SyntaxError:
        sig_params = None
        errs.append("signature is not a valid def line")
    try:
        sol_params = fn_params(p["solution"])
        if sol_params is None:
            errs.append("solution must define solve()")
        elif sig_params is not None and sol_params != sig_params:
            errs.append(f"solution params {sol_params} != signature params {sig_params}")
    except SyntaxError as e:
        errs.append(f"solution has a syntax error: {e}")
    for f in ("setup", "tests", "starter"):
        if p.get(f):
            try:
                ast.parse(p[f])
            except SyntaxError as e:
                errs.append(f"{f} has a syntax error: {e}")
    try:
        ast.parse(p["hint2"])
    except SyntaxError:
        warns.append("hint2 is not valid Python on its own (fine for fragments, but check it)")
    body = [l for l in p["solution"].splitlines()
            if l.strip() and not l.strip().startswith(("#", "import ", "from ", "def solve"))]
    limit = 15 if p["difficulty"] == "Hard" else 8
    if len(body) > limit:
        warns.append(f"reference solution has {len(body)} lines (> {limit})")
    if len(p["explanation"]) > 600:
        warns.append(f"explanation is long ({len(p['explanation'])} chars; aim for 1-3 lines)")
    for url in p["docs"]:
        if not re.match(r"https://(" + "|".join(map(re.escape, DOC_DOMAINS)) + r")/", url):
            errs.append(f"docs URL not on an official domain: {url}")
    if p["difficulty"] in ("Medium", "Hard") and not p["wrong_solutions"]:
        errs.append("Medium/Hard problems need at least one realistic wrong solution")
    if p["section"] == "plotting" and not p.get("plot"):
        errs.append("plotting problems need a plot spec: plot=dict(returns=..., checks=[...])")
    if p["section"] == "chains":
        if p.get("chain") not in CHAINS or not isinstance(p.get("step"), int):
            errs.append(f"chain problems need chain in {list(CHAINS)} and an int step")
    if p["section"] == "bugs" and not p.get("starter"):
        errs.append("fix-the-bug problems need the buggy code as starter")
    return errs, warns


# ---------------------------------------------------------------------------
# Markdown (small subset: paragraphs, lists, code, emphasis, links, tables)
# ---------------------------------------------------------------------------
def md_inline(s):
    out = []
    for part in re.split(r"(`[^`]+`)", s):
        if len(part) > 1 and part.startswith("`") and part.endswith("`"):
            out.append(f"<code>{html.escape(part[1:-1], quote=False)}</code>")
            continue
        t = html.escape(part, quote=False)
        t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', t)
        t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
        t = re.sub(r"(?<![\w*])\*(?![\s*])(.+?)(?<![\s*])\*(?![\w*])", r"<em>\1</em>", t)
        out.append(t)
    return "".join(out)


LIST_RE = re.compile(r"^(\s*)([-*]|\d+\.)\s+(.*)$")


def _render_list(items, start=0, indent=None):
    """items: [(indent, ordered, text)] -> html, next index"""
    if start >= len(items):
        return "", start
    indent = items[start][0] if indent is None else indent
    tag = "ol" if items[start][1] else "ul"
    parts, i = [f"<{tag}>"], start
    while i < len(items) and items[i][0] >= indent:
        if items[i][0] > indent:
            sub, i = _render_list(items, i, items[i][0])
            parts[-1] = parts[-1].replace("</li>", sub + "</li>")
            continue
        parts.append(f"<li>{md_inline(items[i][2])}</li>")
        i += 1
    parts.append(f"</{tag}>")
    return "".join(parts), i


def md(text):
    lines = textwrap.dedent(text or "").strip("\n").split("\n")
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("```"):
            lang = line.strip()[3:].strip() or "python"
            buf, i = [], i + 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            code = html.escape(textwrap.dedent("\n".join(buf)), quote=False)
            out.append(f'<pre class="code" data-lang="{lang}"><code>{code}</code></pre>')
            i += 1
            continue
        if not line.strip():
            i += 1
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            lvl = min(len(m.group(1)) + 2, 6)
            out.append(f"<h{lvl}>{md_inline(m.group(2))}</h{lvl}>")
            i += 1
            continue
        if LIST_RE.match(line):
            items = []
            while i < len(lines) and lines[i].strip():
                lm = LIST_RE.match(lines[i])
                if lm:
                    items.append([len(lm.group(1)), lm.group(2)[0].isdigit(), lm.group(3)])
                elif items:
                    items[-1][2] += " " + lines[i].strip()
                i += 1
            out.append(_render_list(items)[0])
            continue
        if line.lstrip().startswith("|"):
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            head = "".join(f"<th>{md_inline(c)}</th>" for c in rows[0])
            body = "".join("<tr>" + "".join(f"<td>{md_inline(c)}</td>" for c in r) + "</tr>" for r in rows[1:])
            out.append(f'<table class="md"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>')
            continue
        buf = []
        while i < len(lines) and lines[i].strip() and not LIST_RE.match(lines[i]) \
                and not lines[i].strip().startswith(("```", "#", "|")):
            buf.append(lines[i].strip())
            i += 1
        out.append(f"<p>{md_inline(' '.join(buf))}</p>")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Validation engine
# ---------------------------------------------------------------------------
def sha(*parts):
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8") if isinstance(p, str) else json.dumps(p, sort_keys=True).encode())
    return h.hexdigest()[:16]


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


def runtime_hash():
    return sha(read("runtime/harness.py"), read("runtime/datasets.py"), read("runtime/validate.py"))


def problem_hash(p, by_id, rt):
    deps = sorted(set(re.findall(r"REF\(\s*['\"]([\w-]+)['\"]", (p.get("setup") or "") + (p.get("tests") or ""))))
    dep_src = [by_id[d]["solution"] for d in deps if d in by_id]
    rec = {k: v for k, v in p.items() if k not in ("num",)}
    return sha(rec, dep_src, rt)


def find_node(arg):
    for cand in [arg, os.environ.get("NODE"), shutil.which("node")]:
        if cand and os.path.exists(cand):
            return cand
    return None


def run_engine(engine, jobs, args):
    os.makedirs(os.path.join(ROOT, ".build"), exist_ok=True)
    jobs_path = os.path.join(ROOT, ".build", "jobs.json")
    out_path = os.path.join(ROOT, ".build", "results.json")
    with open(jobs_path, "w", encoding="utf-8") as f:
        json.dump(jobs, f)
    if os.path.exists(out_path):
        os.remove(out_path)
    if engine == "pyodide":
        node = find_node(args.node)
        cmd = [node, os.path.join(ROOT, "tools", "run_pyodide.mjs"), ROOT,
               ".build/jobs.json", ".build/results.json"]
    else:
        cmd = [args.python or sys.executable, os.path.join(ROOT, "runtime", "validate.py"), jobs_path, out_path]
    print(f"$ {' '.join(cmd)}", flush=True)
    proc = subprocess.run(cmd, cwd=ROOT)
    if proc.returncode != 0 or not os.path.exists(out_path):
        raise SystemExit(f"validation engine failed (exit {proc.returncode})")
    with open(out_path, encoding="utf-8") as f:
        return json.load(f)


def pick_engine(args):
    if args.engine != "auto":
        return args.engine
    have_node = find_node(args.node) and os.path.exists(os.path.join(ROOT, "tools", "node_modules", "pyodide"))
    return "pyodide" if have_node else "cpython"


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------
def needs_for(p, section_needs):
    pk = list(section_needs)
    src = (p.get("solution") or "") + (p.get("setup") or "") + (p.get("tests") or "")
    for mod, pkg in PKG_FOR_IMPORT.items():
        if re.search(rf"^\s*(from|import)\s+{mod}\b", src, re.M) and pkg not in pk:
            pk.append(pkg)
    if "matplotlib" in pk and "seaborn" not in pk:
        pk.append("seaborn")
    return pk


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--all", action="store_true", help="revalidate every problem")
    ap.add_argument("--only", help="comma-separated problem ids to (re)validate")
    ap.add_argument("--engine", default="auto", choices=["auto", "cpython", "pyodide"])
    ap.add_argument("--python", help="interpreter for the cpython engine (default: this one)")
    ap.add_argument("--node", help="path to node for the pyodide engine")
    ap.add_argument("--no-validate", action="store_true", help="use cached results only")
    ap.add_argument("--keep-failing", action="store_true", help="include failing problems in the page")
    ap.add_argument("--check-links", action="store_true", help="verify every docs URL (and #anchor) resolves, then exit")
    args = ap.parse_args()
    if args.check_links:
        raise SystemExit(check_links(load_problems()))

    problems = load_problems()
    prefix = {k: pre for k, pre, _, _ in SECTIONS}
    section_needs = {k: needs for k, _, _, needs in SECTIONS}
    by_id, errors, warnings_ = {}, {}, {}
    for p in problems:
        if p["id"] in by_id:
            raise SystemExit(f"duplicate problem id {p['id']}")
        by_id[p["id"]] = p
        e, w = static_check(p, prefix[p["section"]])
        if e:
            errors[p["id"]] = e
        if w:
            warnings_[p["id"]] = w
    order, unknown_in_path, not_in_path = load_path(problems)
    if unknown_in_path:
        print(f"note: path.txt lists unknown ids (ignored): {unknown_in_path}")
    if not_in_path:
        print(f"note: not in path.txt yet (appended at the end): {not_in_path}")

    cards_mod = load_module("content/cards.py")
    pg_mod = load_module("content/playground.py")
    predict = cards_mod.get("PREDICT", [])
    recall_extra = cards_mod.get("RECALL_EXTRA", [])
    prompts = pg_mod.get("PROMPTS", [])

    cache = {"problems": {}, "snippets": {}, "walkthroughs": {}}
    if os.path.exists(CACHE):
        with open(CACHE, encoding="utf-8") as f:
            cache.update(json.load(f))
    rt = runtime_hash()
    only = set(args.only.split(",")) if args.only else None
    todo = []
    for p in problems:
        if p["id"] in errors:
            continue
        h = problem_hash(p, by_id, rt)
        p["_hash"] = h
        cached = cache["problems"].get(p["id"])
        stale = not cached or cached.get("hash") != h
        if args.all or (only and p["id"] in only) or (stale and not only):
            todo.append(p)
    snip_todo = {c["id"]: dedent(c["code"]) for c in predict
                 if args.all or cache["snippets"].get(c["id"], {}).get("hash") != sha(dedent(c["code"]), rt)}
    walk_todo = {w["id"]: w["steps"] for w in prompts
                 if args.all or cache["walkthroughs"].get(w["id"], {}).get("hash") != sha(w["steps"], rt)}

    engine = pick_engine(args)
    if (todo or snip_todo or walk_todo) and not args.no_validate:
        print(f"validating {len(todo)} problem(s), {len(snip_todo)} snippet(s), "
              f"{len(walk_todo)} walkthrough(s) with the {engine} engine", flush=True)
        jobs = {"budget": BUDGET[engine],
                "solutions": {p["id"]: p["solution"] for p in problems},
                "problems": [{k: v for k, v in p.items() if not k.startswith("_")} for p in todo],
                "snippets": snip_todo, "walkthroughs": walk_todo}
        res = run_engine(engine, jobs, args)
        v = res["versions"]
        mism = {k: (v.get(k), want) for k, want in PINS.items() if v.get(k) != want}
        if mism:
            print(f"WARNING: engine versions differ from Pyodide {PYODIDE_VERSION} pins: {mism}")
        stamp = dt.datetime.now().isoformat(timespec="seconds")
        for pid, r in res["problems"].items():
            cache["problems"][pid] = {"hash": by_id[pid]["_hash"], "result": r, "engine": engine,
                                      "versions": v, "validated": stamp}
        for sid, r in res["snippets"].items():
            code = next(dedent(c["code"]) for c in predict if c["id"] == sid)
            cache["snippets"][sid] = {"hash": sha(code, rt), **r}
        for wid, r in res["walkthroughs"].items():
            steps = next(w["steps"] for w in prompts if w["id"] == wid)
            cache["walkthroughs"][wid] = {"hash": sha(steps, rt), **r}
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        with open(CACHE, "w", encoding="utf-8") as f:
            json.dump(cache, f)

    # ---------------- assemble page data ----------------
    dropped = {}
    included = []
    for pid in order:
        p = by_id[pid]
        if pid in errors:
            dropped[pid] = errors[pid]
            continue
        c = cache["problems"].get(pid)
        if not c:
            dropped[pid] = ["not validated yet"]
            continue
        r = c["result"]
        if c["hash"] != p.get("_hash"):
            dropped[pid] = ["changed since last validation (run without --no-validate)"]
            continue
        if not r["ok"] and not args.keep_failing:
            dropped[pid] = r["errors"]
            continue
        included.append((p, r))

    page_problems = []
    for num, (p, r) in enumerate(included, 1):
        page_problems.append({
            "id": p["id"], "num": num, "section": p["section"], "title": p["title"],
            "difficulty": p["difficulty"], "tags": p["tags"],
            "statement": md(p["statement"]), "signature": p["signature"],
            "starter": p.get("starter") or (p["signature"] + "\n    pass\n"),
            "setup": p["setup"], "tests": p["tests"], "solution": p["solution"],
            "compare": p.get("compare"), "plot": p.get("plot"), "mutation_check": p.get("mutation_check", False),
            "hint1": md_inline(p["hint1"]), "hint2": p["hint2"], "explanation": md(p["explanation"]),
            "docs": p["docs"], "chain": p.get("chain"), "step": p.get("step"),
            "recall": p.get("recall") or p["title"],
            "needs": needs_for(p, section_needs[p["section"]]),
            "example": {"inputs": r.get("example_inputs"), "expected": r.get("example_expected")},
            "target_image": r.get("target_image"),
            "expected_plots": r.get("expected_plots"),
        })

    pred_cards = []
    for c in predict:
        res = cache["snippets"].get(c["id"])
        if not res or res.get("hash") != sha(dedent(c["code"]), rt):
            print(f"note: predict card {c['id']} has no current output; skipped")
            continue
        pred_cards.append({"id": c["id"], "topic": c.get("topic", ""), "section": c.get("section", "pandas"),
                           "code": dedent(c["code"]).rstrip("\n"), "output": res["output"],
                           "note": md(c.get("note", ""))})
    recall_cards = [{"id": c["id"], "section": c.get("section", ""), "front": c["front"],
                     "back": textwrap.dedent(c["back"]).strip()} for c in recall_extra]
    pg = []
    for w in prompts:
        res = cache["walkthroughs"].get(w["id"], {})
        if not res.get("ok"):
            dropped[w["id"]] = [res.get("error", "walkthrough not validated")]
            continue
        pg.append({"id": w["id"], "title": w["title"], "datasets": w.get("datasets", []),
                   "prompt": md(w["prompt"]), "minutes": w.get("minutes", 45),
                   "steps": [{"md": md(s.get("md", "")), "code": dedent(s.get("code", "")).rstrip("\n")}
                             for s in w["steps"]]})

    pre = re.search(r"PLAYGROUND_PRELOAD = '''(.*?)'''", read("runtime/harness.py"), re.S).group(1)
    data = {
        "built": dt.datetime.now().isoformat(timespec="seconds"),
        "pyodide": {"version": PYODIDE_VERSION, "indexURL": PYODIDE_INDEX, "seaborn": SEABORN_VERSION},
        "sections": [{"key": k, "prefix": pre_, "title": t, "chains": CHAINS if k == "chains" else None}
                     for k, pre_, t, _ in SECTIONS],
        "tags": TAGS,
        "problems": page_problems,
        "cards": {"predict": pred_cards, "recall_extra": recall_cards},
        "playground": pg,
        "playground_preload": pre.strip(),
        "runtime": {"harness.py": read("runtime/harness.py"), "datasets.py": read("runtime/datasets.py")},
    }
    write_page(data)
    write_coverage([p for p, _ in included], dropped)
    report(included, dropped, warnings_, pred_cards, recall_cards, pg, cache)


def check_links(problems):
    """Fetch every docs URL once; report HTTP errors and missing #anchors."""
    import concurrent.futures
    import urllib.request
    urls = {}
    for p in problems:
        for u in p.get("docs", []):
            urls.setdefault(u, []).append(p["id"])

    def fetch(u):
        try:
            req = urllib.request.Request(u.split("#")[0], headers={"User-Agent": "Mozilla/5.0 leetstats-link-check"})
            with urllib.request.urlopen(req, timeout=20) as r:
                body = r.read().decode("utf-8", "ignore")
            anchor = u.split("#", 1)[1] if "#" in u else None
            return None if anchor is None or f'id="{anchor}"' in body else "missing #anchor"
        except Exception as e:  # HTTP errors, timeouts
            return str(e)[:80]

    with concurrent.futures.ThreadPoolExecutor(16) as ex:
        bad = [(u, err) for u, err in zip(urls, ex.map(fetch, urls)) if err]
    print(f"{len(urls)} docs URLs checked, {len(bad)} broken")
    for u, err in bad:
        print(f"  {err}: {u}  ({', '.join(urls[u])})")
    return 1 if bad else 0


def data_uri(rel):
    """Embed a small image so index.html stays a single self-contained file.
    The icons are generated from logo/logo.png (see BUILD_LOG.md)."""
    import base64
    with open(os.path.join(ROOT, rel), "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")


def write_page(data):
    tpl = read("src/template.html")
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    worker = read("src/worker.js").replace("</", "<\\/")
    page = (tpl.replace("/*__CSS__*/", read("src/app.css"))
               .replace("/*__APP_JS__*/", read("src/app.js").replace("</script", "<\\/script"))
               .replace("/*__WORKER_JS__*/", worker)
               .replace("__CODEMIRROR__", CODEMIRROR)
               .replace("__ICON_LIGHT__", data_uri("logo/icon-light.png"))
               .replace("__ICON_DARK__", data_uri("logo/icon-dark.png"))
               .replace("__FAVICON__", data_uri("logo/favicon.png"))
               .replace("__DATA_JSON__", blob))
    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(page)
    print(f"wrote index.html ({len(page) / 1e6:.2f} MB)")


def write_coverage(problems, dropped):
    lines = ["# Coverage", "",
             "Auto-generated by `build.py`. One line per brick (from Hint 1), grouped by section and topic.",
             "Use it to spot gaps before adding problems (`/add-problems`).", ""]
    titles = {k: t for k, _, t, _ in SECTIONS}
    lines.append("| Section | Easy | Medium | Hard | Total |")
    lines.append("|---|---|---|---|---|")
    tot = {d: 0 for d in DIFFS}
    for key, _, title, _ in SECTIONS:
        ps = [p for p in problems if p["section"] == key]
        cnt = {d: sum(p["difficulty"] == d for p in ps) for d in DIFFS}
        for d in DIFFS:
            tot[d] += cnt[d]
        lines.append(f"| {title} | {cnt['Easy']} | {cnt['Medium']} | {cnt['Hard']} | {len(ps)} |")
    n = sum(tot.values()) or 1
    lines.append(f"| **All** | {tot['Easy']} ({tot['Easy'] * 100 // n}%) | {tot['Medium']} ({tot['Medium'] * 100 // n}%) "
                 f"| {tot['Hard']} ({tot['Hard'] * 100 // n}%) | {sum(tot.values())} |")
    lines.append("")
    for key, _, title, _ in SECTIONS:
        ps = [p for p in problems if p["section"] == key]
        if not ps:
            continue
        lines.append(f"## {title} ({len(ps)})")
        lines.append("")
        topics = {}
        for p in ps:
            topics.setdefault(p["tags"][0], []).append(p)
        for t in TAGS[key]:
            if t not in topics:
                continue
            lines.append(f"### {t}")
            for p in topics[t]:
                brick = re.sub(r"\s+", " ", p["hint1"]).strip()
                extra = f" [chain {p['chain']} step {p['step']}]" if p.get("chain") else ""
                lines.append(f"- `{p['id']}` {p['difficulty'][0]} — {p['title']}{extra}: {brick}")
            lines.append("")
        unused = [t for t in TAGS[key] if t not in topics]
        if unused:
            lines.append(f"_Topics with no problem yet (as primary tag): {', '.join(unused)}_")
            lines.append("")
    if dropped:
        lines.append("## Not in the app (failed validation or not yet validated)")
        for pid, errs in dropped.items():
            lines.append(f"- `{pid}`: {errs[0].splitlines()[0][:200]}")
    with open(os.path.join(ROOT, "COVERAGE.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def report(included, dropped, warnings_, pred, recall, pg, cache):
    print("\n=== build report ===")
    print(f"{'section':<14}{'Easy':>6}{'Medium':>8}{'Hard':>6}{'Total':>7}")
    tot = {d: 0 for d in DIFFS}
    for key, _, title, _ in SECTIONS:
        ps = [p for p, _ in included if p["section"] == key]
        c = {d: sum(p["difficulty"] == d for p in ps) for d in DIFFS}
        for d in DIFFS:
            tot[d] += c[d]
        print(f"{title:<14}{c['Easy']:>6}{c['Medium']:>8}{c['Hard']:>6}{len(ps):>7}")
    print(f"{'TOTAL':<14}{tot['Easy']:>6}{tot['Medium']:>8}{tot['Hard']:>6}{sum(tot.values()):>7}")
    slow = sorted(((r.get("submit_seconds") or 0, p["id"]) for p, r in included), reverse=True)[:5]
    print(f"slowest submits: {', '.join(f'{i} {s:.2f}s' for s, i in slow)}")
    print(f"cards: {len(pred)} predict-the-output, {len(recall)} extra recall; playground prompts: {len(pg)}")
    if warnings_:
        print(f"\nwarnings ({len(warnings_)}):")
        for pid, ws in warnings_.items():
            for w in ws:
                print(f"  {pid}: {w}")
    if dropped:
        print(f"\nDROPPED ({len(dropped)}):")
        for pid, errs in dropped.items():
            for e in errs:
                print(f"  {pid}: {e.splitlines()[0]}")


if __name__ == "__main__":
    main()
