"""Read-only API for the global bookmaker discovery directory."""
from fastapi import APIRouter, HTTPException, Query

from app.providers.bookmaker_directory import BookmakerDirectory

router = APIRouter(prefix="/api/v1/bookmakers", tags=["bookmakers"])
bookmaker_directory = BookmakerDirectory()


@router.get("")
def list_bookmakers(
    q: str | None = Query(default=None, min_length=1, max_length=100),
    integration_status: str | None = None,
):
    """List bookmaker discovery candidates and their independently tracked status."""
    profiles = bookmaker_directory.list_profiles(query=q)
    if integration_status:
        profiles = [
            item for item in profiles
            if item["integration_status"] == integration_status
        ]
    return {
        "count": len(profiles),
        "bookmakers": profiles,
        "coverage_note": (
            "Directory presence is not proof of live access, data rights, "
            "regional availability or complete market coverage."
        ),
    }


@router.get("/{operator_id}")
def get_bookmaker(operator_id: str):
    """Return one bookmaker's discovery and verification record."""
    try:
        from dataclasses import asdict
        profile = bookmaker_directory.get(operator_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return asdict(profile)
