"""하위 호환용 래퍼 - 기존 인터페이스 유지하면서 aggregator로 위임"""
import re
from datetime import date
from typing import List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from flight_tracker.models import FlightResult, RoundTripCombo
from flight_tracker.providers import get_provider, PROVIDERS
from flight_tracker.providers.base import FlightProvider
from flight_tracker import aggregator


def _default_providers() -> List[FlightProvider]:
    return [cls() for cls in PROVIDERS.values()]


def parse_hour(time_str: str) -> Optional[float]:
    """'7:05 PM on Wed, Apr 1' -> 19.083"""
    m = re.match(r"(\d+):(\d+)\s*(AM|PM)", time_str)
    if not m:
        return None
    h, mi, ap = int(m.group(1)), int(m.group(2)), m.group(3)
    if ap == "PM" and h != 12: h += 12
    if ap == "AM" and h == 12: h = 0
    return h + mi / 60.0


def search_one_day(from_airport: str, to_airport: str, date_str: str, providers: List[FlightProvider] = None) -> List[FlightResult]:
    return aggregator.search_one_day(providers or _default_providers(), from_airport, to_airport, date_str)


def search_date_range(from_airport: str, to_airport: str, start_date: date, end_date: date, providers: List[FlightProvider] = None, **_) -> List[FlightResult]:
    return aggregator.search_date_range(providers or _default_providers(), from_airport, to_airport, start_date, end_date)


def search_daytrip(
    from_ap: str, to_ap: str, start_date: date, end_date: date,
    dep_after: float, dep_before: float,
    ret_after: float, arrive_by: float,
    top_n: int = 10, providers: List[FlightProvider] = None,
) -> List[RoundTripCombo]:
    provs = providers or _default_providers()
    dates = []
    d = start_date
    while d <= end_date:
        dates.append(d)
        d += __import__("datetime").timedelta(days=1)

    print(f"📅 {start_date} ~ {end_date} ({len(dates)}일) 검색 중...\n")

    def _search_one(d: date) -> Optional[Tuple[FlightResult, FlightResult]]:
        ds = d.strftime("%Y-%m-%d")
        out_flights = aggregator.search_one_day(provs, from_ap, to_ap, ds)
        best_out = next((f for f in out_flights if (h := parse_hour(f.departure)) is not None and dep_after <= h <= dep_before), None)
        if not best_out:
            return None
        ret_flights = aggregator.search_one_day(provs, to_ap, from_ap, ds)
        best_ret = next((f for f in ret_flights if (dh := parse_hour(f.departure)) is not None and (ah := parse_hour(f.arrival)) is not None and dh >= ret_after and ah <= arrive_by), None)
        if not best_ret:
            return None
        return best_out, best_ret

    results: List[RoundTripCombo] = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(_search_one, d): d for d in dates}
        for fut in as_completed(futures):
            d = futures[fut]
            ds, dow = d.strftime("%Y-%m-%d"), d.strftime("%a")
            r = fut.result()
            if r:
                out, ret = r
                print(f"  ✅ {ds} ({dow}) ₩{out.price + ret.price:,}  가:{out.airline} {out.departure} ₩{out.price:,} / 오:{ret.airline} {ret.departure} ₩{ret.price:,}")
                results.append(RoundTripCombo(outbound=out, inbound=ret))
            else:
                print(f"  ⚠️  {ds} ({dow}) 조건 맞는 항공편 없음")

    return sorted(results, key=lambda c: c.total_price)[:top_n]
