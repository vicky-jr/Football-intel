"""FastAPI application for Football Intel."""
import os

from fastapi import FastAPI, Query
from app.models import AnalysisRequest, AnalysisResponse
from app.services.analysis import analyze_fixture
from app.services.sqlite_store import SQLiteMarketStore
from app.services.market_movement import summarize_odds_movement
from app.services.market_taxonomy import MarketTaxonomyRegistry

market_taxonomy = MarketTaxonomyRegistry()

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


@app.get("/api/v1/taxonomy/definitions")
def taxonomy_definitions():
    """List the canonical market vocabulary currently supported."""
    return {
        "taxonomy_version": "1.0",
        "definitions": market_taxonomy.definitions(),
        "provider_mappings_loaded": 0,
        "note": "Only explicitly verified provider mappings may classify source markets.",
    }


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


@app.get(
    "/api/v1/providers/{provider_id}/events/{source_event_id}/taxonomy"
)
def event_market_taxonomy(
    provider_id: str,
    source_event_id: str,
    limit: int = Query(default=1, ge=1, le=500),
):
    """Show conservative canonical classifications for captured event markets."""
    snapshots = market_store.snapshots_for_event(provider_id, source_event_id, limit=limit)
    latest = snapshots[0] if snapshots else None
    results = []
    for market in (latest or {}).get("markets", []):
        source = {
            "provider": market.get("provider", provider_id),
            "source_event_id": market.get("source_event_id", source_event_id),
            "source_market_id": market.get("source_market_id"),
            "name": market.get("name", ""),
            "period": market.get("period"),
            "line": market.get("line"),
            "status": market.get("status"),
            "selections": [],
        }
        from app.providers.base import ProviderMarket, ProviderSelection
        source["selections"] = [
            ProviderSelection(
                item.get("source_selection_id"),
                item.get("name", ""),
                item.get("odds_decimal"),
                item.get("participant"),
                item.get("raw") or {},
            )
            for item in market.get("selections", [])
        ]
        provider_market = ProviderMarket(**source)
        results.append({
            "source_market_id": provider_market.source_market_id,
            "source_market_name": provider_market.name,
            "source_period": provider_market.period,
            "source_line": provider_market.line,
            "classification": market_taxonomy.classify(provider_market),
        })
    return {
        "provider": provider_id,
        "source_event_id": source_event_id,
        "captured_at": latest.get("captured_at") if latest else None,
        "markets": results,
    }


@app.get(
    "/api/v1/providers/{provider_id}/events/{source_event_id}/markets/"
    "{source_market_id}/selections/{source_selection_id}/movement"
)
def selection_movement(
    provider_id: str,
    source_event_id: str,
    source_market_id: str,
    source_selection_id: str,
    limit: int = Query(default=500, ge=1, le=2000),
):
    """Summarize observed decimal-odds movement for one provider-native selection."""
    history = market_store.selection_price_history(
        provider_id, source_event_id, source_market_id, source_selection_id, limit
    )
    return {
        "provider": provider_id,
        "source_event_id": source_event_id,
        "source_market_id": source_market_id,
        "source_selection_id": source_selection_id,
        "observations": history,
        "movement": summarize_odds_movement(history),
    }


@app.post("/api/v1/analyze", response_model=AnalysisResponse)
def analyze(request: AnalysisRequest):
    """Analyze a fixture from user-supplied team statistics."""
    return analyze_fixture(request)
