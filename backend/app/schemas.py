from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class SimulationStateRequest(BaseModel):
    t: float
    t_prev: Optional[float] = None
    mode: Literal["playback", "seek"]
    selected_route_id: Optional[str] = None


class RouteSummary(BaseModel):
    route_id: str
    route_name: str
    status: str
    avg_soc: float
    min_soc: float
    cumulative_ec: float
    active_trip_count: int


class ThresholdEvent(BaseModel):
    event_type: str
    route_id: Optional[str] = None
    message: Optional[str] = None
    t: Optional[float] = None
    model_config = ConfigDict(extra="allow")


class SimulationStateResponse(BaseModel):
    current_time: float
    routes: List[RouteSummary]
    selected_route: Optional[RouteSummary]
    events: List[ThresholdEvent] = Field(default_factory=list)


class GTFSStopPoint(BaseModel):
    stop_id: str
    stop_name: str
    lat: float
    lon: float


class GTFSRoute(BaseModel):
    route_id: str
    route_name: str
    trip_count: int = 0
    stop_count: int = 0
    geometry_source: str = "stops"
    coordinates: List[List[float]] = Field(default_factory=list)
    stop_points: List[GTFSStopPoint] = Field(default_factory=list)
    length_km: float = 0.0


class GTFSRoutesResponse(BaseModel):
    feed_loaded: bool = False
    route_count: int = 0
    routes: List[GTFSRoute] = Field(default_factory=list)
