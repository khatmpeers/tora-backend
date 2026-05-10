from __future__ import annotations

from typing import List

from app.sim.models import ECWindow


class RouteZeroAdapter:
    """Pass 1 stub for future RouteZero EC integration."""

    def get_ec_windows(self, *, route_id: str, t: float) -> List[ECWindow]:
        # Placeholder output to preserve integration boundaries for later passes.
        return [
            ECWindow(
                start_time=max(t - 15, 0),
                end_time=t,
                energy_kwh=0.0,
            )
        ]
