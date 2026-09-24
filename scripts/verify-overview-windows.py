"""Read-only acceptance for the installed overview using existing local XDR data."""
import json
import os
import re
import subprocess
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


local = Path(os.environ["LOCALAPPDATA"])
build = local / "SentinelBuild"
output = build / "overview-installed-review"
output.mkdir(exist_ok=True)
exe = local / "Programs" / "DoublePupil" / "DoublePupil.exe"
env = dict(
    os.environ,
    SXF_WORKBENCH_PROFILE=str(build / "overview-installed-profile"),
)
process = subprocess.Popen(
    [str(exe), "--remote-debugging-port=9237"],
    env=env,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)

try:
    with sync_playwright() as playwright:
        for _ in range(100):
            try:
                browser = playwright.chromium.connect_over_cdp(
                    "http://127.0.0.1:9237", timeout=1_000
                )
                break
            except Exception:
                time.sleep(0.3)
        else:
            raise RuntimeError("Installed desktop did not expose its review endpoint")

        context = browser.contexts[0]
        page = (
            context.pages[0]
            if context.pages
            else context.wait_for_event("page", timeout=30_000)
        )
        page.set_default_timeout(30_000)
        expect(page.get_by_role("heading", name="安全态势总览")).to_be_visible()
        expect(page.get_by_label("工作区状态")).to_contain_text("服务正常")
        expect(page.get_by_label("工作区状态")).to_contain_text("XDR 实时")
        dashboard = page.evaluate("window.desktop.request('/dashboard')")
        categories = [row["name"] for row in dashboard["types"]]
        assert categories
        assert all(not re.fullmatch(r"\d+", name) for name in categories)
        assert page.locator(".overview-metric").count() == 4
        assert page.locator(".risk-ring").count() == 1

        page.get_by_label("外观主题").select_option("light")
        page.screenshot(path=str(output / "installed-overview-light.png"))
        page.get_by_label("外观主题").select_option("dark")
        page.screenshot(path=str(output / "installed-overview-dark.png"))

        assert page.get_by_role("button", name="调查画布", exact=True).count() == 0
        page.get_by_role("button", name="思维链", exact=True).click()
        expect(page.get_by_role("heading", name="调查思维链", exact=True)).to_be_visible()
        expect(page.get_by_label("选择调查")).not_to_have_value("")
        expect(page.get_by_role("heading", name="调查执行过程", exact=True)).to_be_visible()
        expect(page.locator(".chain-node").first).to_be_visible()
        page.screenshot(path=str(output / "installed-investigation-chain.png"))

        page.get_by_role("button", name="代码审计", exact=True).click()
        expect(page.get_by_role("heading", name="代码审计", exact=True)).to_be_visible()
        expect(page.get_by_role("heading", name="漏洞清单", exact=True)).to_be_visible()
        expect(page.locator(".audit-metrics article")).to_have_count(4)
        page.screenshot(path=str(output / "installed-code-audit.png"))

        result = {
            "status": "passed",
            "event_count": dashboard["total"],
            "categories": categories,
            "numeric_category_visible": False,
            "checks": [
                "installed executable",
                "title-bar workspace telemetry",
                "existing XDR cache",
                "four KPI cards",
                "trend and risk panels",
                "light and dark themes",
                "single investigation-chain navigation",
                "compact attack path and execution timeline",
                "vulnerability-first code audit",
            ],
        }
        (output / "result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(result, ensure_ascii=False))
        page.evaluate("setTimeout(() => window.desktop.windowControl('close'), 100)")
        time.sleep(0.8)
finally:
    if process.poll() is None:
        process.terminate()
