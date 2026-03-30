from flight_tracker.providers.base import FlightProvider
from flight_tracker.providers.google import GoogleFlightsProvider
from flight_tracker.providers.tripcom import TripComProvider
from flight_tracker.providers.fli_provider import FliProvider

PROVIDERS: dict[str, type[FlightProvider]] = {
    "google": GoogleFlightsProvider,
    "fli": FliProvider,
    "tripcom": TripComProvider,
}


def get_provider(name: str) -> FlightProvider:
    cls = PROVIDERS.get(name)
    if not cls:
        raise ValueError(f"Unknown provider: {name}. Available: {list(PROVIDERS.keys())}")
    return cls()
