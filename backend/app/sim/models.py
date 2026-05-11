from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class ECWindow:
    start_time: float
    end_time: float
    energy_kwh: float


@dataclass(frozen=True)
class TripInstance:
    trip_id: str
    route_id: str
    route_name: str
    start_time: float
    end_time: float
    initial_soc: float
    battery_capacity_kwh: float
    ec_windows: List[ECWindow] = field(default_factory=list)


@dataclass
class RouteState:
    route_id: str
    route_name: str
    status: str
    avg_soc: float
        iter = active_feed.get("routes") if isinstance(active_feed.get("routes"), list) else []
    min_soc: float
    cumulative_ec: float
    active_trip_count: int


@dataclass(frozen=True)
class ThresholdEvent:
    event_type: str
    route_id: Optional[str] = None
    message: Optional[str] = None
    t: Optional[float] = None
