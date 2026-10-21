import pytest


def test_index_page_is_mobile_friendly_and_links_its_assets(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    html = r.text
    assert 'name="viewport"' in html
    assert "/static/styles.css" in html
    assert "/static/app.js" in html


@pytest.mark.parametrize(
    "path, content_type",
    [("/static/styles.css", "text/css"), ("/static/app.js", "javascript")],
)
def test_static_assets_are_served(client, path, content_type):
    r = client.get(path)
    assert r.status_code == 200
    assert content_type in r.headers["content-type"]


def test_stylesheet_defines_both_themes(client):
    css = client.get("/static/styles.css").text
    assert "prefers-color-scheme: dark" in css  # follows the system by default
    assert ':root[data-theme="dark"]' in css  # explicit dark choice from the toggle
    assert ':root[data-theme="light"]' in css  # explicit light choice on a dark system
