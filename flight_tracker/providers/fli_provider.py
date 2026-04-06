"""Fli 라이브러리 기반 Google Flights 프로바이더 (리버스 엔지니어링 API)"""
import os
from typing import List

import requests as _requests

from flight_tracker.models import FlightResult
from flight_tracker.providers.base import FlightProvider


def _get_usd_krw() -> float:
    """실시간 USD/KRW 환율 조회 (frankfurter.dev, 무료/키 불필요)"""
    try:
        r = _requests.get("https://api.frankfurter.dev/latest?from=USD&to=KRW", timeout=5)
        return r.json()["rates"]["KRW"]
    except Exception:
        return 1350.0  # fallback


def _patch_fli():
    try:
        import fli.search.client as client_mod
        from curl_cffi import requests as cffi_requests

        def _patched_init(self):
            self._client = cffi_requests.Session(verify=False)
            self._client.headers.update(self.DEFAULT_HEADERS)
            self._client.headers["Accept-Language"] = "ko-KR,ko;q=0.9"
        client_mod.Client.__init__ = _patched_init

        import fli.search.flights as flights_mod
        flights_mod.SearchFlights.BASE_URL = (
            "https://www.google.co.kr/_/FlightsFrontendUi/data/"
            "travel.frontend.flights.FlightsFrontendService/GetShoppingResults"
        )

        _orig_search = flights_mod.SearchFlights.search
        def _patched_search(self, filters, top_n=5):
            _orig_post = self.client._client.post
            def _no_impersonate_post(*args, **kwargs):
                kwargs.pop("impersonate", None)
                return _orig_post(*args, **kwargs)
            self.client._client.post = _no_impersonate_post
            return _orig_search(self, filters, top_n)
        flights_mod.SearchFlights.search = _patched_search
    except ImportError:
        pass

_patch_fli()


class FliProvider(FlightProvider):
    @property
    def name(self) -> str:
        return "fli"

    def search_one_day(self, from_airport: str, to_airport: str, date_str: str) -> List[FlightResult]:
        try:
            from fli.search import SearchFlights
            from fli.models import Airport, PassengerInfo, SeatType, MaxStops, SortBy, FlightSearchFilters, FlightSegment

            dep = getattr(Airport, from_airport, None)
            arr = getattr(Airport, to_airport, None)
            if not dep or not arr:
                return []

            filters = FlightSearchFilters(
                passenger_info=PassengerInfo(adults=1),
                flight_segments=[FlightSegment(
                    departure_airport=[[dep, 0]],
                    arrival_airport=[[arr, 0]],
                    travel_date=date_str,
                )],
                seat_type=SeatType.ECONOMY,
                stops=MaxStops.ANY,
                sort_by=SortBy.CHEAPEST,
            )

            search = SearchFlights()
            flights = search.search(filters)

            results = []
            for f in flights:
                leg = f.legs[0] if f.legs else None
                if not leg or f.price <= 0:
                    continue
                price = int(f.price)
                # 서버 IP가 해외인 경우 USD로 반환됨 — KRW 가격은 최소 10,000 이상
                if price < 10000:
                    price = int(price * _get_usd_krw())
                results.append(FlightResult(
                    date=date_str,
                    airline=leg.airline.value if leg.airline else "Unknown",
                    departure=leg.departure_datetime.strftime("%H:%M") if leg.departure_datetime else "",
                    arrival=leg.arrival_datetime.strftime("%H:%M") if leg.arrival_datetime else "",
                    price=price,
                    duration=f"{f.duration // 60}h {f.duration % 60}m" if f.duration else "",
                    stops=f.stops or 0,
                    source="fli",
                ))
            return sorted(results, key=lambda x: x.price)

        except Exception as e:
            print(f"  ⚠ [fli] {date_str} {from_airport}→{to_airport} 실패: {e}")
            return []
