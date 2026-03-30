"""Trip.com 항공편 검색 프로바이더 (Playwright 기반)

Playwright sync API는 메인 스레드에서만 동작하므로,
subprocess로 별도 프로세스에서 실행하여 스레드 안전성을 확보합니다.
"""
import json
import re
import subprocess
import sys
from typing import List

from flight_tracker.models import FlightResult
from flight_tracker.providers.base import FlightProvider

# 별도 프로세스에서 실행할 스크래핑 스크립트
_SCRAPE_SCRIPT = '''
import json, sys
from playwright.sync_api import sync_playwright

from_ap, to_ap, date_str = sys.argv[1], sys.argv[2], sys.argv[3]
captured = []

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        locale="ko-KR",
    )
    page = ctx.new_page()

    def on_resp(resp):
        if "flightListSearch" in resp.url or "flightList" in resp.url:
            try:
                body = resp.json()
                items = body.get("data", {}).get("flightItineraryList") or body.get("flightItineraryList") or []
                captured.extend(items)
            except:
                pass

    page.on("response", on_resp)
    url = f"https://kr.trip.com/flights/list?dcity={from_ap.lower()}&acity={to_ap.lower()}&ddate={date_str}&triptype=ow&class=y&quantity=1&locale=ko-KR&curr=KRW"
    try:
        page.goto(url, timeout=20000)
        page.wait_for_timeout(6000)
    except:
        pass

    # DOM fallback
    if not captured:
        try:
            cards = page.query_selector_all("[class*=\\'flight-item\\'], [class*=\\'FlightItem\\'], [class*=\\'list-item\\']")
            for card in cards[:10]:
                captured.append({"_dom_text": card.inner_text()})
        except:
            pass

    browser.close()

print(json.dumps(captured, ensure_ascii=False))
'''


def _parse_price(text: str) -> int:
    nums = re.sub(r"[^\d]", "", text)
    return int(nums) if nums else 0


class TripComProvider(FlightProvider):
    @property
    def name(self) -> str:
        return "tripcom"

    def search_one_day(self, from_airport: str, to_airport: str, date_str: str) -> List[FlightResult]:
        try:
            items = self._run_scraper(from_airport, to_airport, date_str)
            return self._to_results(items, date_str)
        except Exception as e:
            print(f"  ⚠ [tripcom] {date_str} {from_airport}→{to_airport} 실패: {e}")
            return []

    def _run_scraper(self, from_ap: str, to_ap: str, date_str: str) -> list:
        """subprocess로 Playwright 실행 (스레드 안전)"""
        result = subprocess.run(
            [sys.executable, "-c", _SCRAPE_SCRIPT, from_ap, to_ap, date_str],
            capture_output=True, text=True, timeout=35,
        )
        if result.returncode != 0:
            return []
        try:
            return json.loads(result.stdout.strip())
        except:
            return []

    def _to_results(self, items: list, date_str: str) -> List[FlightResult]:
        results = []
        for item in items:
            try:
                if "_dom_text" in item:
                    r = self._parse_dom_text(item["_dom_text"], date_str)
                    if r:
                        results.append(r)
                    continue

                segs = item.get("flightSegments", [{}])
                seg = segs[0] if segs else {}
                legs = seg.get("flightLegs", seg.get("legs", [{}]))
                leg = legs[0] if legs else {}

                airline = leg.get("airlineName") or seg.get("airlineName") or "Unknown"
                dep = leg.get("departureTime", "")
                arr = leg.get("arrivalTime", "")
                duration = seg.get("duration") or leg.get("duration") or ""

                price_info = item.get("priceList", item.get("policyInfo", [{}]))
                price = 0
                if price_info:
                    pi = price_info[0] if isinstance(price_info, list) else price_info
                    price = pi.get("adultPrice", pi.get("price", 0))

                if price > 0:
                    results.append(FlightResult(
                        date=date_str, airline=airline, departure=dep, arrival=arr,
                        price=int(price), duration=str(duration),
                        stops=max(0, len(legs) - 1), source="tripcom",
                    ))
            except:
                continue
        return sorted(results, key=lambda x: x.price)

    def _parse_dom_text(self, text: str, date_str: str):
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        price = 0
        for l in lines:
            p = _parse_price(l)
            if 10000 < p < 10000000:
                price = p
                break
        if not price:
            return None
        return FlightResult(
            date=date_str, airline=lines[0] if lines else "Unknown",
            departure="", arrival="", price=price, duration="",
            stops=0, source="tripcom",
        )
