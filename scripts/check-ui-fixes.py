"""Acceptance tests for docs/UI-FIXES-SPEC.md. Every API is mocked; nothing starts a model.

Run in an environment with Playwright and Chromium:
    HARNESS_UI=path/to/index.html python scripts/check-ui-fixes.py --only status,composer
Sections: status, composer, sessions, a11y (wave 1, the default) and copy (wave 2).
Exit code 1 when any check fails.
"""
import argparse
import copy
import os
import re
import sys
import time
import traceback
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
PAGE = Path(os.environ.get("HARNESS_UI", ROOT / "package/agent-workbench/ui/index.html"))
EVIDENCE = Path(os.environ.get("HARNESS_EVIDENCE", ROOT / "artifacts/ui-evidence/fixes"))
HOST = "http://127.0.0.1:18788"
H, P = "/home/user/projects/harness", "/home/user/projects/personal-workbench"
NOW = time.time()
expect.set_options(timeout=4000)


def job(id, role="codex", project=H, state="done", age=300, **extra):
    data = {"id": id, "role": role, "project": project, "state": state, "started": NOW - age,
            "output": "Mock log", "url": None}
    data.update(extra)
    return data


def base_state():
    return {
        "local": "off", "auth": {"codex": True, "claude": True}, "memory": True,
        "cloud_ready": False, "cloud_provider": "openrouter", "cloud_model": "",
        "providers": {"openrouter": {"has_key": False}, "opencode": {"has_key": False}},
        "projects": {"selected": H, "projects": [H, P]},
        "versions": {"omnigent": "0.20.0", "codex": "0.165.0"},
        "local_model_file": "", "local_models": [],
        "usage": {"checked": NOW - 60, "codex": {"windows": [
            {"used": 50, "minutes": 300, "resets": NOW + 3600},
            {"used": 20, "minutes": 10080, "resets": NOW + 5 * 86400}]},
            "cloud": {"status": "available", "provider": "openrouter", "limit": 50, "remaining": 25}},
        "usage_refreshing": False,
        "jobs": [
            job("one", title="Improve project navigation", answer="Done.", url="http://127.0.0.1:6767/c/" + "a" * 32),
            job("two", role="research", project=P, age=3 * 3600, answer="Notes."),
            job("three", role="claude", state="stopped", age=10 * 86400),
        ],
    }


REPOS = [{"id": "unsloth/Model-GGUF", "downloads": 6042413, "likes": 5402, "gated": False,
          "updated": "2026-08-20T12:04:25.000Z", "task": "text-generation"},
         {"id": "vendor/Gated-GGUF", "downloads": 1200, "likes": 4, "gated": True, "updated": None, "task": ""}]
FILES = [{"file": "Model-Q4_K_M.gguf", "name": "Model-Q4_K_M", "paths": ["Model-Q4_K_M.gguf"], "sizes": [9e9],
          "size": 9e9, "quant": "Q4_K_M", "fit": "fits", "downloaded": False},
         {"file": "Model-Q6_K.gguf", "name": "Model-Q6_K", "paths": ["Model-Q6_K.gguf"], "sizes": [14e9],
          "size": 14e9, "quant": "Q6_K", "fit": "tight", "downloaded": True},
         {"file": "Q8_0/Model-Q8_0-00001-of-00002.gguf", "name": "Model-Q8_0",
          "paths": ["Q8_0/Model-Q8_0-00001-of-00002.gguf", "Q8_0/Model-Q8_0-00002-of-00002.gguf"],
          "sizes": [9e9, 8e9], "size": 17e9, "quant": "Q8_0", "fit": "too_large", "downloaded": False}]
LOCAL = [{"id": "/home/user/models/Swift-27B-IQ3_S.gguf", "name": "Swift-27B-IQ3_S", "quant": "IQ3_S", "size": 12.1e9, "fit": "fits"},
         {"id": "/home/user/models/Small-Q4_K_M.gguf", "name": "Small-Q4_K_M", "quant": "Q4_K_M", "size": 5e9, "fit": "fits"}]


class Mock:
    """One isolated page with a mocked Harness API."""

    def __init__(self, browser, state=None, width=1440, height=1000, scheme="light"):
        self.state = state or base_state()
        self.calls, self.errors, self.overrides = [], [], {}
        self.status_mode = "ok"  # ok | network | html
        self.context = browser.new_context(viewport={"width": width, "height": height},
                                           timezone_id="America/Los_Angeles", locale="en-US",
                                           color_scheme=scheme, reduced_motion="reduce")
        self.page = self.context.new_page()
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))
        self.page.route("**/*", self.handle)

    def handle(self, route):
        req = route.request
        if not req.url.startswith(HOST):
            return route.abort()
        path = req.url[len(HOST):].split("#")[0]
        if path == "/":
            return route.fulfill(body=PAGE.read_text(encoding="utf-8").replace("__CSRF_TOKEN__", "t"),
                                 content_type="text/html")
        if path in self.overrides:
            if req.method == "POST":
                self.calls.append((path, req.post_data_json or {}))
            return self.overrides[path](route)
        if path == "/api/status":
            if self.status_mode == "network":
                return route.abort()
            if self.status_mode == "html":
                return route.fulfill(status=500, body="<html>down</html>", content_type="text/html")
            return route.fulfill(json=self.state)
        if not path.startswith("/api/") or req.method != "POST":
            return route.abort()
        body = req.post_data_json or {}
        self.calls.append((path, body))
        if path == "/api/task-models":
            return route.fulfill(json={"models": []})
        if path == "/api/run":
            new = job("new", role=body.get("role"), project=body.get("project"), state="running", age=1,
                      title=(body.get("prompt") or "Task").splitlines()[0], output="Starting…")
            self.state["jobs"].insert(0, new)
            return route.fulfill(json={"id": "new"})
        if path == "/api/stop":
            for j in self.state["jobs"]:
                if j["id"] == body.get("id"):
                    j["state"] = "stopped"
            return route.fulfill(json={"message": "Stop requested."})
        if path == "/api/local":
            self.state["local"] = "loading" if body.get("action") == "start" else "off"
            return route.fulfill(json={"message": "Done."})
        if path == "/api/accounts":
            return route.fulfill(json={"message": "Accounts checked."})
        if path == "/api/project":
            return route.fulfill(status=400, json={"error": "Choose an existing project folder."})
        if path == "/api/discover":
            return route.fulfill(json={"models": REPOS})
        if path == "/api/model-files":
            return route.fulfill(json={"files": FILES})
        if path == "/api/download":
            self.state["download"] = {"repo": body["repo"], "file": body["file"], "name": "Model-Q4_K_M", "quant": "Q4_K_M",
                                      "size": 9e9, "done": 3e9, "speed": 50e6, "state": "downloading", "error": ""}
            return route.fulfill(json={"message": "Download started. The local model stays off."})
        if path == "/api/download-cancel":
            self.state["download"]["state"] = "cancelled"
            return route.fulfill(json={"message": "Cancelling download…"})
        if path == "/api/select-local":
            self.state["local_model_file"] = body["model"]
            return route.fulfill(json={"message": "Local model selected. Start it when you are ready."})
        return route.fulfill(status=404, json={"error": "Unexpected " + path})

    def open(self, hash="", connected=True):
        self.page.goto(HOST + "/" + hash)
        if connected:
            expect(self.page.locator("#panelStatus")).to_have_text("Connected")
        return self.page

    def refresh(self):
        return self.page.evaluate("refresh()")

    def local_calls(self):
        return [c for c in self.calls if c[0] == "/api/local"]

    def close(self):
        assert not self.errors, self.errors
        self.context.close()


# ---------- helpers ----------

CONTRAST_JS = """
(() => {
  const rgba = c => { const m = c.match(/[\\d.]+/g) || [0,0,0,0]; return m.map(Number).concat(m.length < 4 ? [1] : []); };
  const lum = c => { const [r,g,b] = rgba(c).slice(0,3).map(v => { v /= 255; return v <= .04045 ? v/12.92 : ((v+.055)/1.055)**2.4; }); return .2126*r + .7152*g + .0722*b; };
  const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => p - q); return (y + .05) / (x + .05); };
  const bg = el => { for (let e = el; e; e = e.parentElement) { const c = getComputedStyle(e).backgroundColor; if (rgba(c)[3] > .5) return c; } return getComputedStyle(document.body).backgroundColor; };
  const token = name => { const p = document.createElement('span'); p.style.color = `var(${name})`; document.body.append(p); const c = getComputedStyle(p).color; p.remove(); return c; };
  return { ratio, bg, token };
})()
"""


def tab_positions(page, selector):
    """Focusable elements under `selector` in tab order, with their positions."""
    return page.evaluate("""(sel) => [...document.querySelectorAll(sel)]
      .filter(e => e.checkVisibility() && !e.disabled && e.tabIndex >= 0 && e.getBoundingClientRect().width)
      .map(e => { const r = e.getBoundingClientRect(); return {id: e.id || e.textContent.trim().slice(0, 20), x: r.left, y: r.top, h: r.height}; })""",
        selector + " :is(a[href],button,input,select,textarea,summary)")


def assert_visual_order(items):
    for a, b in zip(items, items[1:]):
        same_row = abs(a["y"] - b["y"]) < min(a["h"], b["h"]) / 2
        assert (b["x"] > a["x"]) if same_row else (b["y"] > a["y"]), ("tab order differs from visual order", a, b)


def submit(page, text="Run the checks"):
    page.locator("#prompt").fill(text)
    page.locator("#prompt").press("Control+Enter")


# ---------- workstream S: status ----------

def s1_local_states(browser):
    labels = {"off": ("Local model off", "Off"), "loading": ("Local model starting…", "Starting…"),
              "ready": ("Local model ready", "Ready")}
    for local, (summary, system) in labels.items():
        m = Mock(browser); m.state["local"] = local; page = m.open()
        state = {"off": "off", "loading": "starting", "ready": "ready"}[local]
        expect(page.locator("#topGpu")).to_have_attribute("data-state", state)
        expect(page.locator("#gpuSummary")).to_have_text(summary)
        expect(page.locator("#gpuState")).to_have_text(system)
        assert "danger" not in (page.locator("#gpuToggle").get_attribute("class") or ""), local
        expect(page.locator("#gpuToggle")).to_have_text("Start Local Model…" if local == "off" else "Stop Local Model")
        c = page.evaluate(f"{CONTRAST_JS}.token('--danger')")
        assert page.locator("#topGpu").evaluate("e=>getComputedStyle(e).color") != c, ("danger color", local)
        if local != "off":
            ratio = page.evaluate(f"(()=>{{const k={CONTRAST_JS};const e=document.getElementById('topGpu');return k.ratio(getComputedStyle(e).color,k.bg(e))}})()")
            assert ratio >= 4.5, ("top bar status contrast", local, ratio)
        if local == "loading":
            expect(page.locator("#topGpu .gpu-spinner")).to_have_count(1)
            assert page.locator("#topGpu .gpu-spinner").evaluate("e=>getComputedStyle(e).animationName") in ("none", ""), "spinner must stop under reduced motion"
        expect(page.locator("#freeGpu")).to_be_visible() if local != "off" else expect(page.locator("#freeGpu")).to_be_hidden()
        m.close()
    m = Mock(browser); page = m.open()
    m.status_mode = "network"; m.refresh()
    expect(page.locator("#topGpu")).to_have_attribute("data-state", "unknown")
    expect(page.locator("#gpuSummary")).to_have_text("Local model status unknown")
    expect(page.locator("#gpuState")).to_have_text("Unknown")
    expect(page.locator("#freeGpu")).to_be_hidden()
    expect(page.locator("#gpuToggle")).to_be_disabled()
    m.close()


def s2_free_gpu(browser):
    m = Mock(browser); m.state["local"] = "ready"; page = m.open()
    expect(page.locator("#freeGpu")).to_have_text("Free GPU")
    page.locator("#freeGpu").click()
    page.wait_for_function("document.querySelector('#topGpu').dataset.state==='off'")
    assert m.local_calls() == [("/api/local", {"action": "stop"})], m.local_calls()
    m.close()
    m = Mock(browser); m.state["local"] = "ready"
    m.state["jobs"].insert(0, job("loc", role="local", state="running", age=20, title="Local task"))
    page = m.open()
    page.locator("#freeGpu").click()
    expect(page.locator("#freeGpuDialog")).to_be_visible()
    expect(page.locator("#freeGpuDialog h2")).to_have_text("Stop the local model?")
    expect(page.locator("#cancelFreeGpu")).to_be_focused()
    page.keyboard.press("Escape")
    expect(page.locator("#freeGpuDialog")).to_be_hidden()
    assert not m.local_calls()
    page.locator("#freeGpu").click()
    page.locator("#confirmFreeGpu").click()
    page.wait_for_function("document.querySelector('#topGpu').dataset.state==='off'")
    assert m.local_calls() == [("/api/local", {"action": "stop"})], m.local_calls()
    m.close()


def s3_announcements(browser):
    m = Mock(browser); m.state["local"] = "ready"; page = m.open()
    expect(page.locator("#gpuLive")).to_have_attribute("aria-live", "polite")
    expect(page.locator("#gpuLive")).to_have_text("")
    m.state["local"] = "off"; m.refresh()
    expect(page.locator("#gpuLive")).to_have_text("Local model stopped. The GPU is free.")
    m.state["local"] = "loading"; m.refresh()
    m.state["local"] = "ready"; m.refresh()
    expect(page.locator("#gpuLive")).to_have_text("Local model ready.")
    m.close()


def s4_disconnect_banner(browser):
    m = Mock(browser); m.status_mode = "network"; page = m.open(connected=False)
    expect(page.locator("#connectionError")).to_be_visible()
    expect(page.locator("#connectionMessage")).to_have_text("Can’t reach Harness.")
    expect(page.locator("#retryConnection")).to_have_text("Try Again")
    expect(page.locator("#panelStatus")).to_have_text("Disconnected")
    m.status_mode = "ok"
    page.locator("#retryConnection").click()
    expect(page.locator("#panelStatus")).to_have_text("Connected")
    expect(page.locator("#connectionError")).to_be_hidden()
    assert page.locator("#main").get_attribute("data-stale") in (None, "false")
    m.status_mode = "network"; m.refresh()
    expect(page.locator("#connectionMessage")).to_have_text(re.compile(r"^Can’t reach Harness\. Showing information from \d{1,2}:\d{2}\s?[AP]M\.$"))
    expect(page.locator("#main")).to_have_attribute("data-stale", "true")
    assert page.locator(".session").count() > 0, "stale sessions stay visible"
    page.screenshot(path=str(EVIDENCE / "status-stale.png"), full_page=True)
    m.status_mode = "ok"; m.refresh()
    expect(page.locator("#connectionError")).to_be_hidden()
    assert page.locator("#main").get_attribute("data-stale") in (None, "false")
    m.close()


def s5_no_eternal_loading(browser):
    m = Mock(browser); m.status_mode = "html"; page = m.open(connected=False)
    expect(page.locator("#panelStatus")).to_have_text("Disconnected")
    expect(page.locator("#project option")).to_have_text(["Unavailable"])
    expect(page.locator("#homeUsageTime")).to_have_text("Usage unavailable")
    expect(page.locator("#sessions")).to_contain_text("Sessions unavailable")
    expect(page.locator("#sessions")).to_contain_text("Harness isn’t responding.")
    visible = page.locator("#sidebar").inner_text() + page.locator("#workspace").inner_text()
    assert not re.search(r"Loading|Checking", visible), visible
    page.screenshot(path=str(EVIDENCE / "status-never-connected.png"), full_page=True)
    m.close()


def s6_plain_errors(browser):
    cases = [
        (lambda r: r.abort(), "Can’t reach Harness. Check that it’s running, then try again."),
        (lambda r: r.fulfill(status=500, body="<html>oops</html>", content_type="text/html"),
         "Harness sent an unexpected response (HTTP 500). Try again."),
        (lambda r: r.fulfill(status=409, json={"error": "A task is already running."}), "A task is already running."),
        (lambda r: r.fulfill(status=502, json={}), "Request failed (HTTP 502). Try again."),
    ]
    for handler, message in cases:
        m = Mock(browser); page = m.open()
        m.overrides["/api/run"] = handler
        submit(page, "Keep this draft")
        expect(page.locator("#taskError")).to_have_text(message)
        expect(page.locator("#prompt")).to_have_value("Keep this draft")
        m.close()


def s7_completion_signal(browser):
    for final, prefix, said in (("done", "✓ Done · ", "Task finished: Write tests."),
                                ("failed", "Failed · ", "Task failed: Write tests.")):
        m = Mock(browser)
        m.state["jobs"].insert(0, job("w", state="running", age=30, title="Write tests"))
        page = m.open()
        expect(page).to_have_title("Workspace · Harness")
        m.state["jobs"][0]["state"] = final; m.refresh()
        expect(page).to_have_title(prefix + "Workspace · Harness")
        expect(page.locator("#taskLive")).to_have_text(said)
        expect(page.locator("#taskLive")).to_have_attribute("aria-live", "polite")
        page.keyboard.press("Shift")
        expect(page).to_have_title("Workspace · Harness")
        m.close()
    m = Mock(browser); m.state["jobs"].insert(0, job("s", state="running", age=30, title="Stop me"))
    page = m.open(); m.state["jobs"][0]["state"] = "stopped"; m.refresh()
    expect(page).to_have_title("Workspace · Harness")
    m.close()


def s8_live_status(browser):
    m = Mock(browser); page = m.open()
    expect(page.locator(".rail-status")).to_have_attribute("role", "status")
    dot = ".rail-status .dot"
    expect(page.locator(dot)).to_have_attribute("data-connected", "true")
    on = page.locator(dot).evaluate("e=>getComputedStyle(e).backgroundColor")
    m.status_mode = "network"; m.refresh()
    expect(page.locator(dot)).to_have_attribute("data-connected", "false")
    assert page.locator(dot).evaluate("e=>getComputedStyle(e).backgroundColor") != on
    m.close()


# ---------- workstream C: composer ----------

def c1_sign_in(browser):
    m = Mock(browser); m.state["auth"] = {"codex": False, "claude": False}; page = m.open()
    page.locator("#agent").select_option("codex")
    expect(page.locator("#run")).to_be_disabled()
    expect(page.locator("#runHint")).to_have_text("Sign in to Codex to use Codex.")
    expect(page.locator("#agentSetup")).to_have_text("Open Connections")
    expect(page.locator("#agentSetup")).to_have_attribute("href", "#connections")
    expect(page.locator("#checkAuth")).to_have_text("Check Again")
    page.locator("#agent").select_option("claude")
    expect(page.locator("#runHint")).to_have_text("Sign in to Claude to use Claude.")
    page.locator("#checkAuth").click()
    page.wait_for_function("!document.getElementById('checkAuth').disabled")
    assert ("/api/accounts", {}) in m.calls, m.calls
    m.state["auth"] = {"codex": True, "claude": True}; m.refresh()
    expect(page.locator("#run")).to_be_enabled()
    expect(page.locator("#checkAuth")).to_be_hidden()
    m.close()
    m = Mock(browser); m.state["auth"] = {}; page = m.open()
    page.locator("#agent").select_option("claude")
    expect(page.locator("#run")).to_be_enabled()
    m.close()


def c2_hints(browser):
    m = Mock(browser); page = m.open()
    for role, text in (("codex", "Runs with your Codex account."), ("claude", "Runs with your Claude account.")):
        page.locator("#agent").select_option(role)
        expect(page.locator("#runHint")).to_have_text(text)
    assert "signed-in" not in page.content()
    m.close()


def c3_quota_warning(browser):
    def run(windows=None, cloud=None, role="codex"):
        m = Mock(browser)
        if windows is not None:
            m.state["usage"]["codex"]["windows"] = windows
        if cloud is not None:
            m.state["cloud_ready"] = True; m.state["cloud_model"] = "x/y"; m.state["usage"]["cloud"].update(cloud)
        page = m.open(); page.locator("#agent").select_option(role)
        return m, page
    m, page = run([{"used": 100, "minutes": 300, "resets": NOW + 3600}, {"used": 20, "minutes": 10080, "resets": NOW + 5 * 86400}])
    expect(page.locator("#quotaWarning")).to_have_text(re.compile(r"^Codex’s 5-hour allowance is used up\. It resets at .+\.$"))
    expect(page.locator("#quotaWarning")).to_have_attribute("role", "status")
    expect(page.locator("#run")).to_be_enabled()
    m.close()
    m, page = run([{"used": 92, "minutes": 300, "resets": NOW + 3600}, {"used": 20, "minutes": 10080, "resets": NOW + 5 * 86400}])
    expect(page.locator("#quotaWarning")).to_have_text("Codex has 8% of its 5-hour allowance left.")
    page.locator("#agent").select_option("claude")
    expect(page.locator("#quotaWarning")).to_be_hidden()
    m.close()
    m, page = run([{"used": 50, "minutes": 300, "resets": NOW + 3600}, {"used": 100, "minutes": 10080, "resets": NOW + 5 * 86400}])
    expect(page.locator("#quotaWarning")).to_have_text(re.compile(r"^Codex’s weekly allowance is used up\."))
    m.close()
    m, page = run()
    expect(page.locator("#quotaWarning")).to_be_hidden()
    m.close()
    m, page = run(cloud={"remaining": 0, "limit": 50}, role="cloud")
    expect(page.locator("#quotaWarning")).to_have_text("Your OpenRouter spending limit is used up.")
    m.close()
    m, page = run(cloud={"remaining": 4, "limit": 50}, role="cloud")
    expect(page.locator("#quotaWarning")).to_have_text("Your OpenRouter spending limit is almost used up ($4.00 left).")
    m.close()


def c4_no_project(browser):
    m = Mock(browser); m.state["projects"] = {"selected": "", "projects": []}; m.state["jobs"] = []; page = m.open()
    expect(page.locator("#run")).to_be_disabled()
    expect(page.locator("#runHint")).to_have_text("Add a project to start a task.")
    expect(page.locator("#agentSetup")).to_have_text("Add Project…")
    page.locator("#agentSetup").click()
    expect(page.locator("#projectDialog")).to_be_visible()
    assert page.evaluate("location.hash") in ("", "#workspace")
    m.close()


def c5_disconnected(browser):
    m = Mock(browser); page = m.open()
    m.status_mode = "network"; m.refresh()
    expect(page.locator("#runHint")).to_have_text("Start Task is unavailable while Harness is disconnected.")
    expect(page.locator("#agentSetup")).to_be_hidden()
    expect(page.locator("#run")).to_be_disabled()
    m.close()


def c6_local_agent(browser):
    m = Mock(browser); page = m.open()
    page.locator("#agent").select_option("local")
    expect(page.locator("#runHint")).to_have_text("The local model is off.")
    expect(page.locator("#agentSetup")).to_be_hidden()
    expect(page.locator("#startLocalInline")).to_have_text("Start Local Model…")
    page.locator("#startLocalInline").click()
    expect(page.locator("#localDialog")).to_be_visible()
    page.keyboard.press("Escape")
    assert not m.local_calls(), m.local_calls()
    m.state["local"] = "loading"; m.refresh()
    expect(page.locator("#runHint")).to_have_text("The local model is starting. This can take a minute.")
    expect(page.locator("#startLocalInline")).to_be_hidden()
    expect(page.locator("#run")).to_be_disabled()
    m.state["local"] = "ready"; m.refresh()
    expect(page.locator("#runHint")).to_have_text("Runs on this computer’s GPU.")
    expect(page.locator("#run")).to_be_enabled()
    m.close()


def c7_busy(browser):
    m = Mock(browser); m.state["jobs"].insert(0, job("busy", role="claude", state="running", age=40, title="Busy"))
    page = m.open()
    page.locator("#agent").select_option("codex")
    expect(page.locator("#run")).to_have_text("Task running…")
    expect(page.locator("#run")).to_be_disabled()
    expect(page.locator("#runHint")).to_have_text("Claude is running in harness. Start another task when it finishes.")
    expect(page.locator("#prompt")).to_be_editable()
    expect(page.locator("#agentSetup")).to_have_text("View Task")
    m.close()


def c8_hosted_not_ready(browser):
    m = Mock(browser); page = m.open()
    page.locator("#agent").select_option("cloud")
    expect(page.locator("#runHint")).to_have_text("Connect a hosted model in Connections first.")
    expect(page.locator("#agentSetup")).to_have_text("Open Connections")
    m.close()


def c9_model_controls_untouched(browser):
    m = Mock(browser); page = m.open()
    for sel in ("#taskModel", "#taskEffort", "#reloadTaskModels", "#applyLocalModel", "#taskModelHint", "#effortHint"):
        assert page.locator(".model-controls " + sel).count() == 1, sel
    expect(page.locator("#reloadTaskModels")).to_have_text("Refresh models")
    assert page.evaluate("document.querySelector('.model-controls').compareDocumentPosition(document.querySelector('.composer-bar')) & Node.DOCUMENT_POSITION_FOLLOWING")
    m.close()


# ---------- workstream D: sessions ----------

def d1_open_link(browser):
    m = Mock(browser); page = m.open()
    assert page.locator("summary a, summary button").count() == 0, "interactive content inside summary"
    expect(page.locator(".session-row")).to_have_count(2)
    expect(page.locator(".session-open")).to_have_count(1)
    link = page.get_by_role("link", name="Open Improve project navigation session in a new tab")
    expect(link).to_be_visible()
    assert page.locator('.session-row[data-id="one"] details.session').get_attribute("open") is None
    assert link.evaluate("e=>!e.closest('details')"), "open link must sit outside the details element"
    assert "Open Session" not in page.locator("#sessions").inner_text()
    m.close()


def d2_meta_line(browser):
    m = Mock(browser); page = m.open()
    meta = page.locator('.session-row[data-id="one"] .session-project')
    expect(meta).to_contain_text("Codex")
    assert "harness" not in meta.inner_text(), meta.inner_text()
    page.locator("#sessionScope").select_option("all")
    expect(page.locator('.session-row[data-id="two"] .session-project')).to_contain_text("personal-workbench")
    m.close()


def d3_relative_time(browser):
    for width in (1440, 1024, 390):
        m = Mock(browser, width=width); page = m.open()
        page.locator("#sessionScope").select_option("all")
        times = {i: page.locator(f'.session-row[data-id="{i}"] .session-time') for i in ("one", "two", "three")}
        expect(times["one"]).to_have_text("5 min ago")
        expect(times["two"]).to_have_text("3 hr ago")
        expect(times["three"]).to_have_text(re.compile(r"^[A-Z][a-z]{2} \d{1,2}$"))
        for t in times.values():
            expect(t).to_be_visible()
            assert t.get_attribute("datetime") and t.get_attribute("title")
        assert page.locator(".session-columns").count() == 0
        m.close()


def d4_group_repeats(browser):
    s = base_state()
    s["jobs"] = [job(f"h{i}", role="doctor", state="failed", age=60 * (i + 1), title="Health check") for i in range(3)] + \
                [job("ok", title="Something else", age=900, answer="Fine.")]
    m = Mock(browser, s); page = m.open()
    expect(page.locator(".session-row")).to_have_count(2)
    expect(page.locator(".session-repeat")).to_have_text("×3")
    expect(page.locator(".session-repeat")).to_have_attribute("aria-label", "3 times")
    expect(page.locator("#taskCount")).to_have_text("4")
    m.close()


def d5_show_more(browser):
    s = base_state(); s["jobs"] = [job(f"j{i}", title=f"Task {i}", age=60 * i + 60, answer="ok") for i in range(30)]
    m = Mock(browser, s); page = m.open()
    expect(page.locator(".session-row")).to_have_count(12)
    expect(page.locator("#showMoreSessions")).to_have_text("Show 12 More")
    page.locator("#showMoreSessions").click()
    expect(page.locator(".session-row")).to_have_count(24)
    expect(page.locator("#showMoreSessions")).to_have_text("Show 6 More")
    page.locator("#showMoreSessions").click()
    expect(page.locator(".session-row")).to_have_count(30)
    expect(page.locator("#showMoreSessions")).to_have_count(0)
    page.locator("#sessionFilter").select_option("done")
    expect(page.locator(".session-row")).to_have_count(12)
    m.close()


def d6_running_row(browser):
    m = Mock(browser)
    m.state["jobs"].insert(0, job("run", state="running", age=125, title="Long task", output="Starting…\nReading files…\n"))
    page = m.open()
    answer = page.locator('.session-row[data-id="run"] .session-answer')
    expect(answer).to_contain_text(re.compile(r"Running · 2 min \d+ s"))
    expect(answer).to_contain_text("Reading files…")
    assert "Preparing the session" not in answer.inner_text()
    progress = page.locator('.session-row[data-id="run"] progress.session-progress')
    expect(progress).to_have_count(1)
    expect(progress).to_have_attribute("aria-label", "Task in progress")
    assert progress.evaluate("e=>e.position") == -1, "progress must be indeterminate"
    first = page.locator('.session-row[data-id="run"] [data-elapsed]').inner_text()
    page.wait_for_timeout(2200)
    assert page.locator('.session-row[data-id="run"] [data-elapsed]').inner_text() != first, "elapsed time must tick"
    page.screenshot(path=str(EVIDENCE / "sessions-running.png"), full_page=True)
    m.close()


def d7_plain_results(browser):
    s = base_state()
    s["jobs"] = [job("f", state="failed", age=60, title="Fails", output="Error: gateway MainPID 0 not reachable on :4000"),
                 job("s", state="stopped", age=120, title="Stopped one"),
                 job("i", state="interrupted", age=180, title="Interrupted one"),
                 job("d", state="done", age=240, title="No reply")]
    m = Mock(browser, s); page = m.open()
    for i, text in (("f", "The task didn’t finish. Open Execution Log for details."), ("s", "You stopped this task."),
                    ("i", "Harness closed before this task finished."),
                    ("d", "The task finished, but no reply was captured. Open the session to review it.")):
        expect(page.locator(f'.session-row[data-id="{i}"] .session-answer')).to_have_text(text)
    row = page.locator('.session-row[data-id="f"]')
    assert "MainPID" not in row.locator(".session-answer").inner_text()
    expect(row.locator(".raw-details > summary")).to_have_text("Execution Log")
    assert "MainPID" in row.locator(".output").text_content()
    m.close()


def d8_focus_after_stop(browser):
    m = Mock(browser); m.state["jobs"].insert(0, job("r1", state="running", age=30, title="Stop target"))
    page = m.open()
    page.locator("#stop-r1").focus()
    page.keyboard.press("Enter")
    page.wait_for_function("!document.getElementById('stop-r1')")
    page.wait_for_timeout(300)
    focused = page.evaluate("(()=>{const a=document.activeElement;return {tag:a.tagName,summary:a.matches('.session-summary'),id:a.closest('[data-id]')?.dataset.id||null,prompt:a.id==='prompt'}})()")
    assert focused["summary"] and focused["id"] == "r1" or focused["prompt"], focused
    m.close()


def d9_empty_states(browser):
    s = base_state(); s["jobs"] = [job("p", project=P, title="Elsewhere", answer="ok")]
    m = Mock(browser, s); page = m.open()
    expect(page.locator("#sessions .empty strong")).to_have_text("No sessions in this project")
    expect(page.locator("#sessions .empty p")).to_have_text("Start a task above, or show sessions from all projects.")
    page.get_by_role("button", name="Show All Projects").click()
    expect(page.locator("#sessionScope")).to_have_value("all")
    expect(page.locator(".session-row")).to_have_count(1)
    m.state["jobs"] = []; m.refresh()
    expect(page.locator("#sessions .empty strong")).to_have_text("No sessions yet")
    m.close()


def d10_tool_order(browser):
    m = Mock(browser, width=390, height=900); page = m.open()
    assert_visual_order(tab_positions(page, ".session-tools"))
    m.close()


# ---------- workstream A: accessibility ----------

FIELDS = {"workspace": [".composer", "#agent", "#project", "#sessionScope", "#sessionSearch", "#sessionFilter"],
          "connections": ["#provider", "#apiKey", "#model"]}


def a1_field_borders(browser):
    for scheme in ("light", "dark"):
        m = Mock(browser, scheme=scheme); page = m.open()
        for view, selectors in FIELDS.items():
            page.evaluate("v=>location.hash=v", view)
            for sel in selectors:
                r = page.evaluate(f"""(sel)=>{{const k={CONTRAST_JS};const e=document.querySelector(sel);const s=getComputedStyle(e);
                    if(parseFloat(s.borderTopWidth)<1)return {{own:0,parent:0}};
                    return {{own:k.ratio(s.borderTopColor,k.bg(e)),parent:k.ratio(s.borderTopColor,k.bg(e.parentElement))}}}}""", sel)
                assert min(r["own"], r["parent"]) >= 3, (scheme, sel, r)
        m.close()


def a2_hover_contrast(browser):
    for scheme in ("light", "dark"):
        m = Mock(browser, scheme=scheme); page = m.open()
        for view in ("workspace", "models", "connections", "diagnostics"):
            page.evaluate("v=>location.hash=v", view)
            targets = page.locator(f"#sidebar :is(button,a):visible, #{view} :is(button,a):visible")
            for i in range(targets.count()):
                t = targets.nth(i)
                if t.is_disabled():
                    continue
                t.hover()
                ratio = t.evaluate(f"e=>{{const k={CONTRAST_JS};return k.ratio(getComputedStyle(e).color,k.bg(e))}}")
                assert ratio >= 4.5, (scheme, view, t.evaluate("e=>e.id||e.textContent.trim()"), round(ratio, 2))
        page.mouse.move(0, 0)
        m.close()


def a3_low_quota(browser):
    m = Mock(browser); m.state["usage"]["codex"]["windows"][0]["used"] = 92; page = m.open()
    line = page.locator("#homeCodex .usage-line").first
    expect(line).to_contain_text("8% left · Low")
    assert "Low" in line.locator("progress").get_attribute("aria-valuetext")
    expect(page.locator("#homeCodex .usage-line").nth(1)).not_to_contain_text("Low")
    m.close()


def a4_dialog_errors(browser):
    m = Mock(browser); page = m.open()
    page.locator("#addProject").click()
    page.locator("#projectPath").fill("/not-a-project")
    page.locator("#saveProject").click()
    expect(page.locator("#projectError")).to_have_text("Choose an existing project folder.")
    expect(page.locator("#projectPath")).to_be_focused()
    expect(page.locator("#projectPath")).to_have_attribute("aria-invalid", "true")
    assert "projectError" in (page.locator("#projectPath").get_attribute("aria-describedby") or "")
    page.locator("#projectPath").press("End"); page.locator("#projectPath").type("x")
    assert page.locator("#projectPath").get_attribute("aria-invalid") in (None, "false")
    page.mouse.click(4, 4)
    expect(page.locator("#projectDialog")).to_be_hidden()
    page.evaluate("location.hash='diagnostics'")
    page.locator("#gpuToggle").click()
    expect(page.locator("#cancelLocalModel")).to_be_focused()
    page.mouse.click(4, 4)
    expect(page.locator("#localDialog")).to_be_hidden()
    page.locator("#gpuToggle").click(); page.keyboard.press("Escape")
    expect(page.locator("#gpuToggle")).to_be_focused()
    assert not m.local_calls(), m.local_calls()
    m.close()


def a5_error_toast(browser):
    m = Mock(browser); page = m.open("#connections")
    m.overrides["/api/accounts"] = lambda r: r.fulfill(status=500, json={"error": "Account check failed."})
    page.locator("#refreshAccounts").click()
    expect(page.locator("#toast")).to_contain_text("Account check failed.")
    expect(page.locator("#toastClose")).to_have_text("Close")
    page.wait_for_timeout(7600)
    expect(page.locator("#toast")).to_be_visible()
    page.locator("#toastClose").click()
    expect(page.locator("#toast")).to_be_hidden()
    m.close()


def a6_reflow_200(browser):
    for width in (768, 1440):
        m = Mock(browser, width=width); page = m.open()
        page.evaluate("document.documentElement.style.fontSize='200%'")
        rail = page.locator("#sidebar").evaluate("e=>e.getBoundingClientRect().width")
        assert rail <= 0.4 * width, (width, rail)
        for sel in (".nav a", "h1"):
            assert page.locator(sel).first.evaluate("e=>getComputedStyle(e).overflowWrap") != "anywhere", sel
        for view in ("workspace", "connections", "diagnostics"):
            page.evaluate("v=>location.hash=v", view)
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), (width, view)
        page.evaluate("location.hash='workspace'")
        page.screenshot(path=str(EVIDENCE / f"a11y-text200-{width}.png"), full_page=True)
        m.close()


def a7_rail_order(browser):
    m = Mock(browser, width=390, height=900); page = m.open()
    assert_visual_order(tab_positions(page, "#sidebar"))
    rects = page.locator(".nav a").evaluate_all("es=>es.map(e=>e.getBoundingClientRect()).map(r=>({l:r.left,r:r.right,t:r.top}))")
    for a, b in zip(rects, rects[1:]):
        if abs(a["t"] - b["t"]) < 4:
            assert b["l"] - a["r"] >= 8, ("nav gap", a, b)
    m.close()


# ---------- workstream W: words, header and docs (wave 2) ----------

def visible_text(page):
    texts = []
    for view in ("workspace", "connections", "diagnostics"):
        page.evaluate("v=>location.hash=v", view)
        texts.append(page.locator("body").inner_text())
    page.evaluate("location.hash='workspace'")
    return "\n".join(texts)


def w1_vocabulary(browser):
    m = Mock(browser); page = m.open()
    text = visible_text(page) + " ".join(page.locator("#agent option").all_text_contents())
    for banned in ("Workbench", "Cloud Model", "Can’t connect", "signed-in", "Diagnostics"):
        assert banned not in text, banned
    expect(page.locator('#agent option[value="cloud"]')).to_have_text("Hosted Model")
    expect(page.locator('.nav a[data-view="diagnostics"]')).to_have_text("System")
    m.close()


def w2_header(browser):
    m = Mock(browser); page = m.open()
    expect(page.locator("#workspaceTitle")).to_have_text("harness")
    expect(page.locator("#projectPathDisplay")).to_have_text(H)
    expect(page.locator("#projectName")).to_have_count(0)
    expect(page.locator(".topbar")).not_to_contain_text("/")
    expect(page.locator("#viewCrumb")).to_have_text("Workspace")
    page.locator("#project").select_option(P)
    expect(page.locator("#workspaceTitle")).to_have_text("personal-workbench")
    expect(page).to_have_title("Workspace · Harness")
    page.evaluate("location.hash='connections'")
    expect(page.locator("#viewCrumb")).to_have_text("Connections")
    m.close()
    s = base_state(); s["projects"] = {"selected": "", "projects": []}; s["jobs"] = []
    m = Mock(browser, s); page = m.open()
    expect(page.locator("#workspaceTitle")).to_have_text("No Project")
    m.close()


def w3_labels(browser):
    m = Mock(browser); page = m.open()
    expect(page.locator("#addProject")).to_have_text("Add Project…")
    page.locator("#addProject").click()
    expect(page.locator('label[for="projectId"]')).to_have_text("Project ID (Optional)")
    page.keyboard.press("Escape")
    page.evaluate("location.hash='connections'")
    expect(page.locator("#saveProvider")).to_be_disabled()
    page.locator("#apiKey").fill("sk-test")
    expect(page.locator("#saveProvider")).to_be_enabled()
    m.close()


def w4_usage_strip(browser):
    m = Mock(browser); page = m.open()
    expect(page.locator("#homeCloud")).to_contain_text("$25.00 left of $50.00")
    expect(page.locator("#homeClaude a")).to_have_count(1)
    weekly = page.locator("#homeCodex .usage-line").nth(1)
    expect(weekly).to_contain_text(re.compile(r"Resets [A-Z][a-z]{2}, [A-Z][a-z]{2} \d{1,2}"))
    m.close()
    s = base_state(); s["usage"] = {"checked": None, "codex": {"windows": []}, "cloud": None}
    m = Mock(browser, s); page = m.open()
    expect(page.locator(".usage-unknown")).to_have_count(0)
    strip = page.locator(".usage-strip").inner_text()
    assert strip.lower().count("unavailable") <= 1, strip
    m.close()


def w5_dead_markup(browser):
    m = Mock(browser); page = m.open("#diagnostics")
    expect(page.locator(".rail-caption")).to_have_count(0)
    expect(page.locator(".rail-bottom p")).to_have_count(0)
    expect(page.locator("#diagnostics")).not_to_contain_text("Team tasks use cloud models.")
    m.close()


def w6_docs_in_sync(browser):
    stale = ["Turn on local model", "Turn off · free GPU now", "Diagnostics", "Start task", "Cloud Model"]
    for doc in ("docs/START-HERE.md", "docs/DAILY-WORKFLOW.md"):
        text = (ROOT / doc).read_text(encoding="utf-8")
        found = [s for s in stale if s in text]
        assert not found, (doc, found)


# ---------- workstream M: models and Claude ----------

def m1_claude_is_one_agent(browser):
    m = Mock(browser)
    m.context.add_init_script("localStorage.setItem('harness.agent','research')")
    page = m.open()
    options = page.locator("#agent option").evaluate_all("o=>o.map(x=>x.value)")
    assert options == ["codex", "claude", "cloud", "local"], options
    expect(page.locator("#agent")).to_have_value("claude")
    # Old Team/Research sessions still read naturally in history.
    page.locator("#sessionScope").select_option("all")
    expect(page.locator('.session[data-id="two"] .session-summary')).to_contain_text("Research")
    m.close()
    m = Mock(browser); m.overrides["/api/task-models"] = lambda route: route.fulfill(json={"models": [
        {"id": "claude-opus-5-5", "name": "Claude Opus 5.5", "efforts": ["low", "medium", "high", "xhigh", "max"]}]})
    page = m.open(); page.locator("#agent").select_option("claude")
    page.locator("#taskModel").select_option("claude-opus-5-5")
    efforts = page.locator("#taskEffort option").evaluate_all("o=>o.map(x=>x.textContent)")
    assert efforts == ["Default", "Low", "Medium", "High", "Extra high", "Maximum"], efforts
    page.locator("#taskEffort").select_option("max")
    submit(page)
    run = [c for c in m.calls if c[0] == "/api/run"][-1][1]
    assert (run["role"], run["model"], run["effort"]) == ("claude", "claude-opus-5-5", "max"), run
    m.close()


def m2_claude_usage(browser):
    s = base_state()
    s["usage"]["claude"] = {"status": "available", "windows": [
        {"bucket": "five_hour", "label": "", "used": 56, "minutes": 300, "resets": NOW + 3600},
        {"bucket": "seven_day", "label": "", "used": 16, "minutes": 10080, "resets": NOW + 4 * 86400}]}
    m = Mock(browser, s); page = m.open()
    expect(page.locator("#homeClaude .usage-line")).to_have_count(2)
    expect(page.locator("#homeClaude .usage-line").first).to_contain_text("5-hour")
    expect(page.locator("#homeClaude .usage-line").first).to_contain_text("44% left")
    expect(page.locator("#homeClaude .usage-line").nth(1)).to_contain_text("84% left")
    expect(page.locator("#homeClaude")).not_to_contain_text("Team")
    m.state["usage"]["claude"]["windows"][0]["used"] = 100; m.refresh()
    page.locator("#agent").select_option("claude")
    expect(page.locator("#quotaWarning")).to_contain_text("Claude’s 5-hour allowance is used up.")
    m.close()
    s = base_state(); s["usage"]["claude"] = {"status": "expired"}
    m = Mock(browser, s); page = m.open()
    expect(page.locator("#homeClaude")).to_contain_text("Shows again after your next Claude task.")
    m.close()


def m3_library(browser):
    s = base_state(); s["local_models"] = LOCAL; s["local_model_file"] = LOCAL[0]["id"]
    m = Mock(browser, s); page = m.open("#models")
    expect(page).to_have_title("Models · Harness")
    expect(page.locator("#libraryCount")).to_have_text("2")
    rows = page.locator("#libraryList .model-row")
    expect(rows.first).to_contain_text("In use")
    expect(rows.first).to_contain_text("IQ3_S · 12.1 GB")
    expect(rows.first.locator("button")).to_be_disabled()
    rows.nth(1).get_by_role("button", name="Use Small-Q4_K_M").click()
    expect(page.locator("#toastMessage")).to_have_text("Local model selected. Start it when you are ready.")
    assert ("/api/select-local", {"model": LOCAL[1]["id"]}) in m.calls, m.calls
    expect(rows.nth(1)).to_contain_text("In use")
    m.state["local"] = "ready"; m.refresh()
    expect(page.locator("#libraryHint")).to_contain_text("Stop the local model")
    expect(rows.first.locator("button")).to_be_disabled()
    assert not m.local_calls(), m.local_calls()
    m.close()
    m = Mock(browser); page = m.open("#models")
    expect(page.locator("#libraryList")).to_contain_text("No models downloaded yet")
    assert not [c for c in m.calls if c[0] == "/api/discover"], "Discover searched before it was opened"
    page.get_by_role("button", name="Discover Models").click()
    expect(page.locator("#discoverQuery")).to_be_focused()
    m.close()


def m4_discover_and_download(browser):
    s = base_state(); s["local_models"] = LOCAL
    m = Mock(browser, s); page = m.open("#models")
    page.get_by_role("tab", name="Discover").click()
    expect(page.locator("#tabDiscover")).to_have_attribute("aria-selected", "true")
    expect(page.locator("#discoverHint")).to_have_text("Most downloaded GGUF models on Hugging Face.")
    assert ("/api/discover", {"query": ""}) in m.calls, m.calls
    page.locator("#discoverQuery").fill("model")
    page.locator("#discoverQuery").press("Enter")
    expect(page.locator("#discoverHint")).to_contain_text("2 results for “model”")
    expect(page.locator("#repoList .repo").nth(1)).to_contain_text("Gated")
    page.locator("#repoList .repo").first.click()
    expect(page.locator("#repoList .repo").first).to_have_attribute("aria-pressed", "true")
    assert ("/api/model-files", {"repo": "unsloth/Model-GGUF"}) in m.calls, m.calls
    rows = page.locator("#repoDetail .model-row")
    expect(rows).to_have_count(3)
    expect(rows.nth(0)).to_contain_text("Fits GPU")
    expect(rows.nth(1)).to_contain_text("Tight fit")
    expect(rows.nth(2)).to_contain_text("17.0 GB · 2 parts")
    expect(rows.nth(2)).to_contain_text("Too large for GPU")
    expect(rows.nth(1).locator("button")).to_have_text("Downloaded")
    expect(rows.nth(1).locator("button")).to_be_disabled()
    expect(page.locator("#repoDetail a")).to_have_attribute("href", "https://huggingface.co/unsloth/Model-GGUF")
    rows.nth(0).locator("button").click()
    assert ("/api/download", {"repo": "unsloth/Model-GGUF", "file": "Model-Q4_K_M.gguf"}) in m.calls, m.calls
    expect(page.locator("#downloadPanel")).to_be_visible()
    expect(page.locator("#downloadName")).to_have_text("Downloading Model-Q4_K_M")
    expect(page.locator("#downloadText")).to_contain_text("3.0 GB of 9.0 GB · 50.0 MB/s · about 2 min left")
    expect(rows.nth(2).locator("button")).to_be_disabled()
    page.screenshot(path=str(EVIDENCE / "models-download.png"), full_page=True, animations="disabled")
    m.state["download"].update(state="failed", error="Download interrupted. Try again to resume it."); m.refresh()
    expect(page.locator("#downloadAction")).to_have_text("Retry")
    expect(page.locator("#downloadText")).to_contain_text("Progress is kept.")
    m.state["download"].update(state="downloading"); m.refresh()
    page.locator("#downloadAction").click()
    assert ("/api/download-cancel", {}) in m.calls, m.calls
    expect(page.locator("#downloadPanel")).to_be_hidden()
    page.locator("#repoList .repo").nth(1).click()
    expect(page.locator("#repoDetail")).to_contain_text("requires accepting its terms")
    expect(page.locator("#repoDetail .model-row button").first).to_be_disabled()
    assert not m.local_calls(), m.local_calls()
    m.close()


def m5_models_layout(browser):
    for width, scheme in ((390, "light"), (1024, "dark")):
        s = base_state(); s["local_models"] = LOCAL
        m = Mock(browser, s, width=width, scheme=scheme); page = m.open("#models")
        page.get_by_role("tab", name="Discover").click()
        page.locator("#repoList .repo").first.click()
        expect(page.locator("#repoDetail .model-row")).to_have_count(3)
        overflow = page.evaluate("document.documentElement.scrollWidth-document.documentElement.clientWidth")
        assert overflow <= 0, (width, overflow)
        page.screenshot(path=str(EVIDENCE / f"models-{width}-{scheme}.png"), full_page=True, animations="disabled")
        page.locator("#tabDiscover").focus(); page.keyboard.press("ArrowLeft")
        expect(page.locator("#tabLibrary")).to_be_focused()
        expect(page.locator("#library")).to_be_visible()
        m.close()


SECTIONS = {
    "status": [s1_local_states, s2_free_gpu, s3_announcements, s4_disconnect_banner, s5_no_eternal_loading,
               s6_plain_errors, s7_completion_signal, s8_live_status],
    "composer": [c1_sign_in, c2_hints, c3_quota_warning, c4_no_project, c5_disconnected, c6_local_agent, c7_busy,
                 c8_hosted_not_ready, c9_model_controls_untouched],
    "sessions": [d1_open_link, d2_meta_line, d3_relative_time, d4_group_repeats, d5_show_more, d6_running_row,
                 d7_plain_results, d8_focus_after_stop, d9_empty_states, d10_tool_order],
    "a11y": [a1_field_borders, a2_hover_contrast, a3_low_quota, a4_dialog_errors, a5_error_toast, a6_reflow_200,
             a7_rail_order],
    "copy": [w1_vocabulary, w2_header, w3_labels, w4_usage_strip, w5_dead_markup, w6_docs_in_sync],
    "models": [m1_claude_is_one_agent, m2_claude_usage, m3_library, m4_discover_and_download, m5_models_layout],
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", default="status,composer,sessions,a11y")
    parser.add_argument("-k", default="", help="run only checks whose name contains this text")
    parser.add_argument("-v", action="store_true", help="print full failure details")
    args = parser.parse_args()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--disable-gpu"])
        for section in args.only.split(","):
            for check in SECTIONS[section]:
                if args.k and args.k not in check.__name__:
                    continue
                try:
                    check(browser)
                    results.append((section, check.__name__, None))
                    print(f"PASS {section}.{check.__name__}", flush=True)
                except Exception as error:
                    detail = "".join(traceback.format_exception_only(type(error), error)).strip()
                    results.append((section, check.__name__, detail))
                    lines = [l.strip() for l in detail.splitlines() if l.strip()]
                    brief = " | ".join(l for l in lines if not l.startswith(("Call log", "-", "Aria snapshot")))[:400]
                    print(f"FAIL {section}.{check.__name__}: {detail if args.v else brief}", flush=True)
        browser.close()
    failed = [r for r in results if r[2]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
