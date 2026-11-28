"""Read-only API for the global bookmaker discovery directory."""
import os

from fastapi import APIRouter, HTTPException, Query

from app.providers.bookmaker_directory import BookmakerDirectory

router = APIRouter(prefix="/api/v1/bookmakers", tags=["bookmakers"])
_market_store = None


def configure_market_store(store) -> None:
    """Inject the application's shared market store for discovery lookups."""
    global _market_store
    _market_store = store


bookmaker_directory = BookmakerDirectory(
    database_path=os.getenv("FOOTBALL_INTEL_DB_PATH", "data/football_intel.sqlite3")
)


@router.get("/discovery/suggested-links")
def suggested_bookmaker_source_links(
    provider_id: str | None = Query(default=None, min_length=1, max_length=100),
    limit: int = Query(default=5000, ge=1, le=5000),
):
    """Suggest exact-name matches for provider books; never auto-links identities."""
    if _market_store is None:
        raise HTTPException(status_code=503, detail="market discovery store is not configured")
    items = _market_store.discovery_inventory(
        provider=provider_id, stage="books", limit=limit
    )
    # Inventory is newest-first. Use only the latest observed label for each
    # provider-native ID; do not let old display names create duplicate suggestions.
    latest = {}
    for item in items:
        key = (item.get("provider"), item.get("source_id") or item.get("name"))
        if key not in latest:
            latest[key] = item
    suggestions = bookmaker_directory.suggest_source_identity_matches(latest.values())
    counts = {}
    for suggestion in suggestions:
        state = suggestion["suggestion_status"]
        counts[state] = counts.get(state, 0) + 1
    return {
        "provider_filter": provider_id,
        "source_books_considered": len(suggestions),
        "suggestion_counts": counts,
        "suggestions": suggestions,
        "note": "Exact normalized-name matches are suggestions only. Review evidence and create a source identity link through a trusted administrative workflow.",
    }


@router.get("/summary")
def bookmaker_summary():
    """Summarize discovery and verification states without implying global coverage."""
    return bookmaker_directory.summary()


@router.get("")
def list_bookmakers(
    q: str | None = Query(default=None, min_length=1, max_length=100),
    integration_status: str | None = None,
    verification_status: str | None = None,
    region: str | None = Query(default=None, min_length=2, max_length=3),
):
    """List discovery candidates, optionally filtered by evidence-backed state or region."""
    profiles = bookmaker_directory.list_profiles(query=q, region=region)
    allowed_integration = {
        "not_connected", "access_review", "authorised", "connected",
        "ingestion_verified", "temporarily_unavailable", "disabled",
    }
    allowed_verification = {
        "not_verified", "partially_verified", "verified", "rejected",
    }
    if integration_status:
        if integration_status not in allowed_integration:
            raise HTTPException(status_code=422, detail="unsupported integration_status")
        profiles = [
            item for item in profiles
            if item["integration_status"] == integration_status
        ]
    if verification_status:
        if verification_status not in allowed_verification:
            raise HTTPException(status_code=422, detail="unsupported verification_status")
        profiles = [
            item for item in profiles
            if item["verification_status"] == verification_status
        ]
    return {
        "count": len(profiles),
        "bookmakers": profiles,
        "coverage_note": (
            "Directory presence is not proof of live access, data rights, "
            "regional availability or complete market coverage. Region filters "
            "include only regions backed by a recorded evidence review."
        ),
    }


@router.get("/{operator_id}/coverage")
def get_bookmaker_coverage(operator_id: str):
    """Report provider observations mapped to an operator through verified links."""
    try:
        profile = bookmaker_directory.get(operator_id)
        links = bookmaker_directory.list_source_links(profile.operator_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if _market_store is None:
        raise HTTPException(status_code=503, detail="market discovery store is not configured")

    verified_links = [link for link in links if link["verification_status"] == "verified"]
    candidate_links = [link for link in links if link["verification_status"] == "candidate"]
    rejected_links = [link for link in links if link["verification_status"] == "rejected"]

    # Query only providers referenced by verified identity links. This avoids a
    # full historical-market scan as the global data store grows.
    reports_by_provider = {}
    for provider_id in sorted({link["provider_id"] for link in verified_links}):
        reports_by_provider[provider_id] = _market_store.source_book_coverage_report(
            provider=provider_id
        )
    index = {
        (provider_id, item["source_book_id"]): item
        for provider_id, report in reports_by_provider.items()
        for item in report["source_books"]
    }
    mapped_observations = []
    verified_without_data = []
    for link in verified_links:
        observed = index.get((link["provider_id"], link["source_book_id"]))
        if observed:
            mapped_observations.append(observed)
        else:
            verified_without_data.append(link)
    if mapped_observations:
        state = "observations_found"
    elif verified_links:
        state = "verified_identity_without_market_observations"
    else:
        state = "no_verified_source_identity"

    return {
        "operator_id": profile.operator_id,
        "display_name": profile.display_name,
        "coverage_state": state,
        "verified_source_links": verified_links,
        "candidate_source_links_not_counted": candidate_links,
        "rejected_source_links": rejected_links,
        "verified_links_without_observations": verified_without_data,
        "observed_market_coverage": mapped_observations,
        "note": (
            "This is measured feed observation coverage only. It does not prove "
            "that every sport, event, market, selection, region or live package "
            "offered by the bookmaker has been collected."
        ),
    }


@router.get("/{operator_id}/sources")
def list_bookmaker_sources(operator_id: str):
    """List provider-native identities associated with a bookmaker, including candidates."""
    try:
        profile = bookmaker_directory.get(operator_id)
        links = bookmaker_directory.list_source_links(profile.operator_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "operator_id": profile.operator_id,
        "source_links": links,
        "note": "Candidate links are not treated as verified identity matches until evidence is reviewed.",
    }


@router.get("/{operator_id}")
def get_bookmaker(operator_id: str):
    """Return one bookmaker's discovery, access and evidence record."""
    from dataclasses import asdict
    try:
        profile = bookmaker_directory.get(operator_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return asdict(profile)
