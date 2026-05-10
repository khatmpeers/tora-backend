from __future__ import annotations

import math
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from app.gtfs.store import get_active_feed
from app.schemas import (
    RouteSummary,
    SimulationStateRequest,
    SimulationStateResponse,
    ThresholdEvent,
)
from app.sim.mock_data import MOCK_TRIPS, ROUTE_CATALOG
from app.sim.models import ECWindow, TripInstance
from app.sim.routezero_adapter import RouteZeroAdapter

_routezero = RouteZeroAdapter()
_SIM_HORIZON = 240.0
_SOC_THRESHOLDS: List[Tuple[float, str]] = [
    (20.0, "warning"),
    (10.0, "critical"),
    (0.0, "failure"),
]
_STATUS_RANK = {
    "normal": 0,
    "warning": 1,
    "critical": 2,
    "failure": 3,
}


def is_trip_active(trip: TripInstance, t: float) -> bool:
    return trip.start_time <= t < trip.end_time


def _window_energy_up_to_t(window: ECWindow, t: float) -> float:
    if t <= window.start_time:
        return 0.0
    if t >= window.end_time:
        return window.energy_kwh

    duration = window.end_time - window.start_time
    if duration <= 0:
        return 0.0

    fraction = (t - window.start_time) / duration
    return window.energy_kwh * fraction


def compute_consumed_energy_up_to_t(trip: TripInstance, t: float) -> float:
    if t <= trip.start_time:
        return 0.0

    capped_t = min(t, trip.end_time)
    return sum(_window_energy_up_to_t(window, capped_t) for window in trip.ec_windows)


def compute_soc_at_t(trip: TripInstance, t: float) -> float:
    consumed_kwh = compute_consumed_energy_up_to_t(trip, t)
    if trip.battery_capacity_kwh <= 0:
        return 0.0
    return trip.initial_soc - (consumed_kwh / trip.battery_capacity_kwh) * 100.0


def _status_from_min_soc(min_soc: float) -> str:
    if min_soc <= 0:
        return "failure"
    if min_soc <= 10:
        return "critical"
    if min_soc <= 20:
        return "warning"
    return "normal"


def _status_from_active_socs(active_socs: List[float]) -> str:
    if not active_socs:
        return "normal"
    return _status_from_min_soc(min(active_socs))


def summarize_route_at_t(route_id: str, route_name: str, trips: List[TripInstance], t: float) -> RouteSummary:
    cumulative_ec = sum(compute_consumed_energy_up_to_t(trip, t) for trip in trips)

    active_socs = [compute_soc_at_t(trip, t) for trip in trips if is_trip_active(trip, t)]
    active_trip_count = len(active_socs)

    if active_trip_count == 0:
        avg_soc = 0.0
        min_soc = 0.0
    else:
        avg_soc = sum(active_socs) / active_trip_count
        min_soc = min(active_socs)

    return RouteSummary(
        route_id=route_id,
        route_name=route_name,
        status=_status_from_active_socs(active_socs),
        avg_soc=round(avg_soc, 1),
        min_soc=round(min_soc, 1),
        cumulative_ec=round(cumulative_ec, 1),
        active_trip_count=active_trip_count,
    )


def _trip_overlaps_interval(trip: TripInstance, t_prev: float, t: float) -> bool:
    interval_start = min(t_prev, t)
    interval_end = max(t_prev, t)
    return trip.start_time <= interval_end and trip.end_time > interval_start


def _estimate_cross_time(
    *,
    threshold: float,
    soc_prev: float,
    soc_now: float,
    t_prev: float,
    t: float,
) -> Optional[float]:
    if soc_prev == soc_now:
        return None

    denominator = soc_prev - soc_now
    if denominator == 0:
        return None

    cross_fraction = (soc_prev - threshold) / denominator
    if cross_fraction < 0.0 or cross_fraction > 1.0:
        return None

    return t_prev + cross_fraction * (t - t_prev)


def _build_threshold_event(trip: TripInstance, event_type: str, cross_time: float) -> ThresholdEvent:
    if event_type == "failure":
        message = "Trip {trip_id} depleted battery".format(trip_id=trip.trip_id)
    else:
        message = "Trip {trip_id} dropped to {event_type} threshold".format(
            trip_id=trip.trip_id,
            event_type=event_type,
        )

    return ThresholdEvent(
        event_type=event_type,
        route_id=trip.route_id,
        t=cross_time,
        message=message,
    )


def _detect_threshold_events_for_trip(trip: TripInstance, t_prev: float, t: float) -> List[ThresholdEvent]:
    if not _trip_overlaps_interval(trip, t_prev, t):
        return []

    soc_prev = compute_soc_at_t(trip, t_prev)
    soc_now = compute_soc_at_t(trip, t)

    events: List[ThresholdEvent] = []
    for threshold, event_type in _SOC_THRESHOLDS:
        crossed = soc_prev > threshold and soc_now <= threshold
        if not crossed:
            continue

        cross_time = _estimate_cross_time(
            threshold=threshold,
            soc_prev=soc_prev,
            soc_now=soc_now,
            t_prev=t_prev,
            t=t,
        )
        if cross_time is None:
            continue

        events.append(_build_threshold_event(trip, event_type, cross_time))

    return events


def _get_interval_events(trips: List[TripInstance], t_prev: float, t: float) -> List[ThresholdEvent]:
    if t == t_prev:
        return []

    events: List[ThresholdEvent] = []
    for trip in trips:
        events.extend(_detect_threshold_events_for_trip(trip, t_prev, t))

    events.sort(key=lambda event: (event.t if event.t is not None else float("inf")))
    return events


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))


def _stable_seed(route_id: str, index: int) -> int:
    checksum = 0
    for idx, char in enumerate(route_id):
        checksum += (idx + 1) * ord(char)
    return checksum + index * 97


def _route_summary_from_uploaded_meta(route_meta: Dict[str, object], t: float, index: int) -> RouteSummary:
    route_id = str(route_meta.get("route_id") or "")
    route_name = str(route_meta.get("route_name") or "Route {id}".format(id=route_id))

    trip_count = int(route_meta.get("trip_count") or 0)
    stop_count = int(route_meta.get("stop_count") or 0)
    length_km = float(route_meta.get("length_km") or 0.0)

    seed = _stable_seed(route_id, index)
    phase = (seed % 360) * (math.pi / 180.0)
    t_norm = max(0.0, t) / _SIM_HORIZON

    service_wave = 0.5 + 0.5 * math.sin((t / 28.0) + phase)
    active_trip_count = int(round(max(0.0, trip_count * (0.15 + 0.7 * service_wave))))
    active_trip_count = min(active_trip_count, max(trip_count, 0))

    avg_soc_start = 90.0 - min(18.0, length_km * 0.8) - min(10.0, stop_count * 0.2)
    avg_soc_decline = t_norm * (12.0 + length_km * 0.6 + trip_count * 0.25)
    avg_soc_wave = 3.5 * math.sin((t / 18.0) + phase)
    avg_soc = _clamp(avg_soc_start - avg_soc_decline + avg_soc_wave, 5.0, 98.0)

    min_soc_spread = 5.0 + min(12.0, length_km * 0.35 + stop_count * 0.12)
    min_soc_wave = 1.5 * math.cos((t / 14.0) + phase * 0.7)
    max_min_soc = max(0.0, avg_soc - 0.2)
    min_soc = _clamp(avg_soc - min_soc_spread + min_soc_wave, 0.0, max_min_soc)

    ec_rate = (
        0.18 * max(trip_count, 1)
        + 0.55 * max(length_km, 1.0)
        + 0.06 * max(stop_count, 1)
    )
    cumulative_ec = max(0.0, ec_rate * max(t, 0.0))

    return RouteSummary(
        route_id=route_id,
        route_name=route_name,
        status=_status_from_min_soc(min_soc),
        avg_soc=round(avg_soc, 1),
        min_soc=round(min_soc, 1),
        cumulative_ec=round(cumulative_ec, 1),
        active_trip_count=active_trip_count,
    )


def _uploaded_seek_events(
    route_summaries_now: List[RouteSummary],
    uploaded_routes: List[Dict[str, object]],
    t_prev: float,
    t: float,
) -> List[ThresholdEvent]:
    if t == t_prev:
        return []

    summaries_prev = {
        summary.route_id: summary
        for summary in [
            _route_summary_from_uploaded_meta(route_meta, t_prev, idx)
            for idx, route_meta in enumerate(uploaded_routes)
        ]
    }

    events: List[ThresholdEvent] = []
    for summary_now in route_summaries_now:
        summary_prev = summaries_prev.get(summary_now.route_id)
        if summary_prev is None:
            continue

        prev_rank = _STATUS_RANK.get(summary_prev.status, 0)
        now_rank = _STATUS_RANK.get(summary_now.status, 0)
        if now_rank <= prev_rank:
            continue

        events.append(
            ThresholdEvent(
                event_type=summary_now.status,
                route_id=summary_now.route_id,
                t=t,
                message="Route {name} entered {status} state".format(
                    name=summary_now.route_name,
                    status=summary_now.status,
                ),
            )
        )

    return events


def get_simulation_state(request: SimulationStateRequest) -> SimulationStateResponse:
    active_feed = get_active_feed()
    if active_feed is not None:
        uploaded_routes: List[Dict[str, object]] = list(active_feed.get("routes") or [])

        route_summaries = [
            _route_summary_from_uploaded_meta(route_meta, request.t, idx)
            for idx, route_meta in enumerate(uploaded_routes)
        ]

        selected_route = None
        if request.selected_route_id:
            selected_route = next(
                (route for route in route_summaries if route.route_id == request.selected_route_id),
                None,
            )

        if selected_route is not None:
            _routezero.get_ec_windows(route_id=selected_route.route_id, t=request.t)

        events: List[ThresholdEvent] = []
        if request.mode == "seek" and request.t_prev is not None:
            events = _uploaded_seek_events(route_summaries, uploaded_routes, request.t_prev, request.t)

        return SimulationStateResponse(
            current_time=request.t,
            routes=route_summaries,
            selected_route=selected_route,
            events=events,
        )

    trips_by_route: Dict[str, List[TripInstance]] = defaultdict(list)
    for trip in MOCK_TRIPS:
        trips_by_route[trip.route_id].append(trip)

    route_summaries = [
        summarize_route_at_t(route_id, route_name, trips_by_route.get(route_id, []), request.t)
        for route_id, route_name in ROUTE_CATALOG
    ]

    selected_route = None
    if request.selected_route_id:
        selected_route = next(
            (route for route in route_summaries if route.route_id == request.selected_route_id),
            None,
        )

    # Boundary call kept intentionally lightweight for future sim+ integration.
    if selected_route is not None:
        _routezero.get_ec_windows(route_id=selected_route.route_id, t=request.t)

    events: List[ThresholdEvent] = []
    if request.mode == "seek" and request.t_prev is not None:
        events = _get_interval_events(MOCK_TRIPS, request.t_prev, request.t)

    return SimulationStateResponse(
        current_time=request.t,
        routes=route_summaries,
        selected_route=selected_route,
        events=events,
    )
