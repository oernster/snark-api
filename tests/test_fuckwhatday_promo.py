"""The homepage plugs FuckWhatDay with a link and its icon.

The icon is a local copy, so the badge never shows a broken image when the
FuckWhatDay site is unreachable. Only the link goes to that site.
"""

from fastapi import status

ICON = "/static/fuckwhatday.png"


def test_homepage_links_to_fuckwhatday_with_its_icon(client):
    response = client.get("/")

    assert 'href="https://ernster.dev/FuckWhatDay/"' in response.text
    assert f'src="{ICON}"' in response.text


def test_fuckwhatday_icon_is_served_locally(client):
    response = client.get(ICON)

    assert response.status_code == status.HTTP_200_OK
    assert response.headers.get("content-type") == "image/png"
