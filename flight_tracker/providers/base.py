from abc import ABC, abstractmethod
from typing import List

from flight_tracker.models import FlightResult


class FlightProvider(ABC):
    """항공권 검색 프로바이더 인터페이스"""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def search_one_day(self, from_airport: str, to_airport: str, date_str: str) -> List[FlightResult]:
        """특정 날짜의 항공편 검색. 가격순 정렬된 리스트 반환."""
        ...
