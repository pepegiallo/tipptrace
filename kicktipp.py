import re
from typing import List, Dict, Union
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


def _clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip() if s else ""


def _to_int(s: str) -> int:
    """
    Konvertiert numerische Strings im deutschen Format in int.
    Leere/ungültige Werte -> 0.
    """
    if not s:
        return 0
    # Ziffern mit optionalem Vorzeichen extrahieren; Tausenderpunkte entfernen
    s = _clean_text(s).replace(".", "")
    m = re.search(r"[-+]?\d+", s)
    return int(m.group(0)) if m else 0


def _to_float_de(s: str) -> float:
    """
    Konvertiert deutsche Zahlendarstellung (z.B. '1,00') in float.
    Leere/ungültige Werte -> 0.0.
    """
    if not s:
        return 0.0
    s = _clean_text(s).replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _fetch_html(url: str, timeout: int = 15) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/127.0.0.0 Safari/537.36"
        )
    }
    resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
    resp.raise_for_status()
    return resp.text


def _parse_players_from_html(html: str) -> List[Dict[str, Union[str, int, float]]]:
    """
    Parst die Tabelle #ranking und liefert:
      - nickname: str (aus .mg_name)
      - points:   int (aus td.gesamtpunkte)
      - victories: float (aus td.siege; deutsche Schreibweise möglich, z.B. '1,00')
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table#ranking")
    if not table:
        raise ValueError("Ranking-Tabelle (#ranking) wurde nicht gefunden.")

    players: List[Dict[str, Union[str, int, float]]] = []
    for tr in table.select("tbody > tr.teilnehmer"):
        name_el = tr.select_one(".mg_name")
        nickname = _clean_text(name_el.get_text() if name_el else "")

        points_el = tr.select_one("td.gesamtpunkte")
        points = _to_int(points_el.get_text() if points_el else "")

        victories_el = tr.select_one("td.siege")
        victories = _to_float_de(victories_el.get_text() if victories_el else "")

        players.append(
            {
                "nickname": nickname,
                "victories": victories,
                "points": points,
            }
        )
    return players


def scrape_kicktipp_players(base_url: str) -> List[Dict[str, Union[str, int, float]]]:
    """
    Nimmt die Basis-URL (z.B. 'https://www.kicktipp.de/bl-amigos-2025'),
    hängt '/tippuebersicht' an, scraped die Seite und liefert die Spieler-Liste.
    """
    if not base_url.endswith("/"):
        base_url = base_url + "/"
    url = urljoin(base_url, "tippuebersicht")
    html = _fetch_html(url)
    return _parse_players_from_html(html)

