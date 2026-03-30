from flight_tracker.providers.base import FlightProvider
from flight_tracker.providers.google import GoogleFlightsProvider

PROVIDERS: dict[str, type[FlightProvider]] = {
    "google": GoogleFlightsProvider,
}


def get_provider(name: str) -> FlightProvider:
    cls = PROVIDERS.get(name)
    if not cls:
        raise ValueError(f"Unknown provider: {name}. Available: {list(PROVIDERS.keys())}")
    return cls()
