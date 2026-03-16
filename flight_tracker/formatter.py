import csv
import json
from typing import List

from rich.console import Console
from rich.table import Table

from flight_tracker.models import FlightResult, RoundTripCombo

console = Console()


def print_oneway(results: List[FlightResult], from_ap: str, to_ap: str):
    if not results:
        console.print("[red]검색 결과가 없습니다.[/red]")
        return

    table = Table(title=f"✈️  {from_ap} → {to_ap} 최저가 검색 결과")
    table.add_column("날짜", style="cyan")
    table.add_column("항공사", style="white")
    table.add_column("출발", style="green")
    table.add_column("도착", style="green")
    table.add_column("소요", style="dim")
    table.add_column("가격", style="bold yellow", justify="right")

    for f in results:
        table.add_row(f.date, f.airline, f.departure, f.arrival, f.duration, f.price_display)

    console.print(table)
    best = results[0]
    console.print(f"\n🏆 [bold green]최저가: {best.date} {best.airline} {best.departure} {best.price_display}[/bold green]")


def print_roundtrip(combos: List[RoundTripCombo], from_ap: str, to_ap: str, top_n: int = 5):
    if not combos:
        console.print("[red]왕복 조합 결과가 없습니다.[/red]")
        return

    table = Table(title=f"✈️  {from_ap} ↔ {to_ap} 왕복 최저가 TOP {min(top_n, len(combos))}")
    table.add_column("가는날", style="cyan")
    table.add_column("가는편", style="white")
    table.add_column("가는편 가격", justify="right")
    table.add_column("오는날", style="cyan")
    table.add_column("오는편", style="white")
    table.add_column("오는편 가격", justify="right")
    table.add_column("합계", style="bold yellow", justify="right")

    for c in combos[:top_n]:
        table.add_row(
            c.outbound.date, c.outbound.airline, c.outbound.price_display,
            c.inbound.date, c.inbound.airline, c.inbound.price_display,
            c.total_display,
        )

    console.print(table)
    best = combos[0]
    console.print(f"\n🏆 [bold green]최저가 왕복: {best.outbound.date}→{best.inbound.date} {best.total_display}[/bold green]")


def print_daytrip(combos: List[RoundTripCombo], from_ap: str, to_ap: str, top_n: int = 10):
    if not combos:
        console.print("[red]조건에 맞는 당일치기 항공편이 없습니다.[/red]")
        return

    table = Table(title=f"✈️  {from_ap} ↔ {to_ap} 당일치기 최저가 TOP {min(top_n, len(combos))}")
    table.add_column("순위", style="bold", justify="center")
    table.add_column("날짜", style="cyan")
    table.add_column("가는편", style="white")
    table.add_column("출발→도착", style="green")
    table.add_column("가는편 가격", justify="right")
    table.add_column("오는편", style="white")
    table.add_column("출발→도착", style="green")
    table.add_column("오는편 가격", justify="right")
    table.add_column("합계", style="bold yellow", justify="right")

    for i, c in enumerate(combos[:top_n], 1):
        table.add_row(
            str(i), c.outbound.date,
            c.outbound.airline, f"{c.outbound.departure} → {c.outbound.arrival}", c.outbound.price_display,
            c.inbound.airline, f"{c.inbound.departure} → {c.inbound.arrival}", c.inbound.price_display,
            c.total_display,
        )

    console.print(table)
    best = combos[0]
    console.print(f"\n🏆 [bold green]최저가: {best.outbound.date} 왕복 {best.total_display}[/bold green]")


def save_csv(results: List[FlightResult], path: str):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["날짜", "항공사", "출발", "도착", "소요시간", "가격(원)"])
        for r in results:
            w.writerow([r.date, r.airline, r.departure, r.arrival, r.duration, r.price])
    console.print(f"📁 CSV 저장: {path}")


def save_json(results: List[FlightResult], path: str):
    data = [
        {"date": r.date, "airline": r.airline, "departure": r.departure,
         "arrival": r.arrival, "duration": r.duration, "price": r.price, "stops": r.stops}
        for r in results
    ]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    console.print(f"📁 JSON 저장: {path}")
