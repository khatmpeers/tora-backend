from __future__ import annotations

import csv
import io
import math
import re
import zipfile
from collections import defaultdict
from typing import Dict, List, Optional, Sequence, Tuple


def parse_gtfs_zip(content: bytes) -> Dict[str, object]:
    if not content:
        raise ValueError("Uploaded GTFS zip is empty")

    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile as exc:
        raise ValueError("Invalid zip file") from exc

    with archive:
        routes_rows = _read_csv_rows(archive, "routes.txt", required=True)
        trips_rows = _read_csv_rows(archive, "trips.txt", required=True)
        stops_rows = _read_csv_rows(archive, "stops.txt", required=True)
        stop_times_rows = _read_csv_rows(archive, "stop_times.txt", required=True)
        shapes_rows = _read_csv_rows(archive, "shapes.txt", required=False)

    routes = _build_routes(
        routes_rows=routes_rows,
        trips_rows=trips_rows,
        stops_rows=stops_rows,
        stop_times_rows=stop_times_rows,
        shapes_rows=shapes_rows,
    )

    return {
        "feed_loaded": True,
        "route_count": len(routes),
        "routes": routes,
    }


def _build_routes(
    *,
    routes_rows: List[Dict[str, str]],
    trips_rows: List[Dict[str, str]],
    stops_rows: List[Dict[str, str]],
    stop_times_rows: List[Dict[str, str]],
    shapes_rows: List[Dict[str, str]],
) -> List[Dict[str, object]]:
    route_rows_in_order = []
    seen_routes = set()
    for row in routes_rows:
        route_id = (row.get("route_id") or "").strip()
        if not route_id or route_id in seen_routes:
            continue
        seen_routes.add(route_id)
        route_rows_in_order.append(row)

    trip_to_meta: Dict[str, Dict[str, str]] = {}
    trips_by_route: Dict[str, List[str]] = defaultdict(list)
    for row in trips_rows:
        trip_id = (row.get("trip_id") or "").strip()
        route_id = (row.get("route_id") or "").strip()
        if not trip_id or not route_id:
            continue

        shape_id = (row.get("shape_id") or "").strip()
        trip_to_meta[trip_id] = {
            "route_id": route_id,
            "shape_id": shape_id,
        }
        trips_by_route[route_id].append(trip_id)

    stops_by_id: Dict[str, Tuple[float, float]] = {}
    stop_name_by_id: Dict[str, str] = {}
    for row in stops_rows:
        stop_id = (row.get("stop_id") or "").strip()
        if not stop_id:
            continue

        lat = _safe_float(row.get("stop_lat"))
        lon = _safe_float(row.get("stop_lon"))
        if lat is None or lon is None:
            continue

        stops_by_id[stop_id] = (lat, lon)
        stop_name_by_id[stop_id] = (row.get("stop_name") or "").strip() or stop_id

    stop_times_by_trip: Dict[str, List[Tuple[int, str]]] = defaultdict(list)
    for row in stop_times_rows:
        trip_id = (row.get("trip_id") or "").strip()
        stop_id = (row.get("stop_id") or "").strip()
        if not trip_id or not stop_id:
            continue

        stop_sequence = _safe_int(row.get("stop_sequence"), fallback=10**9)
        stop_times_by_trip[trip_id].append((stop_sequence, stop_id))

    for trip_id in list(stop_times_by_trip.keys()):
        stop_times_by_trip[trip_id].sort(key=lambda item: item[0])

    shape_to_coordinates: Dict[str, List[List[float]]] = {}
    shape_to_length_km: Dict[str, float] = {}
    if shapes_rows:
        shape_points: Dict[str, List[Tuple[int, float, float]]] = defaultdict(list)
        for row in shapes_rows:
            shape_id = (row.get("shape_id") or "").strip()
            if not shape_id:
                continue

            lat = _safe_float(row.get("shape_pt_lat"))
            lon = _safe_float(row.get("shape_pt_lon"))
            if lat is None or lon is None:
                continue

            seq = _safe_int(row.get("shape_pt_sequence"), fallback=10**9)
            shape_points[shape_id].append((seq, lat, lon))

        for shape_id, points in shape_points.items():
            points.sort(key=lambda item: item[0])
            coords = _dedupe_consecutive([[lat, lon] for _, lat, lon in points])
            shape_to_coordinates[shape_id] = coords
            shape_to_length_km[shape_id] = _route_length_km(coords)

    parsed_routes: List[Dict[str, object]] = []
    for route_row in route_rows_in_order:
        route_id = (route_row.get("route_id") or "").strip()
        route_name = _route_name(route_row, route_id)

        trip_ids = trips_by_route.get(route_id, [])
        trip_count = len(trip_ids)

        representative_trip_id = trip_ids[0] if trip_ids else None
        stop_points = _stop_points_for_trip(
            representative_trip_id,
            stop_times_by_trip,
            stops_by_id,
            stop_name_by_id,
        )

        stop_ids = set()
        for trip_id in trip_ids:
            for _, stop_id in stop_times_by_trip.get(trip_id, []):
                if stop_id in stops_by_id:
                    stop_ids.add(stop_id)
        stop_count = len(stop_ids)

        coordinates: List[List[float]] = []
        geometry_source = "stops"

        if shape_to_coordinates:
            candidate_shape_ids = []
            seen_candidate_shape_ids = set()
            for trip_id in trip_ids:
                shape_id = (trip_to_meta.get(trip_id) or {}).get("shape_id", "")
                if not shape_id or shape_id not in shape_to_coordinates:
                    continue
                if shape_id in seen_candidate_shape_ids:
                    continue
                seen_candidate_shape_ids.add(shape_id)
                candidate_shape_ids.append(shape_id)

            if candidate_shape_ids:
                candidates = [
                    {
                        "shape_id": shape_id,
                        "coordinates": shape_to_coordinates[shape_id],
                        "point_count": len(shape_to_coordinates[shape_id]),
                        "length_km": float(shape_to_length_km.get(shape_id, 0.0)),
                    }
                    for shape_id in candidate_shape_ids
                ]

                valid_candidates = [
                    item
                    for item in candidates
                    if item["point_count"] >= 10 and item["length_km"] >= 1.0
                ]

                if valid_candidates:
                    canonical_candidate = max(
                        valid_candidates,
                        key=lambda item: (item["length_km"], item["point_count"], item["shape_id"]),
                    )
                else:
                    canonical_candidate = max(
                        candidates,
                        key=lambda item: (item["length_km"], item["point_count"], item["shape_id"]),
                    )

                coordinates = list(canonical_candidate["coordinates"])
                geometry_source = "shapes"

        if not coordinates:
            coordinates = [[point["lat"], point["lon"]] for point in stop_points]
            coordinates = _dedupe_consecutive(coordinates)

        route_length_km = _route_length_km(coordinates)

        parsed_routes.append(
            {
                "route_id": route_id,
                "route_name": route_name,
                "trip_count": trip_count,
                "stop_count": stop_count,
                "geometry_source": geometry_source,
                "coordinates": coordinates,
                "stop_points": stop_points,
                "length_km": round(route_length_km, 3),
            }
        )

    return parsed_routes


def _stop_points_for_trip(
    trip_id: Optional[str],
    stop_times_by_trip: Dict[str, List[Tuple[int, str]]],
    stops_by_id: Dict[str, Tuple[float, float]],
    stop_name_by_id: Dict[str, str],
) -> List[Dict[str, object]]:
    if trip_id is None:
        return []

    stop_points: List[Dict[str, object]] = []
    seen_consecutive_stop_id: Optional[str] = None

    for _, stop_id in stop_times_by_trip.get(trip_id, []):
        stop_coord = stops_by_id.get(stop_id)
        if stop_coord is None:
            continue

        if stop_id == seen_consecutive_stop_id:
            continue

        stop_points.append(
            {
                "stop_id": stop_id,
                "stop_name": stop_name_by_id.get(stop_id, stop_id),
                "lat": float(stop_coord[0]),
                "lon": float(stop_coord[1]),
            }
        )
        seen_consecutive_stop_id = stop_id

    return stop_points


def _read_csv_rows(archive: zipfile.ZipFile, filename: str, required: bool) -> List[Dict[str, str]]:
    member_name = _find_member_name(archive, filename)
    if member_name is None:
        if required:
            raise ValueError("Missing required GTFS file: {name}".format(name=filename))
        return []

    with archive.open(member_name, "r") as handle:
        text_handle = io.TextIOWrapper(handle, encoding="utf-8-sig", newline="")
        reader = csv.DictReader(text_handle)
        if not reader.fieldnames:
            return []

        rows: List[Dict[str, str]] = []
        for row in reader:
            normalized_row = {}
            for key, value in row.items():
                normalized_key = (key or "").strip()
                normalized_value = value.strip() if isinstance(value, str) else ""
                normalized_row[normalized_key] = normalized_value
            rows.append(normalized_row)
        return rows


def _find_member_name(archive: zipfile.ZipFile, filename: str) -> Optional[str]:
    wanted = filename.lower()
    matches: List[str] = []
    for member in archive.namelist():
        base_name = member.rsplit("/", 1)[-1].lower()
        if base_name == wanted:
            matches.append(member)

    if not matches:
        return None

    matches.sort(key=lambda item: (len(item), item))
    return matches[0]


def _safe_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Optional[str], fallback: int = 0) -> int:
    if value is None:
        return fallback
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return fallback


def _is_placeholder_value(value: str) -> bool:
    normalized = value.strip().lower()
    if not normalized:
        return True

    explicit_invalid = {
        "{short_name}",
        "{long_name}",
        "${short_name}",
        "${long_name}",
    }
    if normalized in explicit_invalid:
        return True

    if re.match(r"^\$?\{[^}]+\}$", normalized):
        return True

    return False


def _route_name(route_row: Dict[str, str], route_id: str) -> str:
    short_name = (route_row.get("route_short_name") or "").strip()
    long_name = (route_row.get("route_long_name") or "").strip()

    short_valid = not _is_placeholder_value(short_name)
    long_valid = not _is_placeholder_value(long_name)

    if short_valid and long_valid:
        if short_name.lower() == long_name.lower():
            return short_name
        return f"{short_name} {long_name}".strip()
    if short_valid:
        return short_name
    if long_valid:
        return long_name
    return "Route {route_id}".format(route_id=route_id)


def _dedupe_consecutive(coordinates: Sequence[Sequence[float]]) -> List[List[float]]:
    deduped: List[List[float]] = []
    last: Optional[Tuple[float, float]] = None

    for pair in coordinates:
        if len(pair) != 2:
            continue

        lat = float(pair[0])
        lon = float(pair[1])
        current = (lat, lon)
        if current == last:
            continue

        deduped.append([lat, lon])
        last = current

    return deduped


def _route_length_km(coordinates: Sequence[Sequence[float]]) -> float:
    if len(coordinates) < 2:
        return 0.0

    total = 0.0
    for idx in range(1, len(coordinates)):
        lat1, lon1 = float(coordinates[idx - 1][0]), float(coordinates[idx - 1][1])
        lat2, lon2 = float(coordinates[idx][0]), float(coordinates[idx][1])
        total += _haversine_km(lat1, lon1, lat2, lon2)

    return total


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0088

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * (math.sin(dlon / 2.0) ** 2)
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return radius_km * c
