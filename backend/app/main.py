from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.gtfs.parser import parse_gtfs_zip
from app.gtfs.store import get_active_feed, set_active_feed
from app.schemas import (
    GTFSRoutesResponse,
    SimulationStateRequest,
    SimulationStateResponse,
)
from app.sim.engine import get_simulation_state

app = FastAPI(title="Tora Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/simulation/state", response_model=SimulationStateResponse)
def simulation_state(payload: SimulationStateRequest) -> SimulationStateResponse:
    return get_simulation_state(payload)


@app.post("/gtfs/upload", response_model=GTFSRoutesResponse)
async def upload_gtfs(file: UploadFile = File(...)) -> GTFSRoutesResponse:
    filename = (file.filename or "").lower()
    if not filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Expected a .zip GTFS upload")

    payload = await file.read()
    try:
        parsed_feed = parse_gtfs_zip(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    set_active_feed(parsed_feed)
    return GTFSRoutesResponse.model_validate(parsed_feed)


@app.get("/gtfs/routes", response_model=GTFSRoutesResponse)
def get_gtfs_routes() -> GTFSRoutesResponse:
    feed = get_active_feed()
    if feed is None:
        return GTFSRoutesResponse(feed_loaded=False, route_count=0, routes=[])
    return GTFSRoutesResponse.model_validate(feed)
