import re
import os
from typing import List, Optional

import requests
import fast_flights.core as core
from fast_flights import FlightData, Passengers, get_flights, Flight

from flight_tracker.models import FlightResult
from flight_tracker.providers.base import FlightProvider

# --- Menlo Security 프록시 우회 ---
CA_CERT = os.environ.get("CA_CERT_PATH", os.path.expanduser("~/Downloads/cacert.pem"))
_COMBINED_CA = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "combined_ca.pem")


def _get_verify():
    for p in [CA_CERT, _COMBINED_CA]:
        if os.path.exists(p):
            return p
    return True


class _Response:
    def __init__(self, r):
        self.status_code = r.status_code
        self.text = r.text

    @property
    def text_markdown(self):
        return self.text[:500]


def _fetch(params):
    verify = _get_verify()
    try:
        r = requests.get(
            "https://www.google.com/travel/flights", params=params,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
            verify=verify, timeout=15,
        )
    except requests.exceptions.SSLError:
        # Python 3.12+ SSL 호환성 fallback
        r = requests.get(
            "https://www.google.com/travel/flights", params=params,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
            verify=False, timeout=15,
        )
    resp = _Response(r)
    assert resp.status_code == 200, f"HTTP {resp.status_code}"
    return resp


core.fetch = _fetch


def _parse_price(price_str: str) -> int:
    nums = re.sub(r"[^\d]", "", price_str)
    return int(nums) if nums else 0


def _parse_flight(f: Flight, search_date: str) -> Optional[FlightResult]:
    price = _parse_price(f.price)
    if price == 0:
        return None
    return FlightResult(
        date=search_date, airline=f.name or "Unknown",
        departure=f.departure or "", arrival=f.arrival or "",
        price=price, duration=f.duration or "",
        stops=f.stops if f.stops is not None else 0,
        source="google",
    )


class GoogleFlightsProvider(FlightProvider):
    @property
    def name(self) -> str:
        return "google"

    def search_one_day(self, from_airport: str, to_airport: str, date_str: str) -> List[FlightResult]:
        try:
            result = get_flights(
                flight_data=[FlightData(date=date_str, from_airport=from_airport, to_airport=to_airport)],
                trip="one-way", seat="economy", passengers=Passengers(adults=1),
            )
            return sorted(
                [p for f in (result.flights or []) if (p := _parse_flight(f, date_str))],
                key=lambda x: x.price,
            )
        except Exception as e:
            print(f"  ⚠ [google] {date_str} {from_airport}→{to_airport} 실패: {e}")
            return []
