"""Browser checks for the panel. All APIs are mocked; no inference or account changes.

Run with an environment containing Playwright and Chromium:
    python scripts/check-ui.py
"""
import copy
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
# HARNESS_UI / HARNESS_EVIDENCE let parallel workers test their own copy.
PAGE = Path(os.environ.get("HARNESS_UI", ROOT / "package/agent-workbench/ui/index.html"))
EVIDENCE = Path(os.environ.get("HARNESS_EVIDENCE", ROOT / "artifacts/ui-evidence"))
EVIDENCE.mkdir(parents=True, exist_ok=True)

BASE = {
    "local": "off", "auth": {"codex": True, "claude": True}, "memory": True,
    "cloud_ready": False, "cloud_provider": "openrouter", "cloud_model": "",
    "providers": {"openrouter": {"has_key": False}, "opencode": {"has_key": False}},
    "projects": {"selected": "/home/user/projects/harness",
                 "projects": ["/home/user/projects/harness", "/home/user/projects/personal-workbench"]},
    "versions": {"omnigent": "0.20.0", "codex": "0.165.0", "claude": "2.1.312", "pi-coding-agent": "1.4.0"},
    "usage": {"checked": 1793210400, "codex": {"windows": [
        {"used": 50, "minutes": 300, "resets": 1793214000},
        {"used": 20, "minutes": 10080, "resets": 1793815200}]},
        "cloud": {"status": "available", "provider": "openrouter", "limit": 50, "remaining": 25}},
    "usage_refreshing": False,
    "jobs": [
        {"id": "one", "title": "Improve project navigation", "role": "codex", "project": "/home/user/projects/harness", "state": "done",
         "started": 1793206800, "answer": "Updated the project navigation and verified the changes.\n\nAll checks passed.",
         "output": "Mock execution log", "url": "http://127.0.0.1:6767/c/" + "a" * 32},
        {"id": "two", "role": "research", "project": "/home/user/projects/personal-workbench",
         "state": "done", "started": 1793203200, "answer": "Research notes are ready for review.",
         "output": "Mock research log", "url": None},
        {"id": "three", "role": "claude", "project": "/home/user/projects/harness",
         "state": "stopped", "started": 1793199600, "output": "", "url": None},
    ],
}
state = copy.deepcopy(BASE)
calls = []
errors = []
layout_metrics = []

def handler(route):
    path = route.request.url.split("127.0.0.1:18787", 1)[1].split("#")[0]
    if path == "/":
        route.fulfill(body=PAGE.read_text(encoding="utf-8").replace("__CSRF_TOKEN__", "test-token"),
                      content_type="text/html")
    elif path == "/api/status":
        route.fulfill(json=state)
    elif path.startswith("/api/"):
        assert route.request.method == "POST"
        assert route.request.headers["x-harness-token"] == "test-token"
        body = route.request.post_data_json
        calls.append((path, body))
        if path == "/api/task-models":
            route.fulfill(json={"models": [{"id": "test-model", "name": "Test Model", "efforts": ["low", "medium", "high"]}]})
        elif path == "/api/run":
            state["jobs"].insert(0, {"id": "new", "role": body["role"], "project": body["project"],
                "state": "running", "started": 1793210400, "output": "Preparing", "url": None})
            route.fulfill(json={"id": "new"})
        elif path == "/api/stop":
            next(j for j in state["jobs"] if j["id"] == body["id"])["state"] = "stopped"
            route.fulfill(json={"message": "Task stopped."})
        else:
            raise AssertionError("Unexpected write: " + path)
    else:
        route.abort()

with sync_playwright() as p:
    browser = p.chromium.launch(args=["--disable-gpu"])
    page = browser.new_page(viewport={"width": 1440, "height": 1000}, timezone_id="America/Los_Angeles")
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.route("**/*", handler)
    page.goto("http://127.0.0.1:18787/")
    expect(page.locator("#taskCount")).to_have_text("2")
    page.locator("#sessionScope").select_option("all")
    expect(page.locator("#taskCount")).to_have_text("3")
    expect(page.locator("#run")).to_be_enabled()
    expect(page.locator("#homeCodex progress").first).to_have_attribute("value", "50")
    assert page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--success').trim()") == "#287343"
    assert "?" not in page.locator(".usage-strip").inner_text()
    assert not page.locator("#homeClaude progress").count()
    page.keyboard.press("Tab")
    expect(page.locator(".skip")).to_be_focused()
    page.keyboard.press("Enter")
    expect(page.locator("#main")).to_be_focused()
    page.locator("#main").evaluate("(el)=>el.blur()")
    page.screenshot(path=str(EVIDENCE / "workspace-desktop.png"), full_page=True, animations="disabled")

    # Search, status filter, expandable answers and preserved expansion during polling.
    page.locator("#sessionSearch").fill("research")
    expect(page.locator(".session")).to_have_count(1)
    page.locator("#sessionSearch").fill("not-present")
    expect(page.get_by_text("No matching sessions", exact=True)).to_be_visible()
    page.get_by_role("button", name="Clear Filters").click()
    expect(page.locator(".session")).to_have_count(3)
    # A title is searchable and a direct session link is visible without expanding.
    page.locator("#sessionSearch").fill("navigation")
    expect(page.locator(".session")).to_have_count(1)
    expect(page.locator(".session-open").first).to_be_visible()
    page.locator("#sessionSearch").fill("")
    page.locator(".session-summary").first.click()
    expect(page.locator(".session-answer").first).to_be_visible()
    page.locator(".session-summary").first.focus()
    state["jobs"][0]["output"] += "\nPolling update"
    page.evaluate("refresh()")
    expect(page.locator(".session").first).to_have_attribute("open", "")
    expect(page.locator(".session-summary").first).to_be_focused()
    page.locator("#sessionFilter").select_option("done")
    expect(page.locator(".session")).to_have_count(2)
    page.locator("#sessionFilter").select_option("all")

    # Missing local/cloud setup has a clear path and cannot submit.
    page.locator("#agent").select_option("local")
    expect(page.locator("#run")).to_be_disabled()
    # Old path: a link to System. New path (UI-FIXES-SPEC C6): an inline start button.
    expect(page.locator("#agentSetup[href='#diagnostics']:visible, #startLocalInline:visible")).to_have_count(1)
    page.locator("#agent").select_option("cloud")
    expect(page.locator("#run")).to_be_disabled()
    page.locator("#agentSetup").click()
    expect(page.locator("#connections")).to_be_visible()
    expect(page).to_have_title("Connections · Harness")
    page.get_by_role("link", name="Workspace", exact=True).click()
    page.locator("#agent").select_option("codex")

    # Drafts and preferences survive reload and are isolated by project.
    page.locator("#prompt").fill("Keep this draft")
    page.locator("#agent").select_option("claude")
    page.reload()
    expect(page.locator("#prompt")).to_have_value("Keep this draft")
    expect(page.locator("#agent")).to_have_value("claude")
    page.locator("#project").select_option(BASE["projects"]["projects"][1])
    expect(page.locator("#prompt")).to_have_value("")
    page.locator("#prompt").fill("Other project draft")
    page.reload()
    expect(page.locator("#project")).to_have_value(BASE["projects"]["projects"][1])
    expect(page.locator("#prompt")).to_have_value("Other project draft")
    page.locator("#project").select_option(BASE["projects"]["selected"])
    expect(page.locator("#prompt")).to_have_value("Keep this draft")
    page.locator("#agent").select_option("codex")

    expect(page.locator("#taskModel")).to_be_enabled()
    page.locator("#taskModel").select_option("test-model")
    page.locator("#taskEffort").select_option("high")
    # Keyboard submission hits only our mock and disables another running task.
    page.locator("#prompt").fill("Review the navigation")
    page.locator("#prompt").press("Control+Enter")
    expect(page.locator("#run")).to_have_text("Task running…")
    assert [c for c in calls if c[0] == "/api/run"] == [
        ("/api/run", {"role": "codex", "project": BASE["projects"]["selected"],
                      "prompt": "Review the navigation", "model": "test-model", "effort": "high"})]
    page.get_by_role("button", name="Stop Task", exact=True).click()
    expect(page.locator("#run")).to_be_enabled()

    # Dialog focus/escape and project changes.
    page.locator("#addProject").click()
    expect(page.locator("#projectDialog")).to_be_visible()
    expect(page.locator("#projectPath")).to_be_focused()
    page.keyboard.press("Escape")
    expect(page.locator("#projectDialog")).not_to_be_visible()
    page.locator("#project").select_option(BASE["projects"]["projects"][1])
    expect(page.locator("#workspaceTitle")).to_have_text("personal-workbench")

    page.locator("#sessionScope").select_option("all")
    page.locator("#toast").evaluate("(el)=>el.hidden=true")
    page.mouse.move(0, 0)
    # Check every screen at phone, tablet, laptop and desktop widths.
    for width in (320, 390, 768, 1024, 1280, 1440):
        page.set_viewport_size({"width": width, "height": 1000})
        for view in ("workspace", "connections", "diagnostics"):
            page.evaluate("(view)=>location.hash=view", view)
            expect(page.locator("#" + view)).to_be_visible()
            if not page.evaluate("document.documentElement.scrollWidth <= innerWidth"):
                page.screenshot(path=str(EVIDENCE / "overflow.png"), full_page=True, animations="disabled")
                print(page.evaluate("Array.from(document.querySelectorAll('body *')).filter(e=>e.checkVisibility()&&e.scrollWidth>e.clientWidth+1).map(e=>[e.tagName,e.id,e.className,e.clientWidth,e.scrollWidth])"));print(page.evaluate("Array.from(document.querySelectorAll('body *')).filter(e=>{let r=e.getBoundingClientRect();return r.width&&r.right>innerWidth+1}).map(e=>[e.tagName,e.id,e.className,e.getBoundingClientRect().width])"))
                raise AssertionError((width, view, "overflow"))
            if view == "workspace":
                top = page.locator(".session-section").evaluate("el=>el.getBoundingClientRect().top+scrollY")
                layout_metrics.append({"width": width, "sessions_top": top})
                if width == 1280:
                    assert top < 950, (width, top)
                if width == 390:
                    assert top < 1400, (width, top)
            page.evaluate("window.scrollTo(0,0); document.activeElement?.blur()")
            if width in (390, 1280, 1440):
                page.screenshot(path=str(EVIDENCE / f"{view}-{width}.png"), full_page=True, animations="disabled")
    state["jobs"] = []
    page.evaluate("location.hash='workspace'; refresh()")
    expect(page.get_by_text("No sessions yet", exact=True)).to_be_visible()
    page.locator("#prompt").fill("")
    page.locator("#prompt").evaluate("(el)=>el.blur()")
    page.set_viewport_size({"width": 390, "height": 900})
    page.screenshot(path=str(EVIDENCE / "workspace-empty-mobile.png"), full_page=True, animations="disabled")
    # Known zero/full quotas and unknown quotas remain distinct.
    state["usage"]["codex"]["windows"][0]["used"] = 100
    state["usage"]["codex"]["windows"][1]["used"] = 0
    page.evaluate("refresh()")
    expect(page.locator("#homeCodex progress").first).to_have_attribute("value", "0")
    expect(page.locator("#homeCodex progress").nth(1)).to_have_attribute("value", "100")
    page.locator("#homeCodex a").focus()
    page.evaluate("refresh()")
    expect(page.locator("#homeCodex a")).to_be_focused()
    state["usage"]["codex"]["windows"] = []
    page.evaluate("refresh()")
    expect(page.locator("#homeCodex progress")).to_have_count(0)
    expect(page.locator("#homeCodex")).to_contain_text("Usage unavailable")

    # A task in another project still explains the global busy state.
    state["jobs"] = [{"id": "cross", "role": "claude", "project": BASE["projects"]["selected"],
                      "state": "running", "started": 1793210400, "output": "", "url": None}]
    page.locator("#sessionScope").select_option("current")
    page.evaluate("refresh()")
    expect(page.locator("#runHint")).to_contain_text("Claude is running in harness")
    page.locator("#agentSetup").click()
    expect(page.locator("#sessionScope")).to_have_value("all")
    expect(page.locator(".session")).to_have_count(1)
    expect(page.locator(".session-summary")).to_be_focused()
    state["jobs"][0]["state"] = "failed"
    page.reload()
    expect(page.locator("#panelStatus")).to_have_text("Connected")
    page.locator("#sessionScope").select_option("all")
    expect(page.locator(".session")).not_to_have_attribute("open", "")
    state["jobs"] = []
    page.evaluate("refresh()")
    page.locator("#sessionFilter").select_option("all")

    # A failed submission keeps the draft and shows a durable inline error.
    page.route("**/api/run", lambda route: route.fulfill(status=409, json={"error": "A task is already running."}))
    page.locator("#prompt").fill("Keep this after a failed submit")
    page.locator("#run").click()
    expect(page.locator("#taskError")).to_have_text("A task is already running.")
    expect(page.locator("#prompt")).to_have_value("Keep this after a failed submit")
    page.reload()
    expect(page.locator("#prompt")).to_have_value("Keep this after a failed submit")

    # Apple-guided recovery and navigation controls.
    state = copy.deepcopy(BASE)
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.reload()
    expect(page.locator("#panelStatus")).to_have_text("Connected")
    page.locator("#toggleSidebar").click()
    expect(page.locator("#sidebar")).not_to_be_visible()
    page.reload()
    expect(page.locator("#toggleSidebar")).to_have_attribute("aria-expanded", "false")
    page.locator("#toggleSidebar").click()
    expect(page.locator("#sidebar")).to_be_visible()
    page.locator("#prompt").fill("Draft to recover")
    page.locator("#clearDraft").click()
    expect(page.locator("#prompt")).to_have_value("")
    page.locator("#undoDraft").click()
    expect(page.locator("#prompt")).to_have_value("Draft to recover")
    page.evaluate("location.hash='diagnostics'")
    page.locator("#gpuToggle").click()
    expect(page.locator("#localDialog")).to_be_visible()
    expect(page.locator("#cancelLocalModel")).to_be_focused()
    page.keyboard.press("Escape")
    expect(page.locator("#localDialog")).not_to_be_visible()
    assert not [c for c in calls if c[0] == "/api/local"]

    page.route("**/api/project",lambda route:route.fulfill(status=400,json={"error":"Choose an existing project folder."}))
    page.evaluate("location.hash='workspace'")
    page.locator("#addProject").click()
    page.locator("#projectPath").fill("/not-a-project")
    page.locator("#saveProject").click()
    expect(page.locator("#projectError")).to_have_text("Choose an existing project folder.")
    expect(page.locator("#projectDialog")).to_be_visible()
    page.keyboard.press("Escape")

    # Contrast checks use resolved browser colors, independent of theme tokens.
    import re
    def luminance(color):
        rgb = [float(n) / 255 for n in re.findall(r"[\d.]+", color)[:3]]
        linear = [n / 12.92 if n <= .04045 else ((n + .055) / 1.055) ** 2.4 for n in rgb]
        return sum(n*w for n,w in zip(linear, [.2126, .7152, .0722]))
    def ratio(a, b):
        x,y=sorted([luminance(a), luminance(b)])
        return (y+.05)/(x+.05)

    for color_scheme in ("light", "dark"):
        for contrast in ("no-preference", "more"):
            page.emulate_media(color_scheme=color_scheme, contrast=contrast, reduced_motion="reduce")
            for width in (390, 1440):
                page.set_viewport_size({"width":width,"height":1000})
                for view in ("workspace","connections","diagnostics"):
                    page.evaluate("(view)=>location.hash=view",view)
                    expect(page.locator("#"+view)).to_be_visible()
                    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), (color_scheme,contrast,width,view)
                page.evaluate("location.hash='workspace'")
                colors=page.locator("#run").evaluate("el=>({fg:getComputedStyle(el).color,bg:getComputedStyle(el).backgroundColor})")
                assert ratio(colors["fg"],colors["bg"]) >= 4.5, colors
                colors=page.evaluate("()=>({fg:getComputedStyle(document.querySelector('.path')).color,bg:getComputedStyle(document.body).backgroundColor})")
                assert ratio(colors["fg"],colors["bg"]) >= 4.5, colors
                assert page.locator("#run").evaluate("el=>getComputedStyle(el).transitionDuration") == "0s"
                page.evaluate("window.scrollTo(0,0);document.activeElement?.blur()")
                page.screenshot(path=str(EVIDENCE/f"apple-{color_scheme}-{contrast}-{width}.png"),full_page=True,animations="disabled")
    # Enlarge all rem-based text to 200% and check every screen.
    page.emulate_media(color_scheme="light",contrast="no-preference")
    page.evaluate("document.documentElement.style.fontSize='200%'")
    for width in (390,1440):
        page.set_viewport_size({"width":width,"height":1000})
        for view in ("workspace","connections","diagnostics"):
            page.evaluate("(view)=>location.hash=view",view)
            expect(page.locator("#"+view)).to_be_visible()
            if not page.evaluate("document.documentElement.scrollWidth<=innerWidth"):
                print(page.evaluate("Array.from(document.querySelectorAll('body *')).filter(e=>e.checkVisibility()&&e.scrollWidth>e.clientWidth+1).map(e=>[e.tagName,e.id,e.className,e.clientWidth,e.scrollWidth])"));print(page.evaluate("Array.from(document.querySelectorAll('body *')).filter(e=>e.checkVisibility()&&e.getBoundingClientRect().right>innerWidth).map(e=>[e.tagName,e.id,e.className,Math.round(e.getBoundingClientRect().width)])"))
                page.screenshot(path=str(EVIDENCE/"apple-text-overflow.png"),full_page=True)
                raise AssertionError(("200% text",width,view))
        page.screenshot(path=str(EVIDENCE/f"apple-large-text-{width}.png"),full_page=True,animations="disabled")
    page.evaluate("document.documentElement.style.fontSize=''")
    page.emulate_media(forced_colors="active")
    page.evaluate("location.hash='workspace'")
    expect(page.locator("#run")).to_be_enabled()
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    page.emulate_media(forced_colors="none",reduced_motion="no-preference")

    # Recoverable disconnect disables writes rather than showing stale readiness.
    page.route("**/api/status", lambda route: route.fulfill(status=503, json={"error": "offline"}))
    page.evaluate("refresh()")
    expect(page.locator("#connectionError")).to_be_visible()
    expect(page.locator("#run")).to_be_disabled()
    expect(page.locator("#gpuToggle")).to_be_disabled()
    assert not errors, errors
    assert all(path != "/api/local" for path, _ in calls), calls
    browser.close()

result = {"browser_errors": errors, "viewports": [320, 390, 768, 1024, 1280, 1440], "layout": layout_metrics,
          "screens": ["workspace", "connections", "diagnostics"],
          "checks": ["search", "filter", "expansion survives refresh", "cloud/local setup",
                     "keyboard submit", "stop task", "project selection", "dialog focus/escape",
                     "no horizontal overflow", "empty state", "disconnect", "no local inference", "quota zero/full/unknown", "task title search", "direct session links", "per-project drafts", "preferences after reload", "focus during polling", "failed submit preserves draft", "keyboard skip navigation", "cross-project running task", "historical failures stay collapsed", "light/dark appearance", "increased contrast", "200% text", "reduced motion", "forced colors", "draft undo", "sidebar preference", "local confirmation cancellation", "inline dialog errors"],
          "writes": "mocked only"}
(EVIDENCE / "checks.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
