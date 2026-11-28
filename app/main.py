"""FastAPI application for Football Intel."""
import os

from fastapi import FastAPI, Query, HTTPException
from app.models import AnalysisRequest, AnalysisResponse
from app.providers.base import ProviderMarket, ProviderSelection
from app.services.analysis import analyze_fixture
from app.services.sqlite_store import SQLiteMarketStore
from app.services.market_movement import summarize_odds_movement
from app.services.market_taxonomy import MarketTaxonomyRegistry
from app.services.data_quality import assess_market_freshness
from app.services.settlement_rules import compare_settlement_profiles
from app.api.features import router as feature_router, settlement_rule_registry
from app.api.bookmakers import router as bookmaker_router, configure_market_store

market_taxonomy = MarketTaxonomyRegistry()
market_store = SQLiteMarketStore(
    os.getenv("FOOTBALL_INTEL_DB_PATH", "data/football_intel.sqlite3")
)
configure_market_store(market_store)

app = FastAPI(
    title="Football Intel API",
    description=(
        "A transparent sports-intelligence foundation. Experimental estimates "
        "use supplied statistics only; provider feeds require separate authorisation."
    ),
    version="0.2.0",
)


app.include_router(feature_router)
app.include_router(bookmaker_router)


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


@app.get("/api/v1/settlement-rules")
def settlement_rule_profiles():
    """List bookmaker settlement profiles that have been explicitly registered."""
    profiles = settlement_rule_registry.list_profiles()
    return {
        "profiles": profiles,
        "verified_profile_count": sum(
            item["verification_status"] == "verified" for item in profiles
        ),
        "note": "No bookmaker settlement profile is pre-verified; official rule evidence is required.",
    }


@app.get("/api/v1/settlement-rules/compare")
def compare_settlement_rules(left_profile_id: str, right_profile_id: str):
    """Compare two registered bookmaker settlement profiles."""
    from fastapi import HTTPException
    try:
        left = settlement_rule_registry.get(left_profile_id)
        right = settlement_rule_registry.get(right_profile_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return compare_settlement_profiles(left, right)


@app.get("/api/v1/taxonomy/definitions")
def taxonomy_definitions():
    """List the canonical market vocabulary currently supported."""
    return {
        "taxonomy_version": "1.0",
        "definitions": market_taxonomy.definitions(),
        "provider_mappings_loaded": 0,
        "note": "Only explicitly verified provider mappings may classify source markets.",
    }


@app.get("/api/v1/providers/{provider_id}/events/{source_event_id}/freshness")
def event_market_freshness(
    provider_id: str,
    source_event_id: str,
    max_age_seconds: int = Query(default=300, ge=0, le=86400),
):
    """Assess collection recency separately from provider-source freshness."""
    snapshots = market_store.snapshots_for_event(provider_id, source_event_id, limit=1)
    latest = snapshots[0] if snapshots else None
    results = []
    for market in (latest or {}).get("markets", []):
        results.append({
            "source_market_id": market.get("source_market_id"),
            "source_market_name": market.get("name"),
            "freshness": assess_market_freshness(
                market,
                latest["captured_at"],
                max_age_seconds=max_age_seconds,
            ),
        })
    return {
        "provider": provider_id,
        "source_event_id": source_event_id,
        "snapshot_found": latest is not None,
        "markets": results,
    }


@app.get("/api/v1/integrations/sportradar/status")
def sportradar_integration_status():
    """Report local configuration only; this endpoint does not make a paid API call."""
    configured = bool(os.getenv("SPORTRADAR_ODDS_API_KEY"))
    return {
        "provider": "sportradar-prematch",
        "configured": configured,
        "package": "prematch",
        "access_level": os.getenv("SPORTRADAR_ACCESS_LEVEL", "trial"),
        "access_tier": "not_checked",
        "note": "The actual access tier is determined from the X-Origin-Id response header after an authenticated Books request.",
        "next_step": "Configure the server-side API key and run scripts/collect_sportradar_prematch.py" if not configured else "Run the Prematch collection script to verify live access and actual bookmaker coverage.",
    }


@app.get("/api/v1/discovery/inventory")
def discovery_inventory(
    provider_id: str | None = None,
    stage: str | None = None,
    limit: int = Query(default=500, ge=1, le=5000),
):
    """Return the raw Books/Sports/Competitions/Stages inventory discovered by provider scans."""
    try:
        return {
            "items": market_store.discovery_inventory(
                provider=provider_id, stage=stage, limit=limit
            )
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/v1/capabilities")
def provider_capabilities(provider_id: str | None = None):
    """Report provider sports, event, package and market capabilities from observations."""
    return market_store.provider_capability_report(provider=provider_id)


@app.get("/api/v1/providers/{provider_id}/capabilities")
def one_provider_capabilities(provider_id: str):
    """Return observed capabilities for one provider; unknown providers return 404."""
    report = market_store.provider_capability_report(provider=provider_id)
    if not report["providers"]:
        raise HTTPException(status_code=404, detail="No observations recorded for this provider")
    return report["providers"][provider_id]


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
            "classification": market_taxonomy.classify(
                provider_market,
                sport=market_store.event_sport(provider_id, source_event_id),
            ),
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
    book_id: str | None = Query(default=None),
):
    """Summarize observed decimal-odds movement for one provider-native selection."""
    try:
        history = market_store.selection_price_history(
            provider_id, source_event_id, source_market_id, source_selection_id,
            limit, source_book_id=book_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "provider": provider_id,
        "source_event_id": source_event_id,
        "source_market_id": source_market_id,
        "source_selection_id": source_selection_id,
        "source_book_id": book_id,
        "observations": history,
        "movement": summarize_odds_movement(history),
    }


@app.post("/api/v1/analyze", response_model=AnalysisResponse)
def analyze(request: AnalysisRequest):
    """Analyze a fixture from user-supplied team statistics."""
    return analyze_fixture(request)
