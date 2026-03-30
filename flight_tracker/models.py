from dataclasses import dataclass
from typing import Optional


@dataclass
class FlightResult:
    date: str
    airline: str
    departure: str
    arrival: str
    price: int  # KRW
    duration: str
    stops: int
    source: str = "google"

    @property
    def price_display(self) -> str:
        return f"₩{self.price:,}"

    @property
    def dedup_key(self) -> str:
        """같은 항공편 판별용 키 (항공사+날짜+출발시간)"""
        return f"{self.airline}|{self.date}|{self.departure}"


@dataclass
class RoundTripCombo:
    outbound: FlightResult
    inbound: FlightResult

    @property
    def total_price(self) -> int:
        return self.outbound.price + self.inbound.price

    @property
    def total_display(self) -> str:
        return f"₩{self.total_price:,}"
