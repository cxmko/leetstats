"""Browser smoke test for index.html opened from file://.

Usage: pip install playwright; python tools/browser_check.py <project dir> [msedge|chrome]
(uses the installed Edge/Chrome; no browser download needed)
"""

import json, os, sys, time
from playwright.sync_api import sync_playwright

ROOT = sys.argv[1]
CHANNEL = sys.argv[2] if len(sys.argv) > 2 else "msedge"
SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".build", "shots")
os.makedirs(SHOTS, exist_ok=True)
URL = ROOT if ROOT.startswith("http") else "file:///" + os.path.join(ROOT, "index.html").replace("\\", "/")
DATA_SOL = {}
results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail else ""), flush=True)


def set_code(page, code, host="#editor-host"):
    page.evaluate("([h, c]) => document.querySelector(h + ' .CodeMirror').CodeMirror.setValue(c)", [host, code])


def get_code(page, host="#editor-host"):
    return page.evaluate("(h) => document.querySelector(h + ' .CodeMirror').CodeMirror.getValue()", host)


def wait_verdict(page, timeout=60000):
    page.wait_for_function("""() => { const v = document.querySelector('#results .verdict');
        return v && !/Running|Waiting|Loading/.test(v.textContent); }""", timeout=timeout)
    return page.inner_text("#results .verdict")


def solution_of(page, pid):
    return page.evaluate("(id) => window.__leetstats.BY_ID[id].solution", pid)


def open_problem(page, pid, review=False):
    page.evaluate("(h) => { location.hash = h; }", f"#problems/{pid}" + ("/review" if review else ""))
    page.wait_for_function("(id) => document.querySelector('.p-sub .pid') && document.querySelector('.p-sub .pid').textContent === id", arg=pid)


with sync_playwright() as p:
    browser = p.chromium.launch(channel=CHANNEL)
    ctx = browser.new_context(viewport={"width": 1500, "height": 950})
    page = ctx.new_page()
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    t0 = time.time()
    page.goto(URL)
    page.wait_for_selector("#plist li[data-id]")
    check("page renders problem list", page.locator("#plist li[data-id]").count() > 0)
    page.wait_for_function("() => window.__leetstats.Py.st.ready", timeout=120000)
    check("numpy+pandas ready", True, f"{time.time() - t0:.1f}s after load")
    page.screenshot(path=os.path.join(SHOTS, "01-problem-light.png"))

    # --- NumPy problem: run then submit the reference
    open_problem(page, "np-010")
    set_code(page, solution_of(page, "np-010"))
    page.click("#run-btn")
    v = wait_verdict(page)
    check("np-010 run matches example", "Matches" in v, v)
    page.click("#submit-btn")
    v = wait_verdict(page)
    check("np-010 submit accepted", "Accepted" in v, v)

    # --- pandas: wrong first (unlocks solution), then correct
    open_problem(page, "pd-036")
    wrong = solution_of(page, "pd-036").replace('transform("sum")', 'sum()')
    set_code(page, wrong)
    page.keyboard.press("Control+Shift+Enter") if False else page.click("#submit-btn")
    v = wait_verdict(page)
    check("pd-036 wrong submit rejected", "Wrong answer" in v, v)
    check("failure shows a diff", page.locator("#results .diffmsg").count() > 0, page.inner_text("#results .diffmsg") if page.locator("#results .diffmsg").count() else "")
    check("solution unlocked after failed submit", "unlocked" in page.inner_text("#sol-block"))
    page.screenshot(path=os.path.join(SHOTS, "02-wrong-answer.png"))
    set_code(page, solution_of(page, "pd-036"))
    page.click("#editor-host .CodeMirror")
    page.keyboard.press("Control+Shift+Enter")
    v = wait_verdict(page)
    check("pd-036 submit via Ctrl+Shift+Enter accepted", "Accepted" in v, v)
    check("reference solution shown after accept", "reference solution" in page.inner_text("#sol-block").lower())
    page.screenshot(path=os.path.join(SHOTS, "03-accepted.png"))

    # --- plot problem
    open_problem(page, "pl-001")
    check("plot target thumbnail shown", page.locator("#problem .target img").count() == 1)
    set_code(page, solution_of(page, "pl-001"))
    page.click("#run-btn")
    v = wait_verdict(page, 120000)
    check("pl-001 run renders a figure", page.locator("#results .fig img").count() >= 1, v)
    page.click("#submit-btn")
    v = wait_verdict(page, 60000)
    check("pl-001 submit accepted (structure checks)", "Accepted" in v, v)
    bad = solution_of(page, "pl-001").replace('ax.plot(s["date"], s["close"])', 'ax.plot(s["close"].to_numpy())')
    set_code(page, bad)
    page.click("#submit-btn")
    v = wait_verdict(page, 60000)
    check("pl-001 wrong plot rejected", "Wrong" in v, page.inner_text("#results .diffmsg") if page.locator("#results .diffmsg").count() else v)
    page.screenshot(path=os.path.join(SHOTS, "04-plot.png"))

    # --- sklearn problem (imports sklearn)
    open_problem(page, "sk-002")
    set_code(page, solution_of(page, "sk-002"))
    page.click("#submit-btn")
    v = wait_verdict(page, 180000)
    check("sk-002 submit accepted", "Accepted" in v, v)

    # --- Stop kills an infinite loop
    open_problem(page, "st-001")
    set_code(page, "def solve(ab):\n    while True:\n        pass\n")
    page.click("#run-btn")
    page.wait_for_function("() => window.__leetstats.Py.st.current && window.__leetstats.Py.st.current.started", timeout=120000)
    time.sleep(1.5)
    page.click("#stop-btn")
    v = wait_verdict(page)
    check("Stop interrupts an infinite loop", "Stopped" in v, v)
    page.wait_for_function("() => window.__leetstats.Py.st.ready", timeout=120000)
    set_code(page, solution_of(page, "st-001"))
    page.click("#submit-btn")
    v = wait_verdict(page, 180000)
    check("Python works again after Stop (st-001 accepted)", "Accepted" in v, v)

    # --- 10 s limit
    open_problem(page, "qt-002")
    set_code(page, "def solve(returns):\n    while True:\n        pass\n")
    t1 = time.time()
    page.click("#run-btn")
    v = wait_verdict(page, 120000)
    check("10 s time limit enforced", "Time limit" in v, f"{v} after {time.time() - t1:.1f}s")
    page.wait_for_function("() => window.__leetstats.Py.st.ready", timeout=120000)

    # --- traceback line numbers match the editor
    set_code(page, "def solve(returns):\n    x = 1\n    return returns.no_such_method()\n")
    page.click("#run-btn")
    wait_verdict(page)
    tb = page.inner_text("#results pre.err")
    check("traceback shows editor line numbers", "Line 3, in solve" in tb and "AttributeError" in tb, tb.replace("\n", " | "))

    # --- review mode starts from the blank starter
    starter = page.evaluate("() => window.__leetstats.BY_ID['pd-036'].starter")
    open_problem(page, "pd-036", review=True)
    check("review mode editor = blank starter", get_code(page).strip() == starter.strip(), get_code(page)[:60])
    check("review chip visible", page.locator(".chip.review").count() > 0)
    open_problem(page, "pd-036")
    check("normal mode keeps the draft", "transform" in get_code(page))

    # --- chain step (uses REF of the previous step)
    open_problem(page, "ch-003")
    set_code(page, solution_of(page, "ch-003"))
    page.click("#submit-btn")
    v = wait_verdict(page, 60000)
    check("chain step ch-003 accepted", "Accepted" in v, v)

    # --- progress survives reload
    page.reload()
    page.wait_for_selector("#plist li[data-id]")
    st = page.evaluate("() => JSON.parse(localStorage.getItem('dsdrill.v1')).problems")
    solved = sorted(k for k, v in st.items() if v.get("solvedAt"))
    check("progress survives reload", {"np-010", "pd-036", "pl-001", "sk-002", "ch-003"} <= set(solved), str(solved))
    check("sidebar shows solved icons", page.locator("#plist .s-solved").count() + page.locator("#plist .s-due").count() >= 4)

    # --- other views render
    for hsh in ["today", "review", "cards", "bricks", "stats"]:
        page.evaluate("(h) => { location.hash = h; }", "#" + hsh)
        page.wait_for_timeout(400)
        check(f"view #{hsh} renders", len(page.inner_text(f"#view-{hsh}")) > 50)
        page.screenshot(path=os.path.join(SHOTS, f"05-{hsh}.png"))
    page.evaluate("() => { location.hash = '#cards'; }")
    page.wait_for_timeout(300)
    page.keyboard.press("Space")
    page.wait_for_timeout(200)
    check("flashcard reveals answer", page.locator("#fc-answer:not([hidden])").count() == 1)
    page.keyboard.press("3")
    page.wait_for_timeout(200)

    # --- playground
    page.evaluate("() => { location.hash = '#playground'; }")
    page.wait_for_timeout(500)
    page.wait_for_function("() => window.__leetstats.Py.st.ready", timeout=120000)
    set_code(page, "churn.groupby('contract')['churned'].mean()", "#pg-editor")
    page.click("#pg-run")
    page.wait_for_function("() => { const c = [...document.querySelectorAll('#pg-out .cell-body')].pop(); return c && !/Running|Waiting|Loading|Resetting/.test(c.textContent); }", timeout=120000)
    out = page.inner_text("#pg-out")
    check("playground shows a value", "Month-to-month" in out, out[-200:].replace("\n", " "))
    set_code(page, "ax = sns.histplot(churn, x='tenure', hue='churned')\nx_saved = 41", "#pg-editor")
    page.click("#pg-run")
    page.wait_for_timeout(500)
    page.wait_for_function("() => { const c = [...document.querySelectorAll('#pg-out .cell-body')].pop(); return c && !/Running|Waiting|Loading/.test(c.textContent); }", timeout=120000)
    check("playground renders seaborn figure", page.locator("#pg-out .fig img").count() >= 1)
    set_code(page, "x_saved + 1", "#pg-editor")
    page.click("#pg-run")
    page.wait_for_function("() => { const c = [...document.querySelectorAll('#pg-out .cell-body')].pop(); return c && !/Running|Waiting|Loading/.test(c.textContent); }", timeout=60000)
    check("playground namespace persists", "42" in page.inner_text("#pg-out .cell:last-child"))
    page.screenshot(path=os.path.join(SHOTS, "06-playground.png"))

    # dark mode screenshot
    page.emulate_media(color_scheme="dark")
    page.evaluate("() => { location.hash = '#problems/pd-036'; }")
    page.wait_for_timeout(600)
    page.screenshot(path=os.path.join(SHOTS, "07-problem-dark.png"))
    page.set_viewport_size({"width": 400, "height": 860})
    page.evaluate("() => { location.hash = '#cards'; }")
    page.wait_for_timeout(400)
    page.screenshot(path=os.path.join(SHOTS, "08-cards-phone.png"))
    page.evaluate("() => { location.hash = '#problems/np-010'; }")
    page.wait_for_timeout(400)
    page.screenshot(path=os.path.join(SHOTS, "09-problem-phone.png"), full_page=True)

    check("no console errors", not errors, " | ".join(errors[:5]))
    browser.close()

n_fail = sum(1 for _, ok, _ in results if not ok)
print(f"\n{len(results) - n_fail}/{len(results)} checks passed ({CHANNEL})")
sys.exit(1 if n_fail else 0)
