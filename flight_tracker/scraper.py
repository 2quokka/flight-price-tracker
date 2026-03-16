import re
import os
from datetime import date, timedelta
from typing import List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import fast_flights.core as core
from fast_flights import FlightData, Passengers, get_flights, Flight

from flight_tracker.models import FlightResult, RoundTripCombo

# --- Menlo Security 프록시 우회 ---
CA_CERT = os.environ.get("CA_CERT_PATH", os.path.expanduser("~/Downloads/cacert.pem"))

class _Response:
    def __init__(self, r):
        self.status_code = r.status_code
        self.text = r.text
    @property
    def text_markdown(self):
        return self.text[:500]

def _fetch(params):
    verify = CA_CERT if os.path.exists(CA_CERT) else True
    r = requests.get(
        "https://www.google.com/travel/flights", params=params,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
        verify=verify, timeout=15,
    )
    resp = _Response(r)
    assert resp.status_code == 200, f"HTTP {resp.status_code}"
    return resp

core.fetch = _fetch


def parse_price(price_str: str) -> int:
    nums = re.sub(r"[^\d]", "", price_str)
    return int(nums) if nums else 0


def parse_hour(time_str: str) -> Optional[float]:
    """'7:05 PM on Wed, Apr 1' -> 19.083"""
    m = re.match(r"(\d+):(\d+)\s*(AM|PM)", time_str)
    if not m:
        return None
    h, mi, ap = int(m.group(1)), int(m.group(2)), m.group(3)
    if ap == "PM" and h != 12: h += 12
    if ap == "AM" and h == 12: h = 0
    return h + mi / 60.0


def parse_flight(f: Flight, search_date: str) -> Optional[FlightResult]:
    price = parse_price(f.price)
    if price == 0:
        return None
    return FlightResult(
        date=search_date, airline=f.name or "Unknown",
        departure=f.departure or "", arrival=f.arrival or "",
        price=price, duration=f.duration or "",
        stops=f.stops if f.stops is not None else 0,
    )


def search_one_day(from_airport: str, to_airport: str, search_date: str) -> List[FlightResult]:
    try:
        result = get_flights(
            flight_data=[FlightData(date=search_date, from_airport=from_airport, to_airport=to_airport)],
            trip="one-way", seat="economy", passengers=Passengers(adults=1),
        )
        return sorted(
            [p for f in (result.flights or []) if (p := parse_flight(f, search_date))],
            key=lambda x: x.price,
        )
    except Exception as e:
        print(f"  ⚠ {search_date} {from_airport}→{to_airport} 실패: {e}")
        return []


def search_date_range(
    from_airport: str, to_airport: str, start_date: date, end_date: date, **_
) -> List[FlightResult]:
    dates = []
    d = start_date
    while d <= end_date:
        dates.append(d)
        d += timedelta(days=1)

    results: List[FlightResult] = []
    total = len(dates)

    def _search(i, d):
        ds = d.strftime("%Y-%m-%d")
        flights = search_one_day(from_airport, to_airport, ds)
        return i, d, ds, flights

    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(_search, i, d): i for i, d in enumerate(dates)}
        done = [None] * total
        for fut in as_completed(futures):
            i, d, ds, flights = fut.result()
            done[i] = (ds, flights)

    for ds, flights in done:
        if flights:
            results.append(flights[0])
            print(f"  ✅ {ds} {flights[0].airline} {flights[0].price_display}")
        else:
            print(f"  ❌ {ds} 결과 없음")

    return sorted(results, key=lambda x: x.price)


def _search_daytrip_one(
    from_ap: str, to_ap: str, d: date,
    dep_after: float, dep_before: float,
    ret_after: float, arrive_by: float,
) -> Optional[Tuple[str, FlightResult, FlightResult]]:
    ds = d.strftime("%Y-%m-%d")

    # 가는편: 출발시간 필터
    out_flights = search_one_day(from_ap, to_ap, ds)
    best_out = None
    for f in out_flights:
        h = parse_hour(f.departure)
        if h is not None and dep_after <= h <= dep_before:
            best_out = f
            break  # already sorted by price

    if not best_out:
        return None

    # 오는편: 출발시간 & 도착시간 필터
    ret_flights = search_one_day(to_ap, from_ap, ds)
    best_ret = None
    for f in ret_flights:
        dep_h = parse_hour(f.departure)
        arr_h = parse_hour(f.arrival)
        if dep_h is not None and arr_h is not None and dep_h >= ret_after and arr_h <= arrive_by:
            best_ret = f
            break

    if not best_ret:
        return None

    return ds, best_out, best_ret


def search_daytrip(
    from_ap: str, to_ap: str, start_date: date, end_date: date,
    dep_after: float, dep_before: float,
    ret_after: float, arrive_by: float,
    top_n: int = 10,
) -> List[RoundTripCombo]:
    dates = []
    d = start_date
    while d <= end_date:
        dates.append(d)
        d += timedelta(days=1)

    total = len(dates)
    print(f"📅 {start_date} ~ {end_date} ({total}일) 검색 중...\n")

    results: List[Tuple[str, FlightResult, FlightResult]] = []

    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {
            ex.submit(_search_daytrip_one, from_ap, to_ap, d, dep_after, dep_before, ret_after, arrive_by): d
            for d in dates
        }
        for fut in as_completed(futures):
            d = futures[fut]
            ds = d.strftime("%Y-%m-%d")
            dow = d.strftime("%a")
            r = fut.result()
            if r:
                _, out, ret = r
                total_p = out.price + ret.price
                print(f"  ✅ {ds} ({dow}) ₩{total_p:,}  가:{out.airline} {out.departure} ₩{out.price:,} / 오:{ret.airline} {ret.departure} ₩{ret.price:,}")
                results.append(r)
            else:
                print(f"  ⚠️  {ds} ({dow}) 조건 맞는 항공편 없음")

    combos = [RoundTripCombo(outbound=out, inbound=ret) for _, out, ret in results]
    return sorted(combos, key=lambda c: c.total_price)[:top_n]
