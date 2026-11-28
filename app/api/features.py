"""API routes for the extended sports-intelligence feature foundations.

These endpoints expose deterministic research services. Production deployment
must add authentication, authorisation, rate limits and user-data protections.
"""
from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, HTTPException

from app.services.alerts import evaluate_price_alert
from app.services.analyst_workspace import AnalystWorkspaceStore
from app.services.backtesting import chronological_split, evaluate_forecasts
from app.services.bet_slip import reconstruct_bet_slip
from app.services.bookmaker_intelligence import summarize_bookmaker_behaviour
from app.services.confidence import assess_evidence_confidence
from app.services.event_matching import match_events
from app.services.game_lab import analyse_game_rounds, verify_seed_commitment
from app.services.historical_results import HistoricalResultsStore
from app.services.odds_comparison import compare_bookmaker_odds
from app.services.responsible_gambling import RiskLimits, evaluate_risk
from app.services.risk_ledger import RiskLedger
from app.services.specialists import aggregate_specialist_assessments

DB_PATH = os.getenv("FOOTBALL_INTEL_DB_PATH", "data/football_intel.sqlite3")
workspace_store = AnalystWorkspaceStore(DB_PATH)
results_store = HistoricalResultsStore(DB_PATH)
risk_ledger = RiskLedger(DB_PATH)

router = APIRouter(prefix="/api/v1", tags=["extended-intelligence"])


def _bad_request(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=422, detail=str(exc))


@router.get("/features")
def feature_catalogue():
    return {
        "implemented_foundations": [
            "cross-provider event candidate matching",
            "historical results with provenance and correction history",
            "decimal odds comparison, implied probabilities and overround",
            "chronological backtesting and calibration metrics",
            "threshold-based market movement alerts",
            "OCR-text bet-slip reconstruction",
            "responsible-gambling exposure checks and user-entered risk ledger",
            "proprietary-game descriptive research and seed commitment check",
            "specialist evidence aggregation interface",
            "observable bookmaker behaviour summaries",
            "evidence confidence and abstention gate",
            "analyst projects, notes and watchlists",
        ],
        "integration_gaps": [
            "verified live bookmaker feeds and official result sources",
            "native image OCR service and secure image upload",
            "deployed specialist models or LLM agents",
            "notification delivery and persisted alert preferences",
            "user authentication and tenant isolation",
        ],
    }


@router.post("/events/match")
def cross_provider_event_match(payload: dict[str, Any]):
    try:
        return match_events(
            payload["left"],
            payload["right"],
            auto_match_threshold=float(payload.get("auto_match_threshold", 0.92)),
            review_threshold=float(payload.get("review_threshold", 0.72)),
            kickoff_tolerance_minutes=int(payload.get("kickoff_tolerance_minutes", 180)),
        )
    except (KeyError, ValueError) as exc:
        raise _bad_request(ValueError(str(exc))) from exc


@router.post("/odds/compare")
def odds_comparison(payload: dict[str, Any]):
    try:
        return compare_bookmaker_odds(payload.get("quotes", []))
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.post("/models/backtest")
def model_backtest(payload: dict[str, Any]):
    try:
        forecasts = payload.get("forecasts", [])
        result = evaluate_forecasts(
            forecasts,
            class_order=payload["class_order"],
            calibration_bins=int(payload.get("calibration_bins", 10)),
        )
        if payload.get("cutoff"):
            result["chronological_split"] = {
                key: len(value)
                for key, value in chronological_split(forecasts, payload["cutoff"]).items()
            }
        return result
    except (KeyError, ValueError) as exc:
        raise _bad_request(ValueError(str(exc))) from exc


@router.post("/alerts/price-movement")
def market_price_alert(payload: dict[str, Any]):
    try:
        return evaluate_price_alert(
            payload.get("history", []),
            threshold_percent=float(payload.get("threshold_percent", 5.0)),
            minimum_observations=int(payload.get("minimum_observations", 2)),
            rule_id=str(payload.get("rule_id", "default")),
        )
    except (TypeError, ValueError) as exc:
        raise _bad_request(ValueError(str(exc))) from exc


@router.post("/bet-slips/reconstruct")
def bet_slip_reconstruction(payload: dict[str, Any]):
    try:
        return reconstruct_bet_slip(
            payload["extracted_text"],
            image_sha256=payload.get("image_sha256"),
            stake=float(payload["stake"]) if payload.get("stake") is not None else None,
        )
    except (KeyError, ValueError) as exc:
        raise _bad_request(ValueError(str(exc))) from exc


@router.post("/risk/check")
def responsible_gambling_check(payload: dict[str, Any]):
    try:
        limits = RiskLimits(**payload["limits"])
        return evaluate_risk(
            proposed_stake=float(payload["proposed_stake"]),
            limits=limits,
            stakes_today=float(payload.get("stakes_today", 0)),
            open_exposure=float(payload.get("open_exposure", 0)),
            net_loss_today=float(payload.get("net_loss_today", 0)),
            self_excluded=bool(payload.get("self_excluded", False)),
            cooling_off_active=bool(payload.get("cooling_off_active", False)),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise _bad_request(ValueError(str(exc))) from exc


@router.post("/risk/records")
def record_risk_entry(payload: dict[str, Any]):
    try:
        return risk_ledger.record(
            user_id=payload["user_id"],
            occurred_at=payload["occurred_at"],
            stake=float(payload["stake"]),
            status=payload["status"],
            net_result=float(payload["net_result"]) if payload.get("net_result") is not None else None,
            metadata=payload.get("metadata") or {},
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise _bad_request(ValueError(str(exc))) from exc


@router.get("/risk/{user_id}/summary")
def risk_summary(user_id: str, since: str):
    return risk_ledger.summary(user_id, since)


@router.post("/games/analyse")
def proprietary_game_analysis(payload: dict[str, Any]):
    try:
        return analyse_game_rounds(payload["game_spec"], payload.get("rounds", []))
    except (KeyError, TypeError, ValueError) as exc:
        raise _bad_request(ValueError(str(exc))) from exc


@router.post("/games/seed-commitment/verify")
def verify_game_seed(payload: dict[str, Any]):
    try:
        return verify_seed_commitment(payload["server_seed"], payload["published_commitment"])
    except (KeyError, ValueError) as exc:
        raise _bad_request(ValueError(str(exc))) from exc


@router.post("/intelligence/specialists/aggregate")
def specialist_aggregation(payload: dict[str, Any]):
    try:
        return aggregate_specialist_assessments(
            payload.get("assessments", []),
            minimum_independent_specialists=int(payload.get("minimum_independent_specialists", 2)),
        )
    except (TypeError, ValueError) as exc:
        raise _bad_request(ValueError(str(exc))) from exc


@router.post("/intelligence/confidence")
def evidence_confidence(payload: dict[str, Any]):
    try:
        return assess_evidence_confidence(
            source_freshness=payload["source_freshness"],
            verified_market_mapping=bool(payload["verified_market_mapping"]),
            verified_settlement_rules=bool(payload["verified_settlement_rules"]),
            sample_size=int(payload["sample_size"]),
            required_sample_size=int(payload["required_sample_size"]),
            calibrated_model=bool(payload["calibrated_model"]),
            material_disagreement=bool(payload.get("material_disagreement", False)),
            minimum_score=float(payload.get("minimum_score", 0.70)),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise _bad_request(ValueError(str(exc))) from exc


@router.post("/bookmakers/behaviour")
def bookmaker_behaviour(payload: dict[str, Any]):
    try:
        return summarize_bookmaker_behaviour(
            payload.get("observations", []),
            minimum_market_series=int(payload.get("minimum_market_series", 5)),
            follow_on_window_minutes=int(payload.get("follow_on_window_minutes", 30)),
        )
    except (TypeError, ValueError) as exc:
        raise _bad_request(ValueError(str(exc))) from exc


@router.post("/results")
def record_historical_result(payload: dict[str, Any]):
    try:
        # Client-submitted records are never marked verified by this public API.
        return results_store.record_result(
            canonical_event_id=payload["canonical_event_id"],
            sport=payload["sport"],
            outcome=payload["outcome"],
            result_payload=payload.get("result_payload") or {},
            source_name=payload["source_name"],
            source_url=payload.get("source_url"),
            observed_at=payload["observed_at"],
            verified=False,
            supersedes_result_id=payload.get("supersedes_result_id"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise _bad_request(ValueError(str(exc))) from exc


@router.get("/results/{canonical_event_id}")
def historical_event_results(canonical_event_id: str):
    return {"results": results_store.get_event_results(canonical_event_id)}


@router.post("/workspaces/projects")
def create_analyst_project(payload: dict[str, Any]):
    try:
        return workspace_store.create_project(
            payload["owner_id"], payload["name"], payload.get("description", "")
        )
    except (KeyError, ValueError) as exc:
        raise _bad_request(ValueError(str(exc))) from exc


@router.get("/workspaces/projects")
def list_analyst_projects(owner_id: str):
    return {"projects": workspace_store.list_projects(owner_id)}


@router.post("/workspaces/projects/{project_id}/notes")
def add_analyst_note(project_id: str, payload: dict[str, Any]):
    try:
        return workspace_store.add_note(
            project_id, payload["title"], payload["body"], payload.get("evidence_ids", [])
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (KeyError, ValueError) as exc:
        raise _bad_request(ValueError(str(exc))) from exc


@router.get("/workspaces/projects/{project_id}/notes")
def list_analyst_notes(project_id: str):
    return {"notes": workspace_store.list_notes(project_id)}


@router.post("/workspaces/projects/{project_id}/watchlist")
def add_analyst_watchlist_item(project_id: str, payload: dict[str, Any]):
    try:
        return workspace_store.add_watchlist_item(
            project_id, payload["item_key"], payload["item_type"], payload["label"]
        )
    except (KeyError, ValueError) as exc:
        raise _bad_request(ValueError(str(exc))) from exc


@router.get("/workspaces/projects/{project_id}/watchlist")
def list_analyst_watchlist(project_id: str):
    return {"items": workspace_store.list_watchlist(project_id)}
