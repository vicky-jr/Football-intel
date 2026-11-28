"""Read-only API for the global bookmaker discovery directory."""
import os

from fastapi import APIRouter, HTTPException, Query

from app.providers.bookmaker_directory import BookmakerDirectory

router = APIRouter(prefix="/api/v1/bookmakers", tags=["bookmakers"])
bookmaker_directory = BookmakerDirectory(
    database_path=os.getenv("FOOTBALL_INTEL_DB_PATH", "data/football_intel.sqlite3")
)


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
