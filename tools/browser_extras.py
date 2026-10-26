"""Browser smoke test for index.html opened from file://.

Usage: pip install playwright; python tools/browser_extras.py <project dir> [msedge|chrome]
(uses the installed Edge/Chrome; no browser download needed)
"""

import json, os, sys, time
from playwright.sync_api import sync_playwright

ROOT = sys.argv[1]
CHANNEL = sys.argv[2] if len(sys.argv) > 2 else "msedge"
SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".build", "shots")
URL = ROOT if ROOT.startswith("http") else "file:///" + os.path.join(ROOT, "index.html").replace("\\", "/")
results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail else ""), flush=True)


def go(page, h):
    page.evaluate("(h) => { location.hash = h; }", h)
    page.wait_for_timeout(350)


def store(page):
    return page.evaluate("() => JSON.parse(localStorage.getItem('dsdrill.v1'))")


def set_code(page, code, host="#editor-host"):
    page.evaluate("([h, c]) => document.querySelector(h + ' .CodeMirror').CodeMirror.setValue(c)", [host, code])


def wait_verdict(page, timeout=90000):
    page.wait_for_function("""() => { const v = document.querySelector('#results .verdict');
        return v && !/Running|Waiting|Loading/.test(v.textContent); }""", timeout=timeout)
    return page.inner_text("#results .verdict")


with sync_playwright() as p:
    browser = p.chromium.launch(channel=CHANNEL)
    ctx = browser.new_context(viewport={"width": 1400, "height": 900}, accept_downloads=True)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto(URL)
    page.wait_for_selector("#plist li[data-id]")
    n_list = page.locator("#plist li[data-id]").count()
    check("all problems listed", n_list >= 200, f"{n_list} rows")

    # --- Today queue: 5 new problems by default, start opens the first in queue mode
    go(page, "#today")
    t = page.inner_text("#view-today")
    check("today shows one new problem per section", "New problems (8)" in t, t[:120].replace("\n", " "))
    page.click("#t-start")
    page.wait_for_function("() => document.querySelector('#problem') && document.querySelector('#problem').innerText.includes('Today ·')")
    check("start opens a problem in the Today queue", "Today · 1 of" in page.inner_text("#problem"))
    page.wait_for_function("() => window.__leetstats.Py.st.ready", timeout=120000)
    pid = page.evaluate("() => document.querySelector('.p-sub .pid').textContent")
    sol = page.evaluate("(id) => window.__leetstats.BY_ID[id].solution", pid)
    set_code(page, sol)
    page.click("#submit-btn")
    v = wait_verdict(page)
    check("first queue item solved", "Accepted" in v, f"{pid}: {v[:40]}")
    page.keyboard.press("n")
    page.wait_for_timeout(500)
    pid2 = page.evaluate("() => document.querySelector('.p-sub .pid').textContent")
    check("N after accept goes to the next queue item", pid2 != pid and "Today · 2 of" in page.inner_text("#problem"), pid2)
    go(page, "#today")
    check("today progress counted", "1/8 done" in page.inner_text("#view-today"))
    check("streak counted", "1-day streak" in page.inner_text("#view-today"))

    # --- Review: fail a problem -> due; peek another -> due; flag one -> due
    go(page, "#problems/np-001")
    page.wait_for_function("() => document.querySelector('.p-sub .pid').textContent === 'np-001'")
    set_code(page, "def solve(lo, hi, n):\n    return np.arange(lo, hi)\n")
    page.click("#submit-btn")
    wait_verdict(page)
    go(page, "#problems/np-002")
    page.wait_for_function("() => document.querySelector('.p-sub .pid').textContent === 'np-002'")
    page.click("#sol-btn")
    page.wait_for_selector("#cb-ok")
    page.click("#cb-ok")
    page.wait_for_timeout(300)
    check("give up shows the solution", "Reference solution" in page.inner_text("#sol-block") or "reference solution" in page.inner_text("#sol-block").lower())
    page.click("#flag-btn")
    go(page, "#review")
    r = page.inner_text("#view-review")
    check("review lists failed, peeked and flagged", all(w in r for w in ["failed", "flagged"]) and "Strike grid" in r and "Constant-correlation" in r, r[:200].replace("\n", " "))
    page.click("#r-start")
    page.wait_for_timeout(500)
    code = page.evaluate("() => document.querySelector('#editor-host .CodeMirror').CodeMirror.getValue()")
    check("review queue starts from the blank starter", code.strip().endswith("pass"), code[:60])

    # --- Flashcards: rate a predict card
    go(page, "#cards")
    page.click("[data-deck=predict]")
    page.wait_for_timeout(200)
    check("predict card shows code", page.locator("#view-cards pre.code").count() >= 1)
    page.keyboard.press("Space")
    page.wait_for_timeout(150)
    out = page.inner_text("#fc-answer")
    check("predict card answer shows captured output", "Output" in out and len(out) > 8, out[:60].replace("\n", " "))
    page.keyboard.press("3")
    page.wait_for_timeout(800)
    s = store(page)
    check("rating stored with a schedule", any(k.startswith("po-") and v.get("stage") == 1 for k, v in s["cards"].items()))

    # --- Mock: start, finish, rubric, saved
    go(page, "#mock")
    page.click("#mk-start")
    page.wait_for_selector("#mk-timer")
    t1 = page.inner_text("#mk-timer")
    check("mock timer starts at 45:00", t1 in ("45:00", "44:59"), t1)
    check("mock hides the walkthrough", "Reference walkthrough" not in page.inner_text("#view-mock"))
    set_code(page, "churn_raw.shape", "#mk-editor")
    page.click("#mk-run")
    page.wait_for_function("() => { const c = [...document.querySelectorAll('#mk-out .cell-body')].pop(); return c && /\\(/.test(c.textContent) && !/Running|Waiting|Resetting/.test(c.textContent); }", timeout=120000)
    page.click("#mk-finish")
    page.wait_for_selector("[data-rb='0']")
    page.check("[data-rb='0']")
    page.check("[data-rb='2']")
    page.click("#mk-save")
    page.wait_for_timeout(300)
    check("mock reveals the walkthrough after the rubric", "Reference walkthrough" in page.inner_text("#view-mock"))
    s = store(page)
    check("mock attempt saved with score and code", len(s["mock"]) == 1 and s["mock"][0]["score"] == 2 and "churn_raw" in s["mock"][0]["code"])
    page.screenshot(path=os.path.join(SHOTS, "10-mock.png"))

    # --- Stats + copy for Claude (clipboard may be blocked -> modal fallback)
    go(page, "#stats")
    st = page.inner_text("#view-stats")
    check("stats show per-topic table", "By topic" in st and "ACCURACY" in st.upper())
    page.evaluate("() => { navigator.clipboard.writeText = (t) => { window.__copied = t; return Promise.resolve(); }; }")
    page.click("#st-copy")
    page.wait_for_timeout(500)
    if page.locator("#modal:not([hidden]) textarea").count():
        txt = page.input_value("#modal textarea")
        page.keyboard.press("Escape")
    else:
        txt = page.evaluate("() => window.__copied || ''")
    check("copy-stats text has the expected sections", "Weakest topics" in txt and "peeked or failed repeatedly" in txt.lower(), txt[:160].replace("\n", " | "))
    page.screenshot(path=os.path.join(SHOTS, "11-stats.png"))
    page.click("#st-drill")
    page.wait_for_timeout(500)
    check("drill weakest topic opens a drill queue", "Drill:" in page.inner_text("#problem"))

    # --- Export, then import into a fresh context
    page.click("#menu-btn")
    with page.expect_download() as dl:
        page.click("[data-act=export]")
    path = os.path.join(SHOTS, "export.json")
    dl.value.save_as(path)
    exported = json.load(open(path, encoding="utf-8"))
    check("export contains progress", len(exported["data"]["problems"]) >= 2 and len(exported["data"]["mock"]) == 1)
    ctx2 = browser.new_context()
    p2 = ctx2.new_page()
    p2.goto(URL + "#stats")
    p2.wait_for_selector("#plist li[data-id]", state="attached")
    p2.set_input_files("#import-file", path)
    p2.wait_for_selector("#cb-ok")
    p2.click("#cb-ok")
    p2.wait_for_load_state("load")
    p2.wait_for_timeout(800)
    s2 = p2.evaluate("() => JSON.parse(localStorage.getItem('dsdrill.v1'))")
    check("import restores progress in a fresh browser", set(s2["problems"]) == set(exported["data"]["problems"]))

    # --- New badge: forget some known ids, reload
    page.evaluate("""() => { const d = window.__leetstats.Store.d;
        d.knownIds = d.knownIds.filter(id => !['st-008', 'qt-012'].includes(id)); window.__leetstats.Store.save(true); }""")
    page.reload()
    page.wait_for_selector("#plist li[data-id]")
    page.evaluate("() => { location.hash = '#problems/np-001'; }")
    page.wait_for_timeout(500)
    badges = page.evaluate("() => [...document.querySelectorAll('#plist li[data-id]')].filter(li => li.querySelector('.new-badge')).map(li => li.dataset.id)")
    check("NEW badge on problems added since the last visit", sorted(badges) == ["qt-012", "st-008"], str(badges))

    # --- Theme toggle cycles system -> light -> dark
    page.click("#theme-btn")
    page.click("#theme-btn")
    check("theme toggle sets dark", page.evaluate("() => document.documentElement.dataset.theme") == "dark")
    page.screenshot(path=os.path.join(SHOTS, "12-dark-bricks.png"))
    go(page, "#bricks")
    check("bricks page lists call shapes for every section", page.locator(".bricks-sec").count() == 8)

    real = [e for e in errors if "favicon" not in e]
    check("no console errors", not real, " | ".join(real[:3]))
    browser.close()

n_fail = sum(1 for _, ok in results if not ok)
print(f"\n{len(results) - n_fail}/{len(results)} extra checks passed ({CHANNEL})")
sys.exit(1 if n_fail else 0)
