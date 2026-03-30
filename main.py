#!/usr/bin/env python3
"""김포↔제주 최저가 항공권 검색기"""
import argparse
from datetime import date, datetime

from flight_tracker.models import RoundTripCombo
from flight_tracker.scraper import search_date_range, search_daytrip
from flight_tracker.formatter import print_oneway, print_roundtrip, print_daytrip, save_csv, save_json, console
from flight_tracker.providers import PROVIDERS, get_provider


def parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def parse_time(s: str) -> float:
    """'08:00' -> 8.0, '21:30' -> 21.5"""
    h, m = map(int, s.split(":"))
    return h + m / 60.0


def build_roundtrip_combos(outbound, inbound):
    combos = []
    for o in outbound:
        for i in inbound:
            if i.date > o.date:
                combos.append(RoundTripCombo(outbound=o, inbound=i))
    return sorted(combos, key=lambda c: c.total_price)


def main():
    p = argparse.ArgumentParser(description="김포↔제주 최저가 항공권 검색기")
    p.add_argument("--from", dest="from_airport", default="GMP")
    p.add_argument("--to", dest="to_airport", default="CJU")
    p.add_argument("--start", help="검색 시작일 (YYYY-MM-DD)")
    p.add_argument("--end", help="검색 종료일 (YYYY-MM-DD)")

    # 왕복 모드
    p.add_argument("--depart-start", help="가는날 시작일")
    p.add_argument("--depart-end", help="가는날 종료일")
    p.add_argument("--return-start", help="오는날 시작일")
    p.add_argument("--return-end", help="오는날 종료일")

    # 당일치기 시간 필터
    p.add_argument("--depart-after", help="가는편 출발 최소 시각 (HH:MM, 예: 08:00)")
    p.add_argument("--depart-before", help="가는편 출발 최대 시각 (HH:MM, 예: 10:00)")
    p.add_argument("--return-after", help="오는편 출발 최소 시각 (HH:MM, 예: 17:00)")
    p.add_argument("--arrive-by", help="오는편 도착 마감 시각 (HH:MM, 예: 21:30)")

    p.add_argument("--top", type=int, default=10, help="TOP N (기본: 10)")
    p.add_argument("--output", help="결과 저장 (.csv/.json)")
    p.add_argument("--provider", nargs="*", help=f"사용할 프로바이더 (기본: 전체). 선택: {list(PROVIDERS.keys())}")

    args = p.parse_args()

    # 프로바이더 설정
    providers = [get_provider(n) for n in args.provider] if args.provider else None

    # 당일치기 모드: --start + --depart-after 있으면
    if args.start and args.depart_after:
        da = parse_time(args.depart_after)
        db = parse_time(args.depart_before or "10:00")
        ra = parse_time(args.return_after or "17:00")
        ab = parse_time(args.arrive_by or "21:30")

        console.print(f"\n✈️  [bold]당일치기 검색: {args.from_airport} ↔ {args.to_airport}[/bold]")
        console.print(f"   가는편 {args.depart_after}~{args.depart_before or '10:00'} 출발 / 오는편 {args.return_after or '17:00'} 이후 출발, {args.arrive_by or '21:30'} 이전 도착\n")

        combos = search_daytrip(
            args.from_airport, args.to_airport,
            parse_date(args.start), parse_date(args.end or args.start),
            da, db, ra, ab, args.top, providers=providers,
        )
        print_daytrip(combos, args.from_airport, args.to_airport, args.top)

    # 왕복 모드
    elif args.depart_start:
        console.print(f"\n✈️  [bold]왕복 검색: {args.from_airport} ↔ {args.to_airport}[/bold]\n")
        console.print("[cyan]▶ 가는편 검색[/cyan]")
        outbound = search_date_range(args.from_airport, args.to_airport, parse_date(args.depart_start), parse_date(args.depart_end), providers=providers)
        console.print("\n[cyan]▶ 오는편 검색[/cyan]")
        inbound = search_date_range(args.to_airport, args.from_airport, parse_date(args.return_start), parse_date(args.return_end), providers=providers)
        combos = build_roundtrip_combos(outbound, inbound)
        print_roundtrip(combos, args.from_airport, args.to_airport, args.top)

    # 편도 모드
    elif args.start:
        console.print(f"\n✈️  [bold]편도 검색: {args.from_airport} → {args.to_airport}[/bold]\n")
        results = search_date_range(args.from_airport, args.to_airport, parse_date(args.start), parse_date(args.end or args.start), providers=providers)
        print_oneway(results, args.from_airport, args.to_airport)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
