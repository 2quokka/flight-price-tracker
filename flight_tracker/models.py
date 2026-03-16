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

    @property
    def price_display(self) -> str:
        return f"₩{self.price:,}"


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
