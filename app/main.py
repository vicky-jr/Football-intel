"""FastAPI application for Football Intel."""
import os

from fastapi import FastAPI, Query
from app.models import AnalysisRequest, AnalysisResponse
from app.services.analysis import analyze_fixture
from app.services.sqlite_store import SQLiteMarketStore

market_store = SQLiteMarketStore(
    os.getenv("FOOTBALL_INTEL_DB_PATH", "data/football_intel.sqlite3")
)

app = FastAPI(
    title="Football Intel API",
    description=(
        "A transparent sports-intelligence foundation. Experimental estimates "
        "use supplied statistics only; provider feeds require separate authorisation."
    ),
    version="0.2.0",
)


@app.get("/")
def root():
    return {
        "name": "Football Intel API",
        "version": app.version,
        "docs": "/docs",
        "coverage": "/api/v1/coverage",
    }


@app.get("/health")
def health():
    return {"status": "ok", "storage": "sqlite"}


@app.get("/api/v1/coverage")
def coverage():
    """Return persisted market-observation coverage by provider."""
    return market_store.coverage_report()


@app.get("/api/v1/scans")
def scans(limit: int = Query(default=50, ge=1, le=500)):
    """Return recent provider scan runs, including partial failures."""
    return {"scans": market_store.scan_history(limit=limit)}


@app.get("/api/v1/providers/{provider_id}/events/{source_event_id}/snapshots")
def event_market_snapshots(
    provider_id: str,
    source_event_id: str,
    limit: int = Query(default=100, ge=1, le=500),
):
    """Return the original market and selection payloads captured for an event."""
    return {
        "provider": provider_id,
        "source_event_id": source_event_id,
        "snapshots": market_store.snapshots_for_event(
            provider_id, source_event_id, limit=limit
        ),
    }


@app.post("/api/v1/analyze", response_model=AnalysisResponse)
def analyze(request: AnalysisRequest):
    """Analyze a fixture from user-supplied team statistics."""
    return analyze_fixture(request)
