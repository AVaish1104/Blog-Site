"""
Browser tests (opt-in): real reader and editor journeys, responsive overflow and
axe-core accessibility checks.

    pytest -m e2e                              # uses Playwright's bundled Chromium
    pytest -m e2e --browser-channel msedge     # or an installed Edge / Chrome
"""

import os
from io import StringIO

import pytest
from django.core.management import call_command

from tests.conftest import PASSWORD

os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")  # Playwright runs an event loop

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]

VIEWPORTS = {"laptop": (1440, 900), "phone": (390, 844)}
PUBLIC_PAGES = [
    "/",
    "/posts/",
    "/posts/editing-is-mostly-subtraction/",
    "/topics/",
    "/topics/design/",
    "/tags/",
    "/authors/iris-calloway/",
    "/search/?q=typography",
    "/search/?q=nomatch",
    "/newsletter/",
    "/studio/login/",
    "/posts/missing/",
]
STUDIO_PAGES = [
    "/studio/",
    "/studio/posts/",
    "/studio/posts/new/",
    "/studio/images/",
    "/studio/topics/",
    "/studio/authors/",
    "/studio/comments/",
    "/studio/subscribers/",
]


@pytest.fixture
def seeded(transactional_db, editor):
    call_command("seed_demo", stdout=StringIO())


def sign_in(page, base):
    page.goto(f"{base}/studio/login/")
    page.fill("#id_username", "editor")
    page.fill("#id_password", PASSWORD)
    page.click("button[type=submit]")
    page.wait_for_url(f"{base}/studio/")


def assert_no_overflow(page, label):
    overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    assert overflow <= 0, f"{label}: page is {overflow}px wider than the viewport"


def assert_accessible(page, label):
    from axe_playwright_python.sync_playwright import Axe

    violations = Axe().run(page).response["violations"]
    summary = [f"{v['id']} ({v['impact']}): {v['nodes'][0]['target']}" for v in violations]
    assert not violations, f"{label}: {summary}"


@pytest.mark.parametrize("viewport", VIEWPORTS)
def test_pages_fit_and_are_accessible(seeded, live_server, browser, viewport):
    width, height = VIEWPORTS[viewport]
    context = browser.new_context(viewport={"width": width, "height": height})
    page = context.new_page()
    for path in PUBLIC_PAGES:
        page.goto(live_server.url + path)
        assert_no_overflow(page, f"{viewport} {path}")
        assert_accessible(page, f"{viewport} {path}")
    sign_in(page, live_server.url)
    for path in STUDIO_PAGES:
        page.goto(live_server.url + path)
        assert_no_overflow(page, f"{viewport} {path}")
        assert_accessible(page, f"{viewport} {path}")
    context.close()


def test_reader_journey(seeded, live_server, page):
    page.goto(live_server.url + "/")
    page.click("#featured-title a")
    assert page.locator("h1").inner_text() == "Editing is mostly subtraction"
    page.click("nav[aria-label=Main] >> text=Search")
    page.fill("#search-q", "typography")
    page.press("#search-q", "Enter")
    assert "Typography is interface" in page.locator(".post-index").inner_text()
    page.click("text=Typography is interface")
    assert page.locator(".prose h2").count() >= 1


def test_mobile_menu_toggles(seeded, live_server, browser):
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    page.goto(live_server.url + "/")
    toggle = page.locator("[data-nav-toggle]")
    assert toggle.get_attribute("aria-expanded") == "false"
    assert not page.locator("#site-nav").is_visible()
    toggle.click()
    assert toggle.get_attribute("aria-expanded") == "true"
    page.click("#site-nav >> text=Articles")
    assert page.url.endswith("/posts/")
    context.close()


def test_editor_writes_previews_publishes_and_deletes(seeded, live_server, page, context):
    sign_in(page, live_server.url)
    page.click("text=New post")
    page.fill("#id_title", "A browser-written post")
    assert page.input_value("#id_slug") == "a-browser-written-post"  # auto-slug
    page.fill("#id_body", "Opening paragraph.")
    page.click("[data-md=heading]")  # toolbar inserts Markdown
    assert "## " in page.input_value("#id_body")

    with context.expect_page() as preview_info:
        page.click("[data-preview]")
    preview = preview_info.value
    preview.wait_for_load_state()
    assert "Preview" in preview.locator(".preview-banner").inner_text()
    assert preview.locator("h1").inner_text() == "A browser-written post"
    preview.close()

    page.check("input[name=status][value=published]")
    page.click("button:has-text('Save')")
    assert "live" in page.locator(".messages").inner_text()

    public = context.new_page()
    public.goto(live_server.url + "/posts/a-browser-written-post/")
    assert public.locator("h1").inner_text() == "A browser-written post"

    page.click("text=Delete…")
    page.click("button:has-text('Delete post')")
    assert "deleted" in page.locator(".messages").inner_text()
    public.goto(live_server.url + "/posts/a-browser-written-post/")
    assert "doesn" in public.locator("h1").inner_text()


def test_validation_errors_are_announced(seeded, live_server, page):
    sign_in(page, live_server.url)
    page.goto(live_server.url + "/studio/posts/new/")
    page.click("button:has-text('Save')")
    summary = page.locator("[data-error-summary]")
    assert summary.is_visible()
    assert "title" in summary.inner_text().lower()
    assert page.evaluate("document.activeElement.hasAttribute('data-error-summary')")
    assert page.get_attribute("#id_title", "aria-invalid") == "true"
