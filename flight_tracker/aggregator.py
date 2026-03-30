"""멀티 프로바이더 항공편 검색 + 중복 제거"""
from datetime import date, timedelta
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed

from flight_tracker.models import FlightResult
from flight_tracker.providers.base import FlightProvider


def _deduplicate(flights: List[FlightResult]) -> List[FlightResult]:
    """같은 항공편이 여러 소스에서 나오면 최저가만 유지"""
    best: dict[str, FlightResult] = {}
    for f in flights:
        key = f.dedup_key
        if key not in best or f.price < best[key].price:
            best[key] = f
    return sorted(best.values(), key=lambda x: x.price)


def search_one_day(
    providers: List[FlightProvider],
    from_airport: str, to_airport: str, date_str: str,
) -> List[FlightResult]:
    """여러 프로바이더에서 특정 날짜 검색 후 병합"""
    all_flights: List[FlightResult] = []
    with ThreadPoolExecutor(max_workers=len(providers)) as ex:
        futures = {ex.submit(p.search_one_day, from_airport, to_airport, date_str): p for p in providers}
        for fut in as_completed(futures):
            all_flights.extend(fut.result())
    return _deduplicate(all_flights)


def search_date_range(
    providers: List[FlightProvider],
    from_airport: str, to_airport: str,
    start_date: date, end_date: date,
) -> List[FlightResult]:
    """날짜 범위 × 프로바이더 병렬 검색, 날짜별 최저가 1건"""
    dates = []
    d = start_date
    while d <= end_date:
        dates.append(d)
        d += timedelta(days=1)

    results: List[FlightResult] = []

    def _search(d: date):
        ds = d.strftime("%Y-%m-%d")
        flights = search_one_day(providers, from_airport, to_airport, ds)
        return ds, flights

    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(_search, d): i for i, d in enumerate(dates)}
        ordered = [None] * len(dates)
        for fut in as_completed(futures):
            idx = futures[fut]
            ordered[idx] = fut.result()

    for ds, flights in ordered:
        if flights:
            best = flights[0]
            results.append(best)
            print(f"  ✅ {ds} {best.airline} {best.price_display} [{best.source}]")
        else:
            print(f"  ❌ {ds} 결과 없음")

    return sorted(results, key=lambda x: x.price)
