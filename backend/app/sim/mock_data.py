from __future__ import annotations

from typing import List, Tuple

from app.sim.models import ECWindow, TripInstance

SIMULATION_HORIZON = 240

ROUTE_CATALOG: List[Tuple[str, str]] = [
    ("R1", "Route 1"),
    ("R2", "Route 2"),
    ("R3", "Route 3"),
    ("R4", "Route 4"),
]

MOCK_TRIPS: List[TripInstance] = [
    TripInstance(
        trip_id="R1-T1",
        route_id="R1",
        route_name="Route 1",
        start_time=0,
        end_time=120,
        initial_soc=92.0,
        battery_capacity_kwh=300.0,
        ec_windows=[
            ECWindow(start_time=0, end_time=30, energy_kwh=18.0),
            ECWindow(start_time=30, end_time=60, energy_kwh=20.0),
            ECWindow(start_time=60, end_time=90, energy_kwh=22.0),
            ECWindow(start_time=90, end_time=120, energy_kwh=24.0),
        ],
    ),
    TripInstance(
        trip_id="R1-T2",
        route_id="R1",
        route_name="Route 1",
        start_time=80,
        end_time=200,
        initial_soc=88.0,
        battery_capacity_kwh=300.0,
        ec_windows=[
            ECWindow(start_time=80, end_time=110, energy_kwh=15.0),
            ECWindow(start_time=110, end_time=140, energy_kwh=18.0),
            ECWindow(start_time=140, end_time=170, energy_kwh=20.0),
            ECWindow(start_time=170, end_time=200, energy_kwh=22.0),
        ],
    ),
    TripInstance(
        trip_id="R1-T3",
        route_id="R1",
        route_name="Route 1",
        start_time=150,
        end_time=240,
        initial_soc=85.0,
        battery_capacity_kwh=280.0,
        ec_windows=[
            ECWindow(start_time=150, end_time=180, energy_kwh=16.0),
            ECWindow(start_time=180, end_time=210, energy_kwh=18.0),
            ECWindow(start_time=210, end_time=240, energy_kwh=20.0),
        ],
    ),
    TripInstance(
        trip_id="R2-T1",
        route_id="R2",
        route_name="Route 2",
        start_time=20,
        end_time=150,
        initial_soc=78.0,
        battery_capacity_kwh=260.0,
        ec_windows=[
            ECWindow(start_time=20, end_time=50, energy_kwh=24.0),
            ECWindow(start_time=50, end_time=80, energy_kwh=26.0),
            ECWindow(start_time=80, end_time=110, energy_kwh=28.0),
            ECWindow(start_time=110, end_time=150, energy_kwh=36.0),
        ],
    ),
    TripInstance(
        trip_id="R2-T2",
        route_id="R2",
        route_name="Route 2",
        start_time=100,
        end_time=230,
        initial_soc=72.0,
        battery_capacity_kwh=250.0,
        ec_windows=[
            ECWindow(start_time=100, end_time=130, energy_kwh=24.0),
            ECWindow(start_time=130, end_time=160, energy_kwh=26.0),
            ECWindow(start_time=160, end_time=190, energy_kwh=28.0),
            ECWindow(start_time=190, end_time=230, energy_kwh=38.0),
        ],
    ),
    TripInstance(
        trip_id="R3-T1",
        route_id="R3",
        route_name="Route 3",
        start_time=40,
        end_time=180,
        initial_soc=70.0,
        battery_capacity_kwh=220.0,
        ec_windows=[
            ECWindow(start_time=40, end_time=70, energy_kwh=26.0),
            ECWindow(start_time=70, end_time=100, energy_kwh=30.0),
            ECWindow(start_time=100, end_time=130, energy_kwh=34.0),
            ECWindow(start_time=130, end_time=180, energy_kwh=48.0),
        ],
    ),
    TripInstance(
        trip_id="R3-T2",
        route_id="R3",
        route_name="Route 3",
        start_time=160,
        end_time=240,
        initial_soc=68.0,
        battery_capacity_kwh=220.0,
        ec_windows=[
            ECWindow(start_time=160, end_time=190, energy_kwh=26.0),
            ECWindow(start_time=190, end_time=220, energy_kwh=30.0),
            ECWindow(start_time=220, end_time=240, energy_kwh=26.0),
        ],
    ),
    TripInstance(
        trip_id="R4-T1",
        route_id="R4",
        route_name="Route 4",
        start_time=0,
        end_time=140,
        initial_soc=65.0,
        battery_capacity_kwh=200.0,
        ec_windows=[
            ECWindow(start_time=0, end_time=30, energy_kwh=24.0),
            ECWindow(start_time=30, end_time=60, energy_kwh=26.0),
            ECWindow(start_time=60, end_time=90, energy_kwh=28.0),
            ECWindow(start_time=90, end_time=120, energy_kwh=30.0),
            ECWindow(start_time=120, end_time=140, energy_kwh=24.0),
        ],
    ),
    TripInstance(
        trip_id="R4-T2",
        route_id="R4",
        route_name="Route 4",
        start_time=120,
        end_time=240,
        initial_soc=60.0,
        battery_capacity_kwh=210.0,
        ec_windows=[
            ECWindow(start_time=120, end_time=150, energy_kwh=24.0),
            ECWindow(start_time=150, end_time=180, energy_kwh=28.0),
            ECWindow(start_time=180, end_time=210, energy_kwh=30.0),
            ECWindow(start_time=210, end_time=240, energy_kwh=34.0),
        ],
    ),
]
