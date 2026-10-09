"""Optional browser smoke test (NOT part of the stdlib-only unit tests).

Needs Playwright:  py -m pip install playwright ; py -m playwright install chromium
Run:               py tests_ui\\ui_smoke.py
Starts its own server on a temporary database, drives the real UI in headless Chromium following the judge demo,
and exits non-zero if anything fails. Your demo database is never touched.
"""
import os, sys, tempfile, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
fd, DB = tempfile.mkstemp(suffix=".db"); os.close(fd); os.unlink(DB)
os.environ["CAMPUSFLOW_DB"] = DB
from campusflow import server  # noqa: E402
try:
    from playwright.sync_api import sync_playwright  # noqa: E402
except ImportError:
    sys.exit("Playwright is not installed. See the docstring at the top of this file.")

srv = server.make_server("127.0.0.1", 0); B = f"http://127.0.0.1:{srv.server_address[1]}"
threading.Thread(target=srv.serve_forever, daemon=True).start()
failures = []
def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  [{extra}]" if (extra and not ok) else "")); ok or failures.append(name)

PAGES = ["#/", "#/report", "#/queue", "#/rooms", "#/map", "#/energy", "#/maintenance", "#/copilot", "#/audit", "#/analytics", "#/demo"]
SCN = "The projector in B204 has stopped working. We have a presentation at 2 PM for 60 students."
with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(viewport={"width": 1366, "height": 850}); js = []
    pg.on("pageerror", lambda e: js.append(e.message))
    pg.goto(B); pg.wait_for_timeout(600)
    for h in PAGES:
        pg.goto(B + "/" + h); pg.wait_for_timeout(500)
        check("page renders " + h, "went wrong" not in pg.inner_text("#main").lower() and len(pg.inner_text("#main")) > 40)
    pg.goto(B + "/#/report"); pg.wait_for_timeout(300); pg.click("#useScn"); pg.click("#sub"); pg.wait_for_timeout(1500)
    t = pg.text_content("#main")
    check("scenario: ticket, P2, A101 suggestion, 'not booked'", all(k in t for k in ("CF-0006", "P2", "A101", "not booked")))
    check("scenario: rejected rooms explained", "B202" in t and "C103" in t)
    pg.select_option("#role", "faculty"); pg.wait_for_timeout(500)
    check("role switch keeps the result visible", "CF-0006" in pg.text_content("#main"))
    pg.click("button[data-reserve]"); pg.wait_for_timeout(900)
    check("reservation succeeds and button shows Booked", "Booked" in pg.inner_text("button[data-reserve]"))
    pg.select_option("#role", "maintenance"); pg.goto(B + "/#/queue"); pg.wait_for_timeout(600)
    pg.click("tr[data-open='CF-0006']"); pg.wait_for_timeout(600); pg.click("button[data-st='In Progress']"); pg.wait_for_timeout(800)
    check("maintenance can move ticket to In Progress", "In Progress" in pg.inner_text("#drawerBody"))
    pg.goto(B + "/#/map"); pg.wait_for_timeout(800)
    check("map shows B204 with active ticket", "CF-0006" in pg.inner_text(".mapTile:has(b:text-is('B204'))"))
    pg.goto(B + "/#/copilot"); pg.wait_for_timeout(400); pg.fill("#cq", "who won the cricket match?"); pg.click("#ask"); pg.wait_for_timeout(700)
    check("copilot says 'not found' for out-of-scope question", "not found in records" in pg.inner_text("#main").lower())
    pg.select_option("#role", "student"); pg.goto(B + "/#/report"); pg.wait_for_timeout(500)
    pg.fill("#rep", "The projector in Z999 is broken, 40 students at 3 PM"); pg.click("#sub"); pg.wait_for_timeout(1000)
    check("unknown room Z999 is rejected, no ticket created", "no ticket was created" in pg.inner_text("#out"))
    m = br.new_page(viewport={"width": 390, "height": 800})
    for h in PAGES:
        m.goto(B + "/" + h); m.wait_for_timeout(500)
        check("mobile (390px) no horizontal overflow " + h, not m.evaluate("document.documentElement.scrollWidth>document.documentElement.clientWidth"))
    check("no uncaught JavaScript errors", not js, "; ".join(js))
    br.close()
srv.shutdown(); srv.server_close()
for e in ("", "-wal", "-shm"):
    try: os.unlink(DB + e)
    except OSError: pass
print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILED: ' + ', '.join(failures)}")
sys.exit(1 if failures else 0)
