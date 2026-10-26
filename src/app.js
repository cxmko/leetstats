/* LeetStats app. Vanilla JS, no build step: build.py inlines this file. */
(() => {
"use strict";

// ===========================================================================
// Utilities
// ===========================================================================
const DATA = JSON.parse(document.getElementById("data").textContent);
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const MIN = 60e3, HOUR = 3600e3, DAY = 86400e3;
const now = () => Date.now();
const pad2 = (n) => String(n).padStart(2, "0");
const dayKey = (t = now()) => { const d = new Date(t); return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`; };
const startOfDay = (t = now()) => { const d = new Date(t); d.setHours(0, 0, 0, 0); return d.getTime(); };
const endOfDay = (t = now()) => startOfDay(t) + DAY - 1;
const fmtClock = (ms) => { const s = Math.floor(ms / 1000); const h = Math.floor(s / 3600); const m = Math.floor((s % 3600) / 60); return (h ? h + ":" + pad2(m) : m) + ":" + pad2(s % 60); };
const fmtDur = (ms) => ms == null ? "–" : ms < 60e3 ? Math.round(ms / 1000) + "s" : ms < 3600e3 ? Math.round(ms / 60e3) + " min" : (ms / 3600e3).toFixed(1) + " h";
const fmtIn = (ms) => ms <= 0 ? "now" : ms < HOUR ? Math.round(ms / MIN) + " min" : ms < DAY ? Math.round(ms / HOUR) + " h" : Math.round(ms / DAY) + " d";
const median = (xs) => { if (!xs.length) return null; const s = [...xs].sort((a, b) => a - b); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
const pct = (x) => x == null || isNaN(x) ? "–" : Math.round(x * 100) + "%";
const isMac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);
const MOD = isMac ? "Cmd" : "Ctrl";

function toast(msg, ms = 2200) {
  const t = $("#toast"); t.textContent = msg; t.hidden = false;
  clearTimeout(toast._t); toast._t = setTimeout(() => (t.hidden = true), ms);
}

function modal(html, { onOpen } = {}) {
  const back = $("#modal"); $("#modal-body").innerHTML = html; back.hidden = false;
  const close = () => { back.hidden = true; $("#modal-body").innerHTML = ""; };
  back.onclick = (e) => { if (e.target === back) close(); };
  $$("[data-close]", back).forEach((b) => (b.onclick = close));
  if (onOpen) onOpen(close);
  return close;
}

function confirmBox(title, body, okLabel = "OK") {
  return new Promise((resolve) => {
    modal(`<h2>${esc(title)}</h2><p class="muted">${body}</p><div class="acts"><button class="btn" data-close>Cancel</button><button class="btn primary" id="cb-ok">${esc(okLabel)}</button></div>`, {
      onOpen: (close) => {
        $("#cb-ok").onclick = () => { close(); resolve(true); };
        $$("[data-close]").forEach((b) => b.addEventListener("click", () => resolve(false)));
        $("#cb-ok").focus();
      },
    });
  });
}

function highlight(root = document) {
  if (!window.CodeMirror || !CodeMirror.runMode) return;
  $$("pre.code:not([data-hl])", root).forEach((pre) => {
    const code = pre.querySelector("code") || pre;
    const text = code.textContent;
    code.innerHTML = "";
    CodeMirror.runMode(text, "python", code);
    pre.setAttribute("data-hl", "1");
    pre.classList.add("cm-s-default");
  });
}
const codeBlock = (src) => `<pre class="code"><code>${esc(src)}</code></pre>`;

// ===========================================================================
// Data indexes
// ===========================================================================
const PROBS = DATA.problems;                       // already in learning-path order
const BY_ID = Object.fromEntries(PROBS.map((p) => [p.id, p]));
const PATH = PROBS.map((p) => p.id);
const SECTIONS = DATA.sections.filter((s) => PROBS.some((p) => p.section === s.key));
const SEC_TITLE = Object.fromEntries(DATA.sections.map((s) => [s.key, s.title]));
const CHAINS = (DATA.sections.find((s) => s.key === "chains") || {}).chains || {};
const ALL_CARDS = [
  ...PROBS.map((p) => ({ id: "rc:" + p.id, type: "recall", section: p.section, front: p.recall, back: p.hint2, pid: p.id })),
  ...DATA.cards.recall_extra.map((c) => ({ ...c, type: "recall", extra: true })),
  ...DATA.cards.predict.map((c) => ({ ...c, type: "predict" })),
];
const CARD_BY_ID = Object.fromEntries(ALL_CARDS.map((c) => [c.id, c]));
const RUBRIC = [
  "Inspected dtypes, shapes and missing values before modelling",
  "Set a baseline (dummy model or simple heuristic) to beat",
  "Avoided leakage: preprocessing fitted inside the CV / on train only, no future info",
  "Cross-validated properly (stratified / grouped / time-ordered as the data requires)",
  "Chose and justified the metric for the business question",
  "Interpreted the results (drivers, coefficients or importances, error analysis)",
  "Made at least one useful plot",
];

// ===========================================================================
// Store (localStorage; every access wrapped in try/catch)
// ===========================================================================
const STORE_KEY = "dsdrill.v1";   // kept from the old name "DS Drill" so saved progress carries over
const Store = (() => {
  let mem = null, timer = null, ok = true;
  const defaults = () => ({
    v: 1, problems: {}, drafts: {}, reviewDrafts: {}, cards: {}, days: {}, mock: [], pgDrafts: {},
    settings: { theme: "system", newPerSection: 1, cardsNewPerDay: 20, deck: "all" },
    filters: { section: "", topics: [], diff: "", status: "" },
    knownIds: null, newIds: [], today: null, lastVisit: null, lastProblem: null, created: now(),
  });
  function load() {
    let raw = null;
    try { raw = localStorage.getItem(STORE_KEY); } catch (e) { ok = false; }
    try { mem = raw ? merge(defaults(), JSON.parse(raw)) : defaults(); } catch (e) { mem = defaults(); }
  }
  function merge(d, x) {
    for (const k of Object.keys(x || {})) {
      if (d[k] && typeof d[k] === "object" && !Array.isArray(d[k]) && x[k] && typeof x[k] === "object" && !Array.isArray(x[k])) d[k] = { ...d[k], ...x[k] };
      else d[k] = x[k];
    }
    return d;
  }
  function flush() {
    try { localStorage.setItem(STORE_KEY, JSON.stringify(mem)); ok = true; }
    catch (e) { if (ok) toast("Could not save progress (storage blocked or full). Export to keep it."); ok = false; }
  }
  function save(immediate) { clearTimeout(timer); if (immediate) flush(); else timer = setTimeout(flush, 250); }
  function replace(obj) { mem = merge(defaults(), obj); flush(); }
  return { load, save, replace, get d() { return mem; }, get ok() { return ok; }, defaults };
})();
const S = () => Store.d;
window.addEventListener("beforeunload", () => Store.save(true));

// ===========================================================================
// Progress + spaced repetition (shared by problems and flashcards)
// ===========================================================================
const LADDER = [1, 3, 7, 21, 60, 150];          // days for stage 1..6
function schedule(srs, rating, t = now(), againMs = 10 * MIN) {
  const prev = srs || { stage: 0, reps: 0, lapses: 0 };
  if (rating === "again") return { stage: 0, due: t + againMs, reps: (prev.reps || 0) + 1, lapses: (prev.lapses || 0) + 1, last: t };
  let s = prev.stage || 0;
  if (rating === "hard") s = Math.max(1, s);
  else if (rating === "good") s = s + 1;
  else if (rating === "easy") s = s + 2;
  s = Math.min(s, LADDER.length);
  return { stage: s, due: t + LADDER[s - 1] * DAY, reps: (prev.reps || 0) + 1, lapses: prev.lapses || 0, last: t };
}
function previewInterval(srs, rating, againMs) { const n = schedule(srs, rating, 0, againMs); return fmtIn(n.due); }

const EMPTY = Object.freeze({});
const getP = (id) => S().problems[id] || EMPTY;
function P(id) {
  const all = S().problems;
  if (!all[id]) all[id] = { attempts: 0, passes: 0, fails: 0, runs: 0, peeks: 0, times: [], cur: freshAttempt() };
  if (!all[id].cur) all[id].cur = freshAttempt();
  return all[id];
}
function freshAttempt() { return { fails: 0, hints: 0, peeked: false, unlocked: false, timeMs: 0, submits: 0 }; }
function status(id) { const p = getP(id); return p.solvedAt ? "solved" : (p.attempts || p.runs || p.peeks) ? "attempted" : "new"; }
function isDue(id, t = now()) { const p = getP(id); return !!p.flagged || !!(p.srs && p.srs.due <= t); }
function dueReason(id) {
  const p = getP(id);
  if (p.flagged) return "flagged";
  if (p.cur && p.cur.peeked) return "peeked";
  if (p.last && p.last.ok === false) return "failed";
  return "scheduled";
}
function day(key = dayKey()) { const d = S().days; return d[key] || (d[key] = { solved: 0, reviews: 0, cards: 0, submits: 0, newCards: 0 }); }

function recordRun(id) { const p = P(id); p.runs++; p.lastSeen = now(); Store.save(); }
function recordHint(id, level) { const p = P(id); p.cur.hints = Math.max(p.cur.hints, level); p.hintsUsed = (p.hintsUsed || 0) + 1; Store.save(); }
function recordPeek(id) {
  const p = P(id);
  if (!p.cur.peeked) { p.peeks++; p.cur.peeked = true; }
  p.peeked = true;
  p.srs = { ...(p.srs || {}), stage: 0, due: now(), last: now() };
  Store.save();
}
function recordSubmit(id, passed, review) {
  const p = P(id), t = now(), d = day();
  p.attempts++; p.cur.submits++; d.submits++;
  if (passed) {
    p.passes++;
    const firstEver = !p.solvedAt;
    const clean = !p.cur.hints && !p.cur.peeked && !p.cur.fails;
    if (firstEver) { p.firstTry = p.attempts === 1; p.firstSolvedAt = t; }
    p.solvedAt = t; p.lastPassAt = t;
    p.times.push(Math.round(p.cur.timeMs)); if (p.times.length > 20) p.times.shift();
    const base = p.cur.peeked ? { stage: 0 } : p.srs;
    p.srs = schedule(base, p.cur.peeked ? "hard" : clean ? "good" : "hard", t);
    if (review || !firstEver) d.reviews++; else d.solved++;
    p.last = { ok: true, t, clean, timeMs: p.cur.timeMs };
    p.cur = freshAttempt();
    delete S().reviewDrafts[id];
  } else {
    p.fails++; p.cur.fails++; p.cur.unlocked = true; p.lastFailAt = t;
    p.srs = { ...(p.srs || {}), stage: 0, due: t, last: t };
    p.last = { ok: false, t };
  }
  Store.save();
}

// ===========================================================================
// Python runtime manager (Web Worker from an inline Blob)
// ===========================================================================
const Py = (() => {
  const st = { worker: null, ready: false, booting: false, text: "Python idle", pkgs: {}, bgDone: false, error: null, current: null, seq: 0, waiters: [] };
  const BG = ["matplotlib", "seaborn", "scipy", "scikit-learn", "statsmodels"];
  const listeners = new Set();
  const emit = () => listeners.forEach((f) => f(st));

  function start() {
    if (st.worker) return;
    st.booting = true; st.ready = false; st.error = null; st.pkgs = {}; st.bgDone = false; st.text = "Starting Python…"; emit();
    const src = $("#worker-src").textContent;
    const url = URL.createObjectURL(new Blob([src], { type: "text/javascript" }));
    const w = new Worker(url);
    st.worker = w;
    w.onmessage = (e) => onMsg(e.data);
    w.onerror = (e) => { st.error = e.message || "worker error"; st.text = "Python failed to start"; emit(); };
    w.postMessage({
      type: "init", indexURL: DATA.pyodide.indexURL, seaborn: DATA.pyodide.seaborn,
      files: DATA.runtime, solutions: Object.fromEntries(PROBS.map((p) => [p.id, p.solution])),
    });
  }
  function onMsg(m) {
    if (m.type === "status") { st.text = m.text; }
    else if (m.type === "ready") { st.ready = true; st.booting = false; st.text = "Python ready"; st.waiters.splice(0).forEach((f) => f()); }
    else if (m.type === "fatal") { st.error = m.error; st.booting = false; st.text = "Python failed to load"; st.waiters.splice(0).forEach((f) => f()); }
    else if (m.type === "pkg") { st.pkgs[m.name] = m.state === "error" ? "error: " + m.error : m.state; }
    else if (m.type === "bg-done") { st.bgDone = true; }
    else if (m.type === "waiting") { if (st.current && st.current.id === m.id && st.current.onWaiting) st.current.onWaiting(m.pkg); }
    else if (m.type === "started") {
      const c = st.current;
      if (c && c.id === m.id) { c.started = now(); if (c.onStarted) c.onStarted(); c.timer = setTimeout(() => stop("timeout"), c.timeout); }
    } else if (m.type === "result") {
      const c = st.current;
      if (c && c.id === m.id) { clearTimeout(c.timer); st.current = null; c.resolve(m.result); }
    }
    emit();
  }
  function whenReady() {
    start();
    if (st.ready || st.error) return Promise.resolve();
    return new Promise((r) => st.waiters.push(r));
  }
  let tail = Promise.resolve();
  function run(job, opts) {          // jobs run one at a time, in order
    const p = tail.then(() => runNow(job, opts));
    tail = p.catch(() => {});
    return p;
  }
  async function runNow(job, { needs = [], timeout = 10000, onWaiting, onStarted } = {}) {
    await whenReady();
    if (st.error) return { internal_error: "Python could not be loaded: " + st.error + "\nCheck your connection (Pyodide loads from cdn.jsdelivr.net) and reload." };
    return new Promise((resolve) => {
      const id = ++st.seq;
      st.current = { id, resolve, timeout, onWaiting, onStarted, timer: null };
      st.worker.postMessage({ type: "job", id, job, needs });
      emit();
    });
  }
  function stop(reason = "stopped") {
    const c = st.current;
    if (st.worker) st.worker.terminate();
    st.worker = null; st.ready = false; st.current = null;
    if (c) { clearTimeout(c.timer); c.resolve({ stopped: reason, elapsed: c.started ? now() - c.started : 0 }); }
    start();
  }
  function bgProgress() { const n = BG.filter((k) => st.pkgs[k] === "loaded").length; return { n, total: BG.length }; }
  return { start, run, stop, whenReady, st, on: (f) => listeners.add(f), bgProgress, BG };
})();

function renderPill() {
  const st = Py.st, pill = $("#py-pill");
  pill.classList.remove("loading", "ready", "busy", "error", "bg");
  const { n, total } = Py.bgProgress();
  let text = st.text;
  if (st.error) pill.classList.add("error");
  else if (st.current) { pill.classList.add("busy"); text = "Running…"; }
  else if (st.ready) {
    pill.classList.add("ready");
    if (!st.bgDone && n < total) { pill.classList.add("bg"); const loadingPkg = Py.BG.find((k) => st.pkgs[k] === "loading"); text = loadingPkg ? `Ready · loading ${loadingPkg}` : "Ready · loading extras"; }
    else text = "Python ready";
  } else if (st.booting) pill.classList.add("loading");
  $("#py-text").textContent = text;
  $("#py-bar").style.width = Math.round((n / total) * 100) + "%";
}
Py.on(renderPill);

// ===========================================================================
// Editors (CodeMirror 5; textarea fallback when the CDN is unreachable)
// ===========================================================================
function makeEditor(host, keys) {
  if (window.CodeMirror) {
    const cm = CodeMirror(host, {
      value: "", mode: "python", lineNumbers: true, indentUnit: 4, tabSize: 4, indentWithTabs: false,
      matchBrackets: true, smartIndent: true, electricChars: true, autofocus: false, spellcheck: false,
      autocorrect: false, autocapitalize: false, inputStyle: "textarea", viewportMargin: 50,
      extraKeys: {
        Tab: (c) => { if (c.somethingSelected()) c.indentSelection("add"); else c.replaceSelection(" ".repeat(4 - (c.getCursor().ch % 4)), "end"); },
        "Shift-Tab": (c) => c.indentSelection("subtract"),
        Backspace: (c) => {
          if (c.somethingSelected()) return CodeMirror.Pass;
          const cur = c.getCursor(), line = c.getLine(cur.line), before = line.slice(0, cur.ch);
          if (cur.ch > 0 && /^ +$/.test(before)) { const n = ((cur.ch - 1) % 4) + 1; c.replaceRange("", { line: cur.line, ch: cur.ch - n }, cur); return; }
          return CodeMirror.Pass;
        },
        "Ctrl-/": "toggleComment", "Cmd-/": "toggleComment",
        ...keys,
      },
    });
    return {
      cm, getValue: () => cm.getValue(), setValue: (v) => { cm.setValue(v); cm.clearHistory(); },
      onChange: (f) => cm.on("changes", f), focus: () => cm.focus(), refresh: () => cm.refresh(),
      blur: () => cm.getInputField().blur(), getSelection: () => cm.getSelection(),
      setCursorEnd: () => { const last = cm.lastLine(); cm.setCursor({ line: last, ch: cm.getLine(last).length }); },
    };
  }
  const ta = document.createElement("textarea");
  ta.className = "fallback"; ta.spellcheck = false; ta.setAttribute("autocapitalize", "off"); ta.setAttribute("autocomplete", "off");
  host.appendChild(ta);
  ta.addEventListener("keydown", (e) => {
    if (e.key === "Tab") {
      e.preventDefault();
      const s = ta.selectionStart; ta.setRangeText("    ", s, ta.selectionEnd, "end");
      ta.dispatchEvent(new Event("input"));
    } else if (e.key === "Enter" && !e.ctrlKey && !e.metaKey && !e.shiftKey) {
      e.preventDefault();
      const s = ta.selectionStart, line = ta.value.slice(0, s).split("\n").pop();
      let ind = line.match(/^ */)[0]; if (/:\s*$/.test(line)) ind += "    ";
      ta.setRangeText("\n" + ind, s, ta.selectionEnd, "end"); ta.dispatchEvent(new Event("input"));
    }
  });
  return {
    cm: null, getValue: () => ta.value, setValue: (v) => (ta.value = v), onChange: (f) => ta.addEventListener("input", f),
    focus: () => ta.focus(), refresh: () => {}, blur: () => ta.blur(),
    getSelection: () => ta.value.slice(ta.selectionStart, ta.selectionEnd),
    setCursorEnd: () => { ta.selectionStart = ta.selectionEnd = ta.value.length; },
  };
}

// ===========================================================================
// Rendering values from the harness
// ===========================================================================
function renderPreview(pv, label) {
  if (!pv) return `<div class="muted small">(nothing)</div>`;
  const lab = label ? `<div class="io-label">${esc(label)}</div>` : "";
  switch (pv.kind) {
    case "df": {
      const dt = pv.dtypes.map(([c, t]) => `<tr><td>${esc(c)}</td><td>${esc(t)}</td></tr>`).join("");
      return `${lab}<div class="io-meta">DataFrame · ${pv.shape[0]} rows × ${pv.shape[1]} columns · ${esc(pv.index)}</div>
        <details class="dtypes"><summary>dtypes</summary><table>${dt}</table></details>
        <div class="tbl-wrap">${pv.html}</div>`;
    }
    case "series":
      return `${lab}<div class="io-meta">Series${pv.name != null ? " '" + esc(pv.name) + "'" : ""} · length ${pv.shape[0]} · dtype ${esc(pv.dtype)} · ${esc(pv.index)}</div><div class="tbl-wrap">${pv.html}</div>`;
    case "array":
      return `${lab}<div class="io-meta">ndarray · shape (${pv.shape.join(", ")}${pv.shape.length === 1 ? "," : ""}) · dtype ${esc(pv.dtype)}</div><pre class="out">${esc(pv.text)}</pre>`;
    case "figure":
      return `${lab}<div class="io-meta">${esc(pv.type || "Figure")}</div>${pv.png ? `<div class="fig"><img alt="figure" src="data:image/png;base64,${pv.png}"></div>` : ""}`;
    case "seq":
      return `${lab}<div class="io-meta">${esc(pv.type)} of ${pv.items.length}</div>` + pv.items.map((it, i) => renderPreview(it, `[${i}]`)).join("");
    case "dict":
      return `${lab}<div class="io-meta">dict</div>` + pv.items.map(([k, v]) => renderPreview(v, k)).join("");
    default:
      return `${lab}<div class="io-meta">${esc(pv.type || "")}</div><pre class="out">${esc(pv.text)}</pre>`;
  }
}

// ===========================================================================
// Problems view
// ===========================================================================
const view = {
  id: null, review: false, queue: null, busy: false, accepted: false, solShown: false,
  editor: null, tick: null, lastTick: 0, runStarted: 0,
};

function initProblemsView() {
  // filters
  const fs = $("#f-section");
  SECTIONS.forEach((s) => fs.insertAdjacentHTML("beforeend", `<option value="${s.key}">${esc(s.title)}</option>`));
  const f = S().filters;
  fs.value = f.section || ""; $("#f-diff").value = f.diff || ""; $("#f-status").value = f.status || "";
  fs.onchange = () => { f.section = fs.value; f.topics = []; buildTopicMenu(); Store.save(); renderList(); };
  $("#f-diff").onchange = (e) => { f.diff = e.target.value; Store.save(); renderList(); };
  $("#f-status").onchange = (e) => { f.status = e.target.value; Store.save(); renderList(); };
  $("#search").oninput = () => renderList();
  buildTopicMenu();
  const mb = $("#f-topic .multi-btn"), pop = $("#f-topic .multi-pop");
  mb.onclick = (e) => { e.stopPropagation(); pop.hidden = !pop.hidden; };
  document.addEventListener("click", (e) => { if (!e.target.closest("#f-topic")) pop.hidden = true; });

  view.editor = makeEditor($("#editor-host"), {
    "Ctrl-Enter": () => doRun("run"), "Cmd-Enter": () => doRun("run"),
    "Shift-Ctrl-Enter": () => doRun("submit"), "Shift-Cmd-Enter": () => doRun("submit"),
    "Alt-N": () => navigate("next"),
  });
  view.editor.onChange(() => saveDraft());
  $("#run-btn").onclick = () => doRun("run");
  $("#submit-btn").onclick = () => doRun("submit");
  $("#stop-btn").onclick = () => Py.stop("stopped");
  $("#hint1-btn").onclick = () => showHint(1);
  $("#hint2-btn").onclick = () => showHint(2);
  $("#sol-btn").onclick = () => showSolution();
  $("#reset-btn").onclick = async () => {
    if (await confirmBox("Reset the editor?", "Your current code for this problem will be replaced by the starter.", "Reset")) {
      view.editor.setValue(BY_ID[view.id].starter); saveDraft(); view.editor.focus();
    }
  };
  $("#next-btn").onclick = () => navigate("next");
  $("#next-more").onclick = (e) => { e.stopPropagation(); $("#next-menu").hidden = !$("#next-menu").hidden; };
  $$("#next-menu [data-nav]").forEach((b) => (b.onclick = () => { $("#next-menu").hidden = true; navigate(b.dataset.nav); }));
  document.addEventListener("click", (e) => { if (!e.target.closest(".split")) $("#next-menu").hidden = true; });
  $("#plist").onclick = (e) => {
    const li = e.target.closest("li[data-id]"); if (!li) return;
    document.body.classList.remove("drawer-open");
    openProblem(li.dataset.id, { queue: null });
  };
  $("#drawer-btn").onclick = () => document.body.classList.toggle("drawer-open");
  // stopwatch: accumulate active time while the problem is visible
  setInterval(() => {
    const t = now(), dt = t - (view.lastTick || t); view.lastTick = t;
    if (!view.id || currentView() !== "problems" || document.hidden || view.accepted) return;
    const p = P(view.id); p.cur.timeMs += Math.min(dt, 5000);
    const w = $("#watch"); if (w) w.textContent = fmtClock(p.cur.timeMs);
    if (Math.random() < 0.1) Store.save();
  }, 1000);
}

function buildTopicMenu() {
  const f = S().filters, pop = $("#f-topic .multi-pop");
  const secs = f.section ? SECTIONS.filter((s) => s.key === f.section) : SECTIONS;
  let html = `<div class="acts"><button type="button" data-all>Clear</button><span class="muted small">pick one or more</span></div>`;
  for (const s of secs) {
    const tags = [...new Set(PROBS.filter((p) => p.section === s.key).flatMap((p) => p.tags))];
    const ordered = (DATA.tags[s.key] || []).filter((t) => tags.includes(t));
    html += `<div class="grp">${esc(s.title)}</div>` + ordered.map((t) => {
      const v = s.key + "|" + t, n = PROBS.filter((p) => p.section === s.key && p.tags.includes(t)).length;
      return `<label><input type="checkbox" value="${esc(v)}" ${f.topics.includes(v) ? "checked" : ""}> ${esc(t)} <span class="muted small">${n}</span></label>`;
    }).join("");
  }
  pop.innerHTML = html;
  pop.onchange = () => { f.topics = $$("input:checked", pop).map((i) => i.value); Store.save(); topicLabel(); renderList(); };
  $("[data-all]", pop).onclick = () => { f.topics = []; $$("input", pop).forEach((i) => (i.checked = false)); Store.save(); topicLabel(); renderList(); };
  topicLabel();
}
function topicLabel() {
  const t = S().filters.topics;
  $("#f-topic .multi-btn").textContent = !t.length ? "All topics" : t.length === 1 ? t[0].split("|")[1] : `${t.length} topics`;
}

function filteredProblems() {
  const f = S().filters, q = $("#search").value.trim().toLowerCase(), t = now();
  return PROBS.filter((p) => {
    if (f.section && p.section !== f.section) return false;
    if (f.topics.length && !p.tags.some((tag) => f.topics.includes(p.section + "|" + tag))) return false;
    if (f.diff && p.difficulty !== f.diff) return false;
    if (f.status) {
      const s = status(p.id);
      if (f.status === "due" ? !isDue(p.id, t) : f.status === "flagged" ? !getP(p.id).flagged : s !== f.status) return false;
    }
    if (q && !(p.title + " " + p.id + " " + p.tags.join(" ") + " " + SEC_TITLE[p.section]).toLowerCase().includes(q)) return false;
    return true;
  });
}

function statusIcon(id) {
  const s = status(id), t = now();
  if (isDue(id, t)) return `<span class="st s-due" title="Due for review">↻</span>`;
  if (s === "solved") return `<span class="st s-solved" title="Solved">✓</span>`;
  if (s === "attempted") return `<span class="st s-attempted" title="Attempted">◐</span>`;
  return `<span class="st s-new" title="Not started">○</span>`;
}

function renderList() {
  const list = filteredProblems(), newIds = new Set(S().newIds);
  let html = "", lastSec = null;
  for (const p of list) {
    if (p.section !== lastSec) { html += `<li class="sec-head">${esc(SEC_TITLE[p.section])}</li>`; lastSec = p.section; }
    const flag = getP(p.id).flagged ? `<span title="Flagged" style="color:var(--review)">⚑</span>` : "";
    html += `<li data-id="${p.id}" class="${p.id === view.id ? "active" : ""}">
      <span class="num">${p.num}</span><span class="ttl">${esc(p.title)}</span>${statusIcon(p.id)}
      <span class="meta"><span class="diff ${p.difficulty}">${p.difficulty}</span>${p.tags.map((t) => `<span class="tag">${esc(t)}</span>`).join("")}${flag}${newIds.has(p.id) ? `<span class="new-badge">NEW</span>` : ""}</span></li>`;
  }
  $("#plist").innerHTML = html || `<li class="sec-head">No problems match.</li>`;
  const solved = PROBS.filter((p) => status(p.id) === "solved").length;
  $("#side-count").textContent = `${list.length} shown · ${solved}/${PROBS.length} solved`;
  const act = $("#plist li.active"); if (act) act.scrollIntoView({ block: "nearest" });
}

function problemPayload(p) {
  return { id: p.id, setup: p.setup, tests: p.tests, solution: p.solution, compare: p.compare, plot: p.plot,
    mutation_check: p.mutation_check, expected_plots: p.expected_plots };
}

function openProblem(id, { review = false, queue } = {}) {
  if (!BY_ID[id]) id = PATH[0];
  saveDraft();
  if (queue !== undefined) view.queue = queue;
  view.id = id; view.review = review; view.accepted = false; view.solShown = false;
  S().lastProblem = id;
  const nIdx = S().newIds.indexOf(id); if (nIdx >= 0) S().newIds.splice(nIdx, 1);
  Store.save();
  if (view.queue && !view.queue.ids.includes(id)) view.queue = null;
  if (view.hintLevel) delete view.hintLevel[id];
  const p = BY_ID[id];
  P(id);
  const code = review ? (S().reviewDrafts[id] ?? p.starter) : (S().drafts[id] ?? p.starter);
  view.editor.setValue(code);
  if (location.hash !== "#problems/" + id + (review ? "/review" : "")) history.replaceState(null, "", "#problems/" + id + (review ? "/review" : ""));
  showView("problems");
  renderProblem(); renderList();
  $("#results").innerHTML = `<div class="results-empty">Run (<kbd>${MOD}</kbd>+<kbd>Enter</kbd>) tries your code on the example. Submit (<kbd>${MOD}</kbd>+<kbd>Shift</kbd>+<kbd>Enter</kbd>) runs the hidden tests.${review ? "<br><br><b>Review:</b> the editor starts from the blank starter. Rebuild it from memory." : ""}</div>`;
  updateButtons();
  setTimeout(() => { view.editor.refresh(); view.editor.focus(); view.editor.setCursorEnd(); }, 0);
  if (p.needs.length) Py.start();
}

function saveDraft() {
  if (!view.id || !view.editor) return;
  const code = view.editor.getValue(), p = BY_ID[view.id];
  const store = view.review ? S().reviewDrafts : S().drafts;
  if (code === p.starter) delete store[view.id]; else store[view.id] = code;
  Store.save();
}

function renderProblem() {
  const p = BY_ID[view.id], pr = getP(p.id);
  const chain = p.chain ? `<span class="chip chain" title="${esc(CHAINS[p.chain] || "")}">chain: ${esc(p.chain)} · step ${p.step}</span>` : "";
  const rev = view.review ? `<span class="chip review">Review</span>` : "";
  const solved = pr.solvedAt ? `<span class="chip solved">✓ solved</span>` : "";
  const q = view.queue ? (() => { const i = view.queue.ids.indexOf(p.id); return `<div class="okmsg" style="background:var(--accent-weak);color:var(--accent)">${esc(view.queue.name)} · ${i + 1} of ${view.queue.ids.length} <a href="#" id="q-exit" style="float:right">leave queue</a></div>`; })() : "";
  const ex = p.example || {};
  const inputs = Object.entries(ex.inputs || {}).map(([k, v]) => renderPreview(v, k)).join("");
  let expected = "";
  if (p.target_image) expected = `<div class="target"><img alt="target figure" src="data:image/png;base64,${p.target_image}"></div><div class="muted small">Target figure (tests check structure, not colours or style).</div>`;
  else expected = renderPreview(ex.expected);
  $("#problem").innerHTML = `${q}
    <div class="p-head"><h1>${p.num}. ${esc(p.title)}</h1><span class="watch" id="watch" title="Time on this attempt">${fmtClock((pr.cur && pr.cur.timeMs) || 0)}</span></div>
    <div class="p-sub"><span class="diff ${p.difficulty}">${p.difficulty}</span><span>·</span><span class="pid">${p.id}</span><span>·</span><span>${esc(SEC_TITLE[p.section])}</span>
      ${p.tags.map((t) => `<span class="tag">${esc(t)}</span>`).join("")} ${chain} ${rev} ${solved}
      <span class="grow"></span><button class="flag-btn ${pr.flagged ? "on" : ""}" id="flag-btn" title="Flag for review">⚑ ${pr.flagged ? "Flagged" : "Flag"}</button></div>
    <div class="statement">${p.statement}</div>
    <div class="sig">${codeBlock(p.signature)}</div>
    <div class="block"><h3>Example</h3>${inputs}<div class="io-label" style="margin-top:14px">Expected output</div>${expected}</div>
    <div class="block" id="hints"></div>
    <div class="block" id="sol-block"></div>`;
  $("#flag-btn").onclick = () => {
    const x = P(p.id); x.flagged = !x.flagged; Store.save(); renderProblem(); renderList(); updateBadges();
  };
  const qe = $("#q-exit"); if (qe) qe.onclick = (e) => { e.preventDefault(); view.queue = null; renderProblem(); };
  renderHints(); renderSolutionBlock(); highlight($("#problem"));
}

function renderHints() {
  const p = BY_ID[view.id], lvl = view.hintLevel?.[view.id] ?? (getP(p.id).cur?.hints || 0);
  let html = "";
  if (lvl >= 1) html += `<div class="hint"><div class="h-title">Hint 1</div>${p.hint1}<div class="docs">${p.docs.map((u) => `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(docLabel(u))}</a>`).join("")}</div></div>`;
  if (lvl >= 2) html += `<div class="hint"><div class="h-title">Hint 2 · call shape</div>${codeBlock(p.hint2)}</div>`;
  $("#hints").innerHTML = html ? `<h3>Hints</h3>${html}` : "";
  highlight($("#hints"));
  $("#hint1-btn").classList.toggle("on", lvl >= 1); $("#hint2-btn").classList.toggle("on", lvl >= 2);
}
function docLabel(u) {
  const m = u.match(/\/([^/]+?)(?:\.html)?(?:#(.*))?$/);
  let s = m ? (m[2] || m[1]) : u;
  s = s.replace(/^(pandas|numpy|sklearn|scipy|matplotlib|seaborn|statsmodels|lightgbm)\./, "$1.");
  return s.length > 60 ? s.slice(0, 57) + "…" : s;
}

function renderSolutionBlock() {
  const p = BY_ID[view.id], pr = getP(p.id), el = $("#sol-block");
  if (view.solShown || view.accepted) {
    el.innerHTML = `<h3>Reference solution</h3><div class="solution-box">${codeBlock(p.solution.trimEnd())}<div class="note">${p.explanation}</div>
      <div class="docs">${p.docs.map((u) => `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(docLabel(u))}</a>`).join("")}</div></div>`;
    highlight(el);
  } else {
    const unlocked = pr.cur && pr.cur.unlocked;
    el.innerHTML = `<div class="solution-box locked">${unlocked
      ? `Solution unlocked by a failed submit. <a href="#" id="sol-open">View it</a> (puts this problem into review).`
      : `🔒 The solution unlocks after one failed submit. <a href="#" id="sol-open">Give up and show it</a> (puts this problem into review).`}</div>`;
    $("#sol-open").onclick = (e) => { e.preventDefault(); showSolution(); };
  }
}

function showHint(level) {
  const pr = getP(view.id);
  const cur = Math.max(view.hintLevel?.[view.id] ?? 0, pr.cur?.hints || 0);
  const lvl = Math.max(cur, level === 2 && cur < 1 ? 2 : level);
  view.hintLevel = view.hintLevel || {}; view.hintLevel[view.id] = lvl;
  if (!view.accepted) recordHint(view.id, lvl);
  renderHints();
  $("#hints").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function showSolution() {
  const pr = getP(view.id);
  if (view.solShown || view.accepted) { $("#sol-block").scrollIntoView({ behavior: "smooth", block: "start" }); return; }
  const unlocked = pr.cur && pr.cur.unlocked;
  if (!unlocked && !(await confirmBox("Give up and see the solution?", "Viewing the solution puts this problem into your review queue (that's the point: you'll redo it from scratch later).", "Show solution"))) return;
  recordPeek(view.id);
  view.solShown = true;
  renderSolutionBlock(); renderList(); updateBadges();
  $("#sol-block").scrollIntoView({ behavior: "smooth", block: "start" });
}

function updateButtons() {
  const b = view.busy;
  $("#run-btn").disabled = b; $("#submit-btn").disabled = b; $("#stop-btn").hidden = !b;
}

async function doRun(kind) {
  if (view.busy || !view.id) return;
  const p = BY_ID[view.id], code = view.editor.getValue();
  saveDraft(); recordRun(p.id);
  view.busy = true; updateButtons();
  const res = $("#results");
  const label = kind === "run" ? "Running on the example" : "Running hidden tests";
  res.innerHTML = `<div class="verdict info"><span id="run-status">${Py.st.ready ? label + "…" : "Waiting for Python to load…"}</span><span class="sub" id="run-clock"></span></div>`;
  const clock = setInterval(() => { const c = $("#run-clock"); if (c && view.runStarted) c.textContent = ((now() - view.runStarted) / 1000).toFixed(1) + " s"; }, 100);
  view.runStarted = 0;
  const r = await Py.run({ kind, code, problem: problemPayload(p) }, {
    needs: p.needs, timeout: 10000,
    onWaiting: (pkg) => { const s = $("#run-status"); if (s) s.textContent = `Loading ${pkg} (first use)…`; },
    onStarted: () => { view.runStarted = now(); const s = $("#run-status"); if (s) s.textContent = label + "…"; },
  });
  clearInterval(clock);
  view.busy = false; updateButtons();
  if (view.id !== p.id) return;           // navigated away meanwhile
  if (r.stopped) {
    const msg = r.stopped === "timeout" ? "Time limit exceeded (10 s)" : "Stopped";
    res.innerHTML = `<div class="verdict bad">${msg}</div><p class="muted">Python was restarted (a fresh interpreter is loading). Look for an infinite loop or a slow Python-level loop.</p>`;
    if (kind === "submit") { recordSubmit(p.id, false, view.review); afterSubmit(false); }
    return;
  }
  if (r.internal_error) { res.innerHTML = `<div class="verdict bad">Internal error</div><pre class="out err">${esc(r.internal_error)}</pre>`; return; }
  if (kind === "run") renderRunResult(r, p);
  else {
    const passed = !!r.passed && !r.compile_error;
    recordSubmit(p.id, passed, view.review);
    renderSubmitResult(r, p, passed);
    afterSubmit(passed);
  }
  // phones: the results sit below the editor, out of view
  if (window.matchMedia("(max-width: 820px)").matches) res.scrollIntoView({ behavior: "smooth", block: "start" });
}

function afterSubmit(passed) {
  renderList(); updateBadges();
  if (passed) {
    view.accepted = true; renderSolutionBlock();
    const sb = $("#sol-block"); if (sb) $("#problem").scrollTo({ top: sb.offsetTop - 12, behavior: "smooth" });
    const w = $("#watch"); if (w) w.textContent = fmtClock(getP(view.id).last?.timeMs || 0);
    view.editor.blur();
  } else { renderSolutionBlock(); }
}

function warningsHtml(ws) { return ws && ws.length ? ws.map((w) => `<div class="warnmsg">⚠ ${esc(w)}</div>`).join("") : ""; }

function renderRunResult(r, p) {
  const res = $("#results");
  if (r.compile_error) { res.innerHTML = `<div class="verdict bad">Error</div><pre class="out err">${esc(r.compile_error)}</pre>`; return; }
  const c = r.cases[0] || {};
  let html = "";
  if (c.error) html += `<div class="verdict bad">Error <span class="sub">on the example</span></div><pre class="out err">${esc(c.error)}</pre>`;
  else if (c.passed) html += `<div class="verdict ok">✓ Matches the expected output <span class="sub">${c.time != null ? (c.time * 1000).toFixed(0) + " ms" : ""} · now Submit to run the hidden tests</span></div>`;
  else html += `<div class="verdict bad">✗ Differs from the expected output</div><div class="diffmsg">${esc(c.diff)}</div>`;
  html += warningsHtml(r.warnings);
  if (r.stdout) html += `<div class="io-label">stdout</div><pre class="out">${esc(r.stdout)}</pre>`;
  if (!c.error) {
    const got = `<div class="panel-box"><div class="lbl">Your return value</div>${renderPreview(r.got)}</div>`;
    const exp = p.target_image ? `<div class="panel-box"><div class="lbl">Target</div><div class="fig"><img src="data:image/png;base64,${p.target_image}" alt="target"></div></div>`
      : `<div class="panel-box"><div class="lbl">Expected</div>${renderPreview(p.example.expected)}</div>`;
    html += c.passed ? got : `<div class="cols2">${got}${exp}</div>`;
  }
  if (r.figures && r.figures.length) html += `<div class="io-label">Open figures (not returned)</div>` + r.figures.map((f) => `<div class="fig"><img src="data:image/png;base64,${f}"></div>`).join("");
  res.innerHTML = html;
}

function renderSubmitResult(r, p, passed) {
  const res = $("#results");
  if (r.compile_error) { res.innerHTML = `<div class="verdict bad">Error</div><pre class="out err">${esc(r.compile_error)}</pre>`; return; }
  const n = r.cases.length, k = r.cases.filter((c) => c.passed).length;
  const chips = r.cases.map((c) => `<span class="${c.passed ? "pass" : "fail"}" title="${c.time != null ? (c.time * 1000).toFixed(0) + " ms" : ""}">${c.passed ? "✓" : "✗"} ${esc(c.name)}</span>`).join("");
  let html;
  if (passed) {
    const pr = getP(p.id), t = pr.last?.timeMs;
    html = `<div class="verdict ok">Accepted <span class="sub">${k}/${n} tests passed${t ? " · " + fmtClock(t) + " on this attempt" : ""}${pr.last?.clean ? " · clean solve" : ""}</span></div>
      <div class="tests">${chips}</div>${warningsHtml(r.warnings)}
      <div class="okmsg">Compare your code with the reference solution below (problem panel), then move on. Next review: ${fmtIn((pr.srs?.due || now()) - now())}.</div>
      <div class="next-cta"><button class="btn primary" id="cta-next">Next problem ›</button><span class="muted small">or press <kbd>N</kbd></span></div>`;
  } else {
    const f = r.failure || {};
    const c = r.cases[f.index] || r.cases.find((x) => !x.passed) || {};
    html = `<div class="verdict bad">Wrong answer <span class="sub">${k}/${n} tests passed · solution unlocked</span></div><div class="tests">${chips}</div>${warningsHtml(r.warnings)}
      <h3 style="margin-top:6px">First failure: ${esc(f.name || c.name || "")}</h3>`;
    if (c.error) html += `<pre class="out err">${esc(c.error)}</pre>`;
    else html += `<div class="diffmsg">${esc(c.diff)}</div>`;
    if (f.stdout) html += `<div class="io-label">stdout</div><pre class="out">${esc(f.stdout)}</pre>`;
    if (f.inputs) html += `<details open><summary class="io-label" style="cursor:pointer">Input</summary>${Object.entries(f.inputs).map(([k2, v]) => renderPreview(v, k2)).join("")}</details>`;
    if (!c.error) html += `<div class="cols2" style="margin-top:10px"><div class="panel-box"><div class="lbl">Expected</div>${renderPreview(f.expected)}</div><div class="panel-box"><div class="lbl">Got</div>${renderPreview(f.got)}</div></div>`;
    else if (f.expected) html += `<div class="panel-box" style="margin-top:10px"><div class="lbl">Expected</div>${renderPreview(f.expected)}</div>`;
  }
  res.innerHTML = html;
  const b = $("#cta-next"); if (b) { b.onclick = () => navigate("next"); }
}

// ----- navigation --------------------------------------------------------
function navigate(kind) {
  const cur = view.id;
  if (kind === "next" && view.queue) {
    const q = view.queue, i = q.ids.indexOf(cur);
    const rest = q.ids.slice(i + 1).concat(q.ids.slice(0, Math.max(i, 0)));
    const nxt = rest.find((id) => !queueItemDone(q, id));
    if (!nxt) { const back = q.back; view.queue = null; toast(`${q.name}: all done`); location.hash = back || "#today"; return; }
    return openProblem(nxt, { review: q.review && isDue(nxt), queue: q });
  }
  let target;
  const i = PATH.indexOf(cur);
  if (kind === "next") target = PATH[(i + 1) % PATH.length];
  else if (kind === "unsolved") {
    const order = PATH.slice(i + 1).concat(PATH.slice(0, i + 1));
    target = order.find((id) => status(id) !== "solved" && id !== cur);
    if (!target) { toast("Everything is solved. Try Review."); return; }
  } else if (kind === "random") {
    const pool = filteredProblems().map((p) => p.id).filter((id) => id !== cur);
    if (!pool.length) { toast("No other problem matches the current filters."); return; }
    const unsolved = pool.filter((id) => status(id) !== "solved");
    const from = unsolved.length ? unsolved : pool;
    target = from[Math.floor(Math.random() * from.length)];
  }
  openProblem(target, { queue: null });
}

function queueItemDone(q, id) {
  const p = getP(id);
  return !!(p.lastPassAt && p.lastPassAt >= (q.started || startOfDay()));
}

// ===========================================================================
// Today
// ===========================================================================
// New problems are drawn from every selected section (next ones in learning-path
// order within each section) and interleaved: NumPy, pandas, Plotting, ... , NumPy, ...
function todaySettings() {
  const s = S().settings;
  if (!Array.isArray(s.todaySections)) s.todaySections = SECTIONS.map((x) => x.key);
  if (typeof s.newPerSection !== "number") s.newPerSection = 1;
  return { secs: SECTIONS.map((x) => x.key).filter((k) => s.todaySections.includes(k)), per: s.newPerSection };
}
function pickFresh(per, secs, exclude, have = []) {
  const lists = secs.map((k) => {
    const already = have.filter((id) => BY_ID[id] && BY_ID[id].section === k).length;
    return PATH.filter((id) => BY_ID[id].section === k && status(id) === "new" && !exclude.has(id)).slice(0, Math.max(0, per - already));
  });
  const out = [];
  for (let i = 0; i < per; i++) lists.forEach((l) => { if (l[i]) out.push(l[i]); });
  return out;
}
function todayPlan() {
  const key = dayKey(), { secs, per } = todaySettings();
  const sig = secs.join(",") + "|" + per;
  let t = S().today;
  if (!t || t.date !== key) {
    const due = PATH.filter((id) => isDue(id, endOfDay()));
    t = S().today = { date: key, due, fresh: pickFresh(per, secs, new Set(due)), sig, rounds: 0 };
    Store.save();
  } else if (t.sig !== sig) {
    // settings changed today: keep what was already worked on, refill the rest
    const keep = t.fresh.filter((id) => BY_ID[id] && (status(id) !== "new" || doneToday(id)));
    t.fresh = keep.concat(pickFresh(per + (t.rounds || 0), secs, new Set([...t.due, ...keep]), keep));
    t.sig = sig; Store.save();
  }
  return t;
}
const doneToday = (id) => (getP(id).lastPassAt || 0) >= startOfDay();

function streak() {
  const d = S().days; let n = 0, t = now();
  const active = (k) => d[k] && (d[k].solved + d[k].reviews + d[k].cards) > 0;
  if (!active(dayKey(t))) t -= DAY;
  while (active(dayKey(t))) { n++; t -= DAY; }
  return n;
}

function historyChart(days = 30) {
  const d = S().days, vals = [];
  for (let i = days - 1; i >= 0; i--) { const k = dayKey(now() - i * DAY); const x = d[k] || {}; vals.push({ k, solved: x.solved || 0, reviews: x.reviews || 0, cards: x.cards || 0 }); }
  const max = Math.max(4, ...vals.map((v) => v.solved + v.reviews));
  const W = 600, H = 120, bw = W / days;
  const bars = vals.map((v, i) => {
    const h1 = (v.solved / max) * (H - 18), h2 = (v.reviews / max) * (H - 18);
    return `<g><title>${v.k}: ${v.solved} new solved, ${v.reviews} reviews, ${v.cards} cards</title>
      <rect x="${i * bw + 2}" y="${H - 14 - h1}" width="${bw - 4}" height="${h1}" rx="2" fill="var(--accent)"></rect>
      <rect x="${i * bw + 2}" y="${H - 14 - h1 - h2}" width="${bw - 4}" height="${h2}" rx="2" fill="var(--review)" opacity=".75"></rect></g>`;
  }).join("");
  const labels = [[0, "start", 2], [Math.floor(days / 2), "middle", Math.floor(days / 2) * bw + bw / 2], [days - 1, "end", W - 2]]
    .map(([i, anchor, x]) => `<text x="${x}" y="${H - 2}" font-size="10" fill="var(--muted)" text-anchor="${anchor}">${vals[i].k.slice(5)}</text>`).join("");
  return `<div class="chart"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Problems solved per day">${bars}${labels}</svg></div>
    <div class="row small muted"><span><span style="display:inline-block;width:10px;height:10px;background:var(--accent);border-radius:2px"></span> new solved</span><span><span style="display:inline-block;width:10px;height:10px;background:var(--review);border-radius:2px;opacity:.75"></span> reviews</span></div>`;
}

function renderToday() {
  const t = todayPlan(), all = t.due.concat(t.fresh);
  const done = all.filter(doneToday).length, sk = streak();
  const item = (id, kind) => {
    const p = BY_ID[id]; if (!p) return "";
    return `<li><span class="${doneToday(id) ? "done" : "muted"}">${doneToday(id) ? "✓" : "○"}</span><span class="ttl"><a href="#problems/${id}${kind === "due" ? "/review" : ""}" data-q="${id}" data-kind="${kind}">${p.num}. ${esc(p.title)}</a></span>
      <span class="diff ${p.difficulty}">${p.difficulty}</span><span class="tag">${esc(SEC_TITLE[p.section])}</span>${kind === "due" ? `<span class="chip review">${dueReason(id) || "review"}</span>` : ""}</li>`;
  };
  const finished = all.length > 0 && done === all.length;
  const cardsDue = cardQueue("all").due.length;
  const el = $("#view-today");
  el.innerHTML = `<div class="inner">
    <div class="page-title"><h1>Today</h1><span class="muted">${new Date().toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" })}</span><span class="grow"></span><span class="chip solved">🔥 ${sk}-day streak</span></div>
    ${finished ? `<div class="card empty"><div class="big">🎉</div><h2>Done for today</h2><p>${done} problem${done === 1 ? "" : "s"} done${cardsDue ? ` · ${cardsDue} flashcards are due` : ""}. Come back tomorrow for the next reviews.</p>
      <div class="row" style="justify-content:center;margin-top:10px"><button class="btn" id="t-more">+1 more per section</button>${cardsDue ? `<a class="btn" href="#cards">Flashcards (${cardsDue})</a>` : ""}<a class="btn" href="#playground">Playground</a></div></div>` : ""}
    <div class="card"><div class="row"><h2 style="margin:0">Queue</h2><span class="muted">${done}/${all.length} done</span><span class="grow"></span>
      <label class="small muted">New per section <input type="number" id="t-n" min="0" max="5" value="${S().settings.newPerSection}" style="width:52px;padding:3px 6px"></label>
      ${!finished && all.length ? `<button class="btn primary" id="t-start">${done ? "Continue" : "Start"} ▶</button>` : ""}</div>
      <div class="sec-toggles" title="Sections that contribute new problems to Today">${SECTIONS.map((s) =>
        `<button type="button" class="sec-chip ${S().settings.todaySections.includes(s.key) ? "on" : ""}" data-sec="${s.key}">${esc(s.title)}</button>`).join("")}</div>
      ${t.due.length ? `<h3 style="margin-top:14px">Due reviews (${t.due.length})</h3><ul class="qlist">${t.due.map((id) => item(id, "due")).join("")}</ul>` : ""}
      ${t.fresh.length ? `<h3 style="margin-top:14px">New problems (${t.fresh.length})</h3><ul class="qlist">${t.fresh.map((id) => item(id, "new")).join("")}</ul>` : ""}
      ${!all.length ? `<p class="muted">Nothing queued: no reviews are due and no new problems are left in the selected sections.</p>` : ""}
    </div>
    <div class="card"><h2>Last 30 days</h2>${historyChart()}</div></div>`;
  const start = () => {
    const ids = all.filter((id) => !doneToday(id));
    if (!ids.length) return;
    const q = { name: "Today", ids: all, review: true, started: startOfDay(), back: "#today" };
    openProblem(ids[0], { review: t.due.includes(ids[0]), queue: q });
  };
  const sb = $("#t-start"); if (sb) sb.onclick = start;
  $("#t-n").onchange = (e) => { S().settings.newPerSection = Math.max(0, Math.min(5, +e.target.value || 0)); Store.save(); renderToday(); updateBadges(); };
  $$("[data-sec]", el).forEach((b) => (b.onclick = () => {
    const s = S().settings, k = b.dataset.sec;
    s.todaySections = s.todaySections.includes(k) ? s.todaySections.filter((x) => x !== k) : [...s.todaySections, k];
    Store.save(); renderToday(); updateBadges();
  }));
  const more = $("#t-more"); if (more) more.onclick = () => {
    t.rounds = (t.rounds || 0) + 1;
    t.fresh = t.fresh.concat(pickFresh(1, todaySettings().secs, new Set([...t.due, ...t.fresh])));
    Store.save(); renderToday(); updateBadges();
  };
  $$("[data-q]", el).forEach((a) => (a.onclick = (e) => {
    e.preventDefault();
    const q = { name: "Today", ids: all, review: true, started: startOfDay(), back: "#today" };
    openProblem(a.dataset.q, { review: a.dataset.kind === "due", queue: q });
  }));
}

// ===========================================================================
// Review
// ===========================================================================
function renderReview() {
  const t = now();
  const due = PATH.filter((id) => isDue(id, t));
  const upcoming = PATH.filter((id) => getP(id).srs && getP(id).srs.due > t && !getP(id).flagged)
    .sort((a, b) => getP(a).srs.due - getP(b).srs.due);
  const el = $("#view-review");
  el.innerHTML = `<div class="inner"><div class="page-title"><h1>Review</h1><span class="muted">failed, peeked and flagged problems, plus solved ones coming back after ~1, 3, 7, 21 days</span></div>
    <div class="card"><div class="row"><h2 style="margin:0">Due now (${due.length})</h2><span class="grow"></span>${due.length ? `<button class="btn primary" id="r-start">Start review ▶</button>` : ""}</div>
      <p class="muted small">In review the editor starts from the blank starter, not your old code.</p>
      ${due.length ? `<ul class="qlist">${due.map((id) => { const p = BY_ID[id]; return `<li><span class="ttl"><a href="#problems/${id}/review" data-r="${id}">${p.num}. ${esc(p.title)}</a></span><span class="diff ${p.difficulty}">${p.difficulty}</span><span class="chip review">${dueReason(id)}</span><span class="muted small">${getP(id).srs ? "stage " + (getP(id).srs.stage || 0) : ""}</span></li>`; }).join("")}</ul>` : `<div class="empty"><div class="big">✓</div>Nothing due. Solved problems come back automatically.</div>`}
    </div>
    <div class="card"><h2>Coming up</h2>${upcoming.length ? `<ul class="qlist">${upcoming.slice(0, 40).map((id) => { const p = BY_ID[id]; return `<li><span class="ttl"><a href="#problems/${id}">${p.num}. ${esc(p.title)}</a></span><span class="muted small">in ${fmtIn(getP(id).srs.due - t)}</span></li>`; }).join("")}</ul>` : `<p class="muted">Solve problems to fill the schedule.</p>`}</div></div>`;
  const q = { name: "Review", ids: due, review: true, started: t, back: "#review" };
  const s = $("#r-start"); if (s) s.onclick = () => openProblem(due[0], { review: true, queue: q });
  $$("[data-r]", el).forEach((a) => (a.onclick = (e) => { e.preventDefault(); openProblem(a.dataset.r, { review: true, queue: q }); }));
}

// ===========================================================================
// Flashcards (no Python needed)
// ===========================================================================
const fc = { deck: null, card: null, shown: false, session: 0 };
function cardQueue(deck) {
  const t = now(), cs = S().cards;
  const inDeck = ALL_CARDS.filter((c) => deck === "all" || (deck === "recall" ? c.type === "recall" : deck === "predict" ? c.type === "predict" : c.section === deck));
  const due = inDeck.filter((c) => cs[c.id] && cs[c.id].due <= t).sort((a, b) => cs[a.id].due - cs[b.id].due);
  const fresh = inDeck.filter((c) => !cs[c.id]);
  const left = Math.max(0, S().settings.cardsNewPerDay - (day().newCards || 0));
  return { due, fresh: fresh.slice(0, left), freshTotal: fresh.length, total: inDeck.length };
}
function renderCards() {
  const el = $("#view-cards"), deck = S().settings.deck || "all", q = cardQueue(deck);
  const decks = [["all", "All"], ["recall", "Recall"], ["predict", "Predict output"]];
  const card = q.due[0] || q.fresh[0] || null;
  fc.card = card; fc.shown = false;
  let body;
  if (!card) {
    body = `<div class="fc empty"><div class="big">✓</div><h2>No cards due</h2><p>${q.freshTotal ? `New-card limit reached for today (${S().settings.cardsNewPerDay}/day).` : "You've seen every card in this deck."}</p>
      <p class="small"><label>New cards per day <input type="number" id="fc-n" min="0" max="200" value="${S().settings.cardsNewPerDay}" style="width:64px;padding:3px 6px"></label></p></div>`;
  } else {
    const srs = S().cards[card.id];
    const kind = card.type === "predict" ? "Predict the output" : "Recall the one-liner";
    const front = card.type === "predict"
      ? `${codeBlock(card.code)}<div class="ask">What does this print or show? Say it out loud, then reveal.</div>`
      : `<div class="front">${esc(card.front)}</div><div class="ask">Write the idiomatic call (in your head or on paper), then reveal.</div>`;
    const back = card.type === "predict"
      ? `<div class="io-label">Output</div><pre class="out">${esc(card.output)}</pre>${card.note ? `<div class="note">${card.note}</div>` : ""}`
      : `${codeBlock(card.back)}${card.pid ? `<div class="small"><a href="#problems/${card.pid}">Open the problem ›</a></div>` : ""}${card.note ? `<div class="note">${esc(card.note)}</div>` : ""}`;
    body = `<div class="fc"><div class="kind">${kind}<span class="tag">${esc(SEC_TITLE[card.section] || card.section || "")}</span>${card.topic ? `<span class="tag">${esc(card.topic)}</span>` : ""}${srs ? "" : `<span class="new-badge">NEW</span>`}</div>
      ${front}<div class="answer" id="fc-answer" hidden>${back}</div><div class="grow"></div>
      <button class="btn primary reveal-btn" id="fc-reveal">Show answer <kbd>Space</kbd></button>
      <div class="rate" id="fc-rate" hidden>
        ${["again", "hard", "good", "easy"].map((r, i) => `<button class="${r}" data-rate="${r}">${r[0].toUpperCase() + r.slice(1)} <kbd>${i + 1}</kbd><small>${previewInterval(srs, r)}</small></button>`).join("")}
      </div></div>`;
  }
  el.innerHTML = `<div class="fc-wrap">
    <div class="page-title"><h1>Flashcards</h1><span class="muted">${q.due.length} due · ${q.fresh.length} new today · ${q.total} in deck</span></div>
    <div class="fc-bar"><div class="seg">${decks.map(([k, l]) => `<button data-deck="${k}" class="${deck === k ? "on" : ""}">${l}</button>`).join("")}</div>
      <select id="fc-sec" aria-label="Section deck"><option value="">By section…</option>${SECTIONS.map((s) => `<option value="${s.key}" ${deck === s.key ? "selected" : ""}>${esc(s.title)}</option>`).join("")}</select>
      <span class="grow"></span><span class="muted small">Same spaced-repetition scheduler as problems</span></div>
    ${body}</div>`;
  highlight(el);
  $$("[data-deck]", el).forEach((b) => (b.onclick = () => { S().settings.deck = b.dataset.deck; Store.save(); renderCards(); }));
  $("#fc-sec").onchange = (e) => { if (e.target.value) { S().settings.deck = e.target.value; Store.save(); renderCards(); } };
  const n = $("#fc-n"); if (n) n.onchange = (e) => { S().settings.cardsNewPerDay = Math.max(0, +e.target.value || 0); Store.save(); renderCards(); };
  const rv = $("#fc-reveal"); if (rv) rv.onclick = revealCard;
  $$("[data-rate]", el).forEach((b) => (b.onclick = () => rateCard(b.dataset.rate)));
}
function revealCard() {
  if (!fc.card || fc.shown) return;
  fc.shown = true; $("#fc-answer").hidden = false; $("#fc-rate").hidden = false; $("#fc-reveal").hidden = true;
  highlight($("#fc-answer"));
}
function rateCard(r) {
  if (!fc.card || !fc.shown) return;
  const cs = S().cards, prev = cs[fc.card.id], d = day();
  if (!prev) d.newCards = (d.newCards || 0) + 1;
  cs[fc.card.id] = schedule(prev, r);
  d.cards++; Store.save(); updateBadges(); renderCards();
}

// ===========================================================================
// Playground + Mock interview (share the worker's persistent namespace)
// ===========================================================================
const pg = { editor: null, prompt: null, busy: false, walk: {} };
const mk = { editor: null, attempt: null, timer: null, busy: false };

function datasetTable() {
  const rows = DATA.playground_preload.split("\n").map((l) => l.match(/^(\w+)\s*=\s*(.+)$/)).filter(Boolean);
  return `<table class="ds-table">${rows.map((m) => `<tr><td>${esc(m[1])}</td><td class="muted mono">${esc(m[2])}</td></tr>`).join("")}</table>
    <p class="muted small">Also preloaded: <code>np</code>, <code>pd</code>, <code>plt</code>, <code>sns</code>, <code>D</code> (generators). Import sklearn / scipy / statsmodels yourself. sklearn's <code>load_*</code> datasets work offline.</p>`;
}

function initPlayground() {
  pg.editor = makeEditor($("#pg-editor"), { "Ctrl-Enter": () => pgRun(pg, "#pg-out"), "Cmd-Enter": () => pgRun(pg, "#pg-out") });
  pg.editor.onChange(() => { S().pgDrafts[pg.prompt || "free"] = pg.editor.getValue(); Store.save(); });
  $("#pg-run").onclick = () => pgRun(pg, "#pg-out");
  $("#pg-stop").onclick = () => Py.stop("stopped");
  $("#pg-reset").onclick = () => pgReset("#pg-out");
  $("#pg-clear").onclick = () => ($("#pg-out").innerHTML = "");
}
function renderPlayground() {
  const side = $("#pg-side"), id = pg.prompt;
  const pr = DATA.playground.find((x) => x.id === id);
  side.innerHTML = `<h1>Playground</h1><p class="muted small">Ungraded. Every dataset is preloaded; the namespace persists until you reset it. Assemble the bricks yourself.</p>
    <ul class="pg-list"><li data-pg="" class="${!id ? "active" : ""}"><span class="n">·</span>Free play</li>
    ${DATA.playground.map((x, i) => `<li data-pg="${x.id}" class="${id === x.id ? "active" : ""}"><span class="n">${i + 1}</span>${esc(x.title)}</li>`).join("")}</ul>
    ${pr ? `<div class="card"><h2>${esc(pr.title)}</h2><div class="statement">${pr.prompt}</div>
      <p class="small muted">Suggested time: ${pr.minutes} min · datasets: ${pr.datasets.map((d) => `<code>${esc(d)}</code>`).join(" ")}</p>
      <div id="walk">${pg.walk[pr.id] ? walkthroughHtml(pr) : `<button class="btn" id="walk-btn">Reveal reference walkthrough</button>`}</div></div>` : ""}
    <h3>Datasets</h3>${datasetTable()}`;
  $$("[data-pg]", side).forEach((li) => (li.onclick = () => { pg.prompt = li.dataset.pg || null; loadPgDraft(); renderPlayground(); }));
  const wb = $("#walk-btn"); if (wb) wb.onclick = async () => {
    if (await confirmBox("Reveal the walkthrough?", "Try the prompt yourself first. The walkthrough is one reasonable answer, not the only one.", "Reveal")) { pg.walk[pr.id] = true; renderPlayground(); }
  };
  highlight(side);
  setTimeout(() => pg.editor.refresh(), 0);
}
function walkthroughHtml(pr) { return `<h3>Reference walkthrough</h3>` + pr.steps.map((s) => `<div class="walk-step">${s.md}${s.code ? codeBlock(s.code) : ""}</div>`).join(""); }
function loadPgDraft() {
  const key = pg.prompt || "free";
  const pr = DATA.playground.find((x) => x.id === pg.prompt);
  const first = pr && pr.datasets.find((d) => /^\w+$/.test(d));
  pg.editor.setValue(S().pgDrafts[key] ?? (pr ? `# ${pr.title}\n# Datasets: ${pr.datasets.join(", ")}\n\n${first ? first + ".head()" : ""}\n` :"# Everything is preloaded: orders, customers, hr, churn, prices, ...\nchurn.head()\n"));
}

async function pgRun(ctx, outSel) {
  if (ctx.busy) return;
  const sel = ctx.editor.getSelection(), code = sel && sel.trim() ? sel : ctx.editor.getValue();
  if (!code.trim()) return;
  ctx.busy = true; setPgBusy(ctx, true);
  const out = $(outSel);
  const cell = document.createElement("div"); cell.className = "cell";
  const first = code.trim().split("\n")[0];
  cell.innerHTML = `<div class="cell-head">${sel && sel.trim() ? "selection · " : ""}${esc(first.slice(0, 90))}</div><div class="cell-body muted">${Py.st.ready ? "Running…" : "Waiting for Python…"}</div>`;
  out.appendChild(cell); cell.scrollIntoView({ block: "end" });
  const r = await Py.run({ kind: "playground", code }, {
    needs: ["matplotlib", "seaborn"], timeout: 60000,
    onWaiting: (pkg) => { $(".cell-body", cell).textContent = `Loading ${pkg}…`; },
  });
  ctx.busy = false; setPgBusy(ctx, false);
  let html = "";
  if (r.stopped) html = `<div class="verdict bad">${r.stopped === "timeout" ? "Time limit exceeded (60 s)" : "Stopped"}</div><p class="muted small">Python restarted: the namespace was reset.</p>`;
  else if (r.internal_error) html = `<pre class="out err">${esc(r.internal_error)}</pre>`;
  else {
    if (r.stdout) html += `<pre class="out">${esc(r.stdout)}</pre>`;
    html += warningsHtml(r.warnings);
    if (r.error) html += `<pre class="out err">${esc(r.error)}</pre>`;
    if (r.value) html += renderPreview(r.value);
    if (r.figures) html += r.figures.map((f) => `<div class="fig"><img src="data:image/png;base64,${f}"></div>`).join("");
    if (!html) html = `<span class="muted small">✓ done (no output)</span>`;
  }
  $(".cell-body", cell).className = "cell-body"; $(".cell-body", cell).innerHTML = html;
  cell.scrollIntoView({ block: "nearest" });
}
function setPgBusy(ctx, b) {
  if (ctx === pg) { $("#pg-run").disabled = b; $("#pg-stop").hidden = !b; }
  else { const r = $("#mk-run"); if (r) r.disabled = b; const s = $("#mk-stop"); if (s) s.hidden = !b; }
}
async function pgReset(outSel) {
  const out = $(outSel);
  const cell = document.createElement("div");
  cell.className = "cell";
  cell.innerHTML = `<div class="cell-head">reset</div><div class="cell-body muted">Resetting namespace…</div>`;
  out.appendChild(cell);
  const r = await Py.run({ kind: "playground_reset" }, { needs: ["matplotlib", "seaborn"], timeout: 30000 });
  $(".cell-body", cell).innerHTML = r.ok ? `Fresh namespace with ${r.names.length} datasets reloaded.` : esc(r.internal_error || r.stopped || "failed");
}

function renderMock() {
  const el = $("#view-mock"), a = mk.attempt;
  if (!a) {
    const hist = S().mock.slice().reverse();
    el.innerHTML = `<div class="page" style="grid-column:1/-1"><div class="inner">
      <div class="page-title"><h1>Mock interview</h1><span class="muted">45 minutes, one open-ended prompt, no hints or walkthroughs until you finish.</span></div>
      <div class="card"><div class="row"><select id="mk-pick"><option value="">Random prompt</option>${DATA.playground.map((x) => `<option value="${x.id}">${esc(x.title)}</option>`).join("")}</select>
        <button class="btn primary big" id="mk-start">Start 45-minute mock ▶</button></div>
        <p class="muted small" style="margin-top:10px">The Python namespace is reset at the start (datasets reloaded). Talk through your reasoning as you would with an interviewer; at the end you'll score yourself on a 7-point rubric.</p></div>
      <div class="card"><h2>Past attempts</h2>${hist.length ? `<table class="grid"><thead><tr><th>Date</th><th>Prompt</th><th class="num">Score</th><th class="num">Time</th><th></th></tr></thead><tbody>
        ${hist.map((h, i) => `<tr><td>${new Date(h.start).toLocaleString()}</td><td>${esc((DATA.playground.find((x) => x.id === h.prompt) || {}).title || h.prompt)}</td><td class="num">${h.score}/${RUBRIC.length}</td><td class="num">${fmtDur(h.durationMs)}</td><td><a href="#" data-mh="${hist.length - 1 - i}">view code</a></td></tr>`).join("")}</tbody></table>` : `<p class="muted">No attempts yet.</p>`}</div></div></div>`;
    $("#mk-start").onclick = () => {
      const pick = $("#mk-pick").value || DATA.playground[Math.floor(Math.random() * DATA.playground.length)].id;
      mk.attempt = { prompt: pick, start: now(), phase: "work", code: "" };
      renderMock(); pgReset("#mk-out");
    };
    $$("[data-mh]", el).forEach((x) => (x.onclick = (e) => {
      e.preventDefault(); const h = S().mock[+x.dataset.mh];
      modal(`<h2>${esc((DATA.playground.find((y) => y.id === h.prompt) || {}).title || "")}</h2><p class="muted small">${new Date(h.start).toLocaleString()} · score ${h.score}/${RUBRIC.length}</p>
        <ul>${RUBRIC.map((r, i) => `<li>${h.rubric[i] ? "✓" : "✗"} ${esc(r)}</li>`).join("")}</ul>${codeBlock(h.code || "(empty)")}<div class="acts"><button class="btn" data-close>Close</button></div>`);
      highlight($("#modal-body"));
    }));
    return;
  }
  const pr = DATA.playground.find((x) => x.id === a.prompt);
  const left = a.start + 45 * MIN - now();
  el.innerHTML = `<aside class="pg-side">
      <div class="row"><span class="timer-big ${left < 5 * MIN ? "low" : ""}" id="mk-timer">${fmtClock(Math.max(0, left))}</span><span class="grow"></span>
        ${a.phase === "work" ? `<button class="btn success" id="mk-finish">Finish</button>` : ""}<button class="btn ghost" id="mk-abandon">Abandon</button></div>
      <h2 style="margin-top:12px">${esc(pr.title)}</h2><div class="statement">${pr.prompt}</div>
      <p class="small muted">Datasets: ${pr.datasets.map((d) => `<code>${esc(d)}</code>`).join(" ")}</p>
      <div id="mk-phase"></div><h3>Datasets</h3>${datasetTable()}</aside>
    <section class="pg-main"><div class="toolbar"><button class="btn primary" id="mk-run">▶ Run</button><button class="btn danger" id="mk-stop" hidden>■ Stop</button>
      <span class="grow"></span><span class="muted small">Selection runs alone · ${MOD}+Enter</span></div>
      <div class="editor-host" id="mk-editor"></div><div class="results" id="mk-out"></div></section>`;
  mk.editor = makeEditor($("#mk-editor"), { "Ctrl-Enter": () => pgRun(mk, "#mk-out"), "Cmd-Enter": () => pgRun(mk, "#mk-out") });
  mk.editor.setValue(a.code || `# ${pr.title}\n# 45 minutes. Explore, model, evaluate, interpret.\n\n`);
  mk.editor.onChange(() => { a.code = mk.editor.getValue(); });
  $("#mk-run").onclick = () => pgRun(mk, "#mk-out");
  $("#mk-stop").onclick = () => Py.stop("stopped");
  const fin = $("#mk-finish"); if (fin) fin.onclick = () => { a.phase = "rubric"; a.end = now(); renderMockPhase(); fin.remove(); };
  $("#mk-abandon").onclick = async () => { if (await confirmBox("Abandon this mock?", "Nothing will be saved.", "Abandon")) { mk.attempt = null; clearInterval(mk.timer); renderMock(); } };
  clearInterval(mk.timer);
  mk.timer = setInterval(() => {
    if (!mk.attempt) return clearInterval(mk.timer);
    const l = mk.attempt.start + 45 * MIN - now(), t = $("#mk-timer");
    if (t) { t.textContent = fmtClock(Math.max(0, l)); t.classList.toggle("low", l < 5 * MIN); }
    if (l <= 0 && mk.attempt.phase === "work") { mk.attempt.phase = "rubric"; mk.attempt.end = now(); toast("Time's up!"); renderMockPhase(); const f = $("#mk-finish"); if (f) f.remove(); }
  }, 500);
  renderMockPhase();
  setTimeout(() => { mk.editor.refresh(); mk.editor.focus(); }, 0);
}
function renderMockPhase() {
  const a = mk.attempt, box = $("#mk-phase"); if (!a || !box) return;
  const pr = DATA.playground.find((x) => x.id === a.prompt);
  if (a.phase === "work") { box.innerHTML = `<p class="muted small">Hints and walkthroughs are hidden until you finish.</p>`; return; }
  if (a.phase === "rubric") {
    box.innerHTML = `<div class="card"><h3>Self-check</h3><div class="rubric">${RUBRIC.map((r, i) => `<label><input type="checkbox" data-rb="${i}"> <span>${esc(r)}</span></label>`).join("")}</div>
      <button class="btn primary" id="mk-save" style="margin-top:10px">Save score and reveal the walkthrough</button></div>`;
    $("#mk-save").onclick = () => {
      const rub = RUBRIC.map((_, i) => $(`[data-rb="${i}"]`).checked);
      const rec = { prompt: a.prompt, start: a.start, durationMs: (a.end || now()) - a.start, code: mk.editor ? mk.editor.getValue() : a.code, rubric: rub, score: rub.filter(Boolean).length };
      S().mock.push(rec); if (S().mock.length > 50) S().mock.shift(); Store.save();
      a.phase = "done"; a.score = rec.score; renderMockPhase();
    };
    return;
  }
  box.innerHTML = `<div class="okmsg">Saved: ${a.score}/${RUBRIC.length}. <a href="#" id="mk-new">Back to mock menu</a></div>${walkthroughHtml(pr)}`;
  $("#mk-new").onclick = (e) => { e.preventDefault(); mk.attempt = null; clearInterval(mk.timer); renderMock(); };
  highlight(box);
}

// ===========================================================================
// Bricks cheat sheet
// ===========================================================================
function renderBricks() {
  const el = $("#view-bricks");
  el.innerHTML = `<div class="inner"><div class="page-title"><h1>Bricks</h1><span class="muted">every Hint 2 call shape, by section: a last-minute cheat sheet</span><span class="grow"></span>
    <input type="search" id="b-search" placeholder="Filter…" style="padding:5px 9px"></div><div id="b-body"></div></div>`;
  const draw = () => {
    const q = $("#b-search").value.trim().toLowerCase();
    $("#b-body").innerHTML = SECTIONS.map((s) => {
      const ps = PROBS.filter((p) => p.section === s.key && (!q || (p.title + " " + p.hint2 + " " + p.tags.join(" ")).toLowerCase().includes(q)));
      if (!ps.length) return "";
      return `<div class="bricks-sec card"><h2>${esc(s.title)} <span class="muted small">${ps.length}</span></h2>${ps.map((p) => `<div class="brick"><div class="bt"><a href="#problems/${p.id}">${p.num}. ${esc(p.title)}</a><span class="diff ${p.difficulty}">${p.difficulty}</span>${statusIcon(p.id)}</div>${codeBlock(p.hint2)}</div>`).join("")}</div>`;
    }).join("") || `<p class="muted">Nothing matches.</p>`;
    highlight($("#b-body"));
  };
  $("#b-search").oninput = draw; draw();
}

// ===========================================================================
// Stats
// ===========================================================================
function topicStats() {
  const rows = {};
  for (const p of PROBS) {
    for (const tag of p.tags.slice(0, 1)) {
      const key = p.section + "|" + tag;
      const r = rows[key] || (rows[key] = { key, section: p.section, tag, ids: [], attempted: 0, solved: 0, submits: 0, passes: 0, peeked: 0, times: [], due: 0 });
      const x = getP(p.id);
      r.ids.push(p.id);
      if (x.attempts || x.runs) r.attempted++;
      if (x.solvedAt) r.solved++;
      r.submits += x.attempts || 0; r.passes += x.passes || 0;
      if (x.peeks) r.peeked++;
      if (x.times && x.times.length) r.times.push(x.times[0]);
      if (isDue(p.id)) r.due++;
    }
  }
  return Object.values(rows).map((r) => ({ ...r, accuracy: r.submits ? r.passes / r.submits : null, peekRate: r.attempted ? r.peeked / r.attempted : null, medTime: median(r.times) }));
}
function weakestTopic(rows) {
  const tried = rows.filter((r) => r.attempted >= 1 && r.submits >= 1);
  if (tried.length) return tried.sort((a, b) => ((a.accuracy ?? 1) - (a.peekRate ?? 0) / 2) - ((b.accuracy ?? 1) - (b.peekRate ?? 0) / 2))[0];
  return rows.find((r) => r.solved < r.ids.length) || rows[0];
}
function renderStats() {
  const rows = topicStats(), el = $("#view-stats");
  const solved = PROBS.filter((p) => status(p.id) === "solved").length;
  const attempted = PROBS.filter((p) => status(p.id) !== "new").length;
  const due = PATH.filter((id) => isDue(id)).length;
  const cardsDue = cardQueue("all").due.length;
  const allTimes = PROBS.map((p) => (getP(p.id).times || [])[0]).filter((x) => x != null);
  const subs = PROBS.reduce((a, p) => a + (getP(p.id).attempts || 0), 0), passes = PROBS.reduce((a, p) => a + (getP(p.id).passes || 0), 0);
  const w = weakestTopic(rows);
  el.innerHTML = `<div class="inner"><div class="page-title"><h1>Stats</h1><span class="grow"></span><button class="btn" id="st-copy">Copy my stats for Claude</button>${w ? `<button class="btn primary" id="st-drill">Drill weakest topic: ${esc(w.tag)} ▶</button>` : ""}</div>
    <div class="tiles">
      <div class="tile"><div class="v">${solved}<span class="muted" style="font-size:14px">/${PROBS.length}</span></div><div class="k">solved</div></div>
      <div class="tile"><div class="v">${attempted}</div><div class="k">attempted</div></div>
      <div class="tile"><div class="v">${pct(subs ? passes / subs : null)}</div><div class="k">submit accuracy</div></div>
      <div class="tile"><div class="v">${fmtDur(median(allTimes))}</div><div class="k">median time to solve</div></div>
      <div class="tile"><div class="v">${due}</div><div class="k">reviews due</div></div>
      <div class="tile"><div class="v">${cardsDue}</div><div class="k">cards due</div></div>
      <div class="tile"><div class="v">🔥 ${streak()}</div><div class="k">day streak</div></div>
    </div>
    <div class="card"><h2>Last 30 days</h2>${historyChart()}</div>
    <div class="card"><h2>By topic</h2><div style="overflow:auto"><table class="grid"><thead><tr><th>Section</th><th>Topic</th><th class="num">Problems</th><th class="num">Solved</th><th class="num">Accuracy</th><th class="num">Median time</th><th class="num">Peek rate</th><th class="num">Due</th><th></th></tr></thead><tbody>
      ${rows.map((r) => `<tr><td>${esc(SEC_TITLE[r.section])}</td><td>${esc(r.tag)}</td><td class="num">${r.ids.length}</td>
        <td class="num"><span class="meter"><span style="width:${(r.solved / r.ids.length) * 100}%"></span></span>${r.solved}</td>
        <td class="num">${pct(r.accuracy)}</td><td class="num">${fmtDur(r.medTime)}</td><td class="num">${pct(r.peekRate)}</td><td class="num">${r.due || ""}</td>
        <td><a href="#" data-drill="${esc(r.key)}">drill</a></td></tr>`).join("")}</tbody></table></div>
      <p class="muted small">Accuracy = passed submits / all submits. Peek rate = share of attempted problems where you viewed the solution. Time = first successful solve. Topic = a problem's first tag.</p></div></div>`;
  $("#st-copy").onclick = copyStats;
  const d = $("#st-drill"); if (d) d.onclick = () => drill(w);
  $$("[data-drill]", el).forEach((a) => (a.onclick = (e) => { e.preventDefault(); drill(rows.find((r) => r.key === a.dataset.drill)); }));
}
function drill(r) {
  if (!r) return;
  const t = now();
  const score = (id) => (isDue(id, t) && status(id) !== "new" ? 0 : status(id) === "attempted" ? 1 : status(id) === "new" ? 2 : 3 + (getP(id).lastPassAt || 0) / 1e15);
  const ids = [...r.ids].sort((a, b) => score(a) - score(b)).slice(0, 5);
  const q = { name: `Drill: ${r.tag}`, ids, review: true, started: t, back: "#stats" };
  openProblem(ids[0], { review: isDue(ids[0]), queue: q });
}
function statsText() {
  const rows = topicStats(), lines = [];
  const solved = PROBS.filter((p) => status(p.id) === "solved").length;
  const attempted = PROBS.filter((p) => status(p.id) !== "new").length;
  const due = PATH.filter((id) => isDue(id)).length;
  lines.push(`LeetStats stats (${dayKey()}; app built ${DATA.built.slice(0, 10)})`);
  lines.push(`Solved ${solved}/${PROBS.length}, attempted ${attempted}, reviews due ${due}, streak ${streak()} days, flashcards reviewed ${Object.keys(S().cards).length}.`);
  const tried = rows.filter((r) => r.submits > 0 || r.peeked > 0);
  const weak = tried.map((r) => ({ ...r, score: (r.accuracy ?? 0) - (r.peekRate ?? 0) / 2 })).sort((a, b) => a.score - b.score).slice(0, 6);
  lines.push("", "Weakest topics (accuracy = passed/total submits; peek = share of attempted problems where I viewed the solution):");
  if (!weak.length) lines.push("- (not enough data yet)");
  for (const r of weak) lines.push(`- ${r.section} / ${r.tag}: accuracy ${pct(r.accuracy)} (${r.passes}/${r.submits}), peek ${pct(r.peekRate)}, solved ${r.solved}/${r.ids.length}, median time ${fmtDur(r.medTime)}`);
  const trouble = PROBS.map((p) => ({ p, x: getP(p.id) })).filter(({ x }) => (x.fails || 0) >= 2 || (x.peeks || 0) >= 1)
    .sort((a, b) => ((b.x.fails || 0) + 2 * (b.x.peeks || 0)) - ((a.x.fails || 0) + 2 * (a.x.peeks || 0))).slice(0, 12);
  lines.push("", "Problems peeked or failed repeatedly:");
  if (!trouble.length) lines.push("- none");
  for (const { p, x } of trouble) lines.push(`- ${p.id} "${p.title}" [${p.section}/${p.tags[0]}]: ${x.fails || 0} failed submits${x.peeks ? `, solution viewed ${x.peeks}x` : ""}${x.solvedAt ? "" : ", not solved yet"}`);
  const full = rows.filter((r) => r.solved === r.ids.length);
  lines.push("", `Topics with nothing left unsolved (${full.length}): ${full.map((r) => `${r.section}/${r.tag}`).join(", ") || "none"}`);
  const untouched = rows.filter((r) => r.attempted === 0);
  lines.push(`Topics not started yet (${untouched.length}): ${untouched.map((r) => `${r.section}/${r.tag}`).join(", ") || "none"}`);
  lines.push("", "Request: add problems that target the weakest topics above (new bricks, not duplicates).");
  return lines.join("\n");
}
async function copyStats() {
  const text = statsText();
  try { await navigator.clipboard.writeText(text); toast("Stats copied. Paste them into Claude with /add-problems"); }
  catch (e) {
    modal(`<h2>Copy my stats for Claude</h2><p class="muted small">Clipboard access was blocked; copy the text below.</p><textarea style="width:100%;height:280px;font:12px var(--mono)" readonly>${esc(text)}</textarea><div class="acts"><button class="btn" data-close>Close</button></div>`);
    const ta = $("#modal-body textarea"); ta.focus(); ta.select();
  }
}

// ===========================================================================
// Menu, theme, export/import, shortcuts
// ===========================================================================
function applyTheme() {
  const t = S().settings.theme;
  if (t === "system") document.documentElement.removeAttribute("data-theme"); else document.documentElement.setAttribute("data-theme", t);
  $("#theme-btn").title = "Theme: " + t + " (click to change)";
  $("#theme-btn").textContent = t === "dark" ? "☾" : t === "light" ? "☀" : "◐";
}
function initMenu() {
  $("#theme-btn").onclick = () => {
    const order = ["system", "light", "dark"], s = S().settings;
    s.theme = order[(order.indexOf(s.theme) + 1) % 3]; Store.save(); applyTheme(); toast("Theme: " + s.theme);
  };
  $("#menu-btn").onclick = (e) => { e.stopPropagation(); $("#menu").hidden = !$("#menu").hidden; };
  document.addEventListener("click", (e) => { if (!e.target.closest(".menu-wrap")) $("#menu").hidden = true; });
  $$("#menu [data-act]").forEach((b) => (b.onclick = () => { $("#menu").hidden = true; menuAct(b.dataset.act); }));
  $("#import-file").onchange = importFile;
  $("#py-pill").onclick = pyDetails;
}
function menuAct(a) {
  if (a === "copy-stats") copyStats();
  else if (a === "export") {
    Store.save(true);
    const blob = new Blob([JSON.stringify({ app: "leetstats", exported: new Date().toISOString(), data: S() }, null, 1)], { type: "application/json" });
    const url = URL.createObjectURL(blob), link = document.createElement("a");
    link.href = url; link.download = `leetstats-progress-${dayKey()}.json`; document.body.appendChild(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000); toast("Progress exported");
  } else if (a === "import") $("#import-file").click();
  else if (a === "shortcuts") {
    modal(`<h2>Keyboard shortcuts</h2><table class="kbd-table">
      <tr><td><kbd>${MOD}</kbd>+<kbd>Enter</kbd></td><td>Run on the example (Playground: run selection or all)</td></tr>
      <tr><td><kbd>${MOD}</kbd>+<kbd>Shift</kbd>+<kbd>Enter</kbd></td><td>Submit to the hidden tests</td></tr>
      <tr><td><kbd>Alt</kbd>+<kbd>N</kbd></td><td>Next problem (also <kbd>N</kbd> after an accepted submit)</td></tr>
      <tr><td><kbd>${MOD}</kbd>+<kbd>/</kbd></td><td>Toggle comment</td></tr>
      <tr><td><kbd>Tab</kbd> / <kbd>Shift</kbd>+<kbd>Tab</kbd></td><td>Indent / dedent (4 spaces)</td></tr>
      <tr><td><kbd>Space</kbd>, <kbd>1</kbd>–<kbd>4</kbd></td><td>Flashcards: show answer, rate Again / Hard / Good / Easy</td></tr>
      <tr><td><kbd>Esc</kbd></td><td>Close dialogs and menus</td></tr></table><div class="acts"><button class="btn" data-close>Close</button></div>`);
  } else if (a === "about") {
    const counts = SECTIONS.map((s) => `${esc(s.title)}: ${PROBS.filter((p) => p.section === s.key).length}`).join(" · ");
    modal(`<h2>About this build</h2><p>${PROBS.length} problems (${counts}); ${ALL_CARDS.length} flashcards; ${DATA.playground.length} playground prompts.</p>
      <p class="small muted">Built ${esc(DATA.built)} · Pyodide ${esc(DATA.pyodide.version)} (seaborn ${esc(DATA.pyodide.seaborn)} via micropip) · progress is stored in this browser under <code>${STORE_KEY}</code>${Store.ok ? "" : " (storage currently unavailable!)"}.</p>
      <div class="acts"><button class="btn" data-close>Close</button></div>`);
  }
}
function importFile(e) {
  const f = e.target.files[0]; e.target.value = "";
  if (!f) return;
  const rd = new FileReader();
  rd.onload = async () => {
    try {
      const obj = JSON.parse(rd.result), data = obj.data || obj;
      if (!data || typeof data !== "object" || !data.problems) throw new Error("not a LeetStats export");
      const n = Object.keys(data.problems).length;
      if (!(await confirmBox("Import progress?", `This replaces the progress in this browser with the file's (${n} problems with history). Export first if unsure.`, "Replace"))) return;
      Store.replace(data); location.reload();
    } catch (err) { toast("Import failed: " + err.message, 4000); }
  };
  rd.readAsText(f);
}
function pyDetails() {
  Py.start();
  const st = Py.st;
  const row = (k) => `<tr><td>${esc(k)}</td><td>${esc(st.pkgs[k] || (k === "numpy" || k === "pandas" ? (st.ready ? "loaded" : "loading") : "pending"))}</td></tr>`;
  modal(`<h2>Python runtime</h2><p class="muted small">Pyodide ${esc(DATA.pyodide.version)} in a Web Worker. NumPy and pandas load first, the rest in the background. LightGBM loads on first import. Runs are limited to 10 s (Playground 60 s); Stop restarts the interpreter.</p>
    <table class="grid">${["numpy", "pandas", ...Py.BG, "lightgbm"].map(row).join("")}</table>
    ${st.error ? `<pre class="out err">${esc(st.error)}</pre>` : ""}
    <div class="acts"><button class="btn" id="py-restart">Restart Python</button><button class="btn primary" data-close>Close</button></div>`, {
    onOpen: (close) => { $("#py-restart").onclick = () => { Py.stop("restart"); close(); toast("Restarting Python…"); }; },
  });
}

// ===========================================================================
// Badges, router, keyboard, init
// ===========================================================================
function updateBadges() {
  const t = now();
  const due = PATH.filter((id) => isDue(id, t)).length;
  $("#badge-review").textContent = due || "";
  const plan = S().today && S().today.date === dayKey() ? S().today : null;
  const left = plan ? plan.due.concat(plan.fresh).filter((id) => !doneToday(id)).length : "";
  $("#badge-today").textContent = left || "";
  const cq = cardQueue("all");
  $("#badge-cards").textContent = cq.due.length || "";
}

const VIEWS = ["problems", "today", "review", "cards", "playground", "mock", "bricks", "stats"];
let activeView = null;
const currentView = () => activeView;
function showView(name) {
  activeView = name;
  VIEWS.forEach((v) => ($("#view-" + v).hidden = v !== name));
  $$("#tabs a").forEach((a) => a.classList.toggle("active", a.dataset.view === name));
  $("#drawer-btn").style.visibility = name === "problems" ? "visible" : "hidden";
  if (name !== "problems") document.body.classList.remove("drawer-open");
}
function route() {
  const h = location.hash.replace(/^#/, "");
  const [name, arg, flag] = h.split("/");
  const v = VIEWS.includes(name) ? name : "problems";
  if (v !== "cards" && v !== "bricks" && v !== "stats" && v !== "review") Py.start();
  if (v === "problems") {
    const id = arg && BY_ID[arg] ? arg : view.id || S().lastProblem || PATH[0];
    const review = arg ? flag === "review" : view.review;
    if (id === view.id && review === view.review) { showView("problems"); renderList(); setTimeout(() => view.editor.refresh(), 0); }
    else openProblem(id, { review });
    return;
  }
  showView(v);
  if (v === "today") renderToday();
  else if (v === "review") renderReview();
  else if (v === "cards") renderCards();
  else if (v === "playground") { if (!pg.loaded) { pg.loaded = true; loadPgDraft(); } renderPlayground(); }
  else if (v === "mock") renderMock();
  else if (v === "bricks") renderBricks();
  else if (v === "stats") renderStats();
  updateBadges();
}

function typingTarget(e) {
  const t = e.target;
  return t && (t.closest && t.closest(".CodeMirror") || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName));
}
document.addEventListener("keydown", (e) => {
  const mod = e.ctrlKey || e.metaKey;
  if (e.key === "Escape") { if (!$("#modal").hidden) { $("#modal").hidden = true; } $$(".menu, .multi-pop").forEach((m) => (m.hidden = true)); document.body.classList.remove("drawer-open"); return; }
  if (!$("#modal").hidden) return;
  if (activeView === "problems") {
    if (mod && e.key === "Enter") { e.preventDefault(); doRun(e.shiftKey ? "submit" : "run"); return; }
    if (e.altKey && e.code === "KeyN") { e.preventDefault(); navigate("next"); return; }
    if (!typingTarget(e) && !mod && !e.altKey && (e.key === "n" || e.key === "N") && view.accepted) { e.preventDefault(); navigate("next"); return; }
  } else if (activeView === "cards" && !typingTarget(e) && !mod) {
    if (e.key === " " || e.key === "Enter") { e.preventDefault(); if (!fc.shown) revealCard(); return; }
    const r = { 1: "again", 2: "hard", 3: "good", 4: "easy" }[e.key]; if (r && fc.shown) { e.preventDefault(); rateCard(r); }
  } else if ((activeView === "playground" || activeView === "mock") && mod && e.key === "Enter" && !typingTarget(e)) {
    e.preventDefault(); activeView === "playground" ? pgRun(pg, "#pg-out") : mk.attempt && pgRun(mk, "#mk-out");
  }
});

function trackNewProblems() {
  const s = S(), ids = PROBS.map((p) => p.id);
  if (!s.knownIds) { s.knownIds = ids; s.newIds = []; }
  else {
    const known = new Set(s.knownIds), present = new Set(ids);
    const added = ids.filter((id) => !known.has(id));
    s.newIds = [...new Set([...(s.newIds || []).filter((id) => present.has(id)), ...added])];
    s.knownIds = [...new Set([...s.knownIds, ...ids])];
  }
  s.lastVisit = now(); Store.save();
}

function init() {
  Store.load();
  applyTheme();
  trackNewProblems();
  initMenu();
  initProblemsView();
  renderList();
  initPlayground();
  window.addEventListener("hashchange", route);
  route();
  updateBadges();
  setInterval(updateBadges, 60e3);
  if (!window.CodeMirror) toast("Editor library could not load (offline?). Using a plain editor.", 4000);
}
init();
window.__leetstats = { Py, Store, BY_ID, schedule };
})();
