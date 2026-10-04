"""The homepage plugs FuckWhatDay with a link and its icon.

Nothing of FuckWhatDay is copied here: the icon is the one the FuckWhatDay
site already publishes, the same way the og:image points at ernster.dev.
"""

FUCKWHATDAY = "https://ernster.dev/FuckWhatDay/"


def test_homepage_links_to_fuckwhatday_with_its_published_icon(client):
    response = client.get("/")

    assert f'href="{FUCKWHATDAY}"' in response.text
    assert f'src="{FUCKWHATDAY}img/apple-touch-icon.png"' in response.text
