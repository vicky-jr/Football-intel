"""Provider settlement-rule profiles and safe comparability checks."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any
from urllib.parse import urlparse


@dataclass(frozen=True)
class SettlementRuleProfile:
    profile_id: str
    provider_id: str
    sport: str
    canonical_market_type_id: str
    settlement_period: str
    overtime_policy: str
    abandoned_policy: str
    postponed_policy: str
    dead_heat_policy: str
    push_policy: str
    retirement_policy: str
    rules_version: str
    verification_status: str = "unverified"
    evidence_url: str | None = None
    verified_at: str | None = None
    region: str | None = None

    def __post_init__(self) -> None:
        required = (
            "profile_id", "provider_id", "sport", "canonical_market_type_id",
            "settlement_period", "rules_version",
        )
        for field_name in required:
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} is required")
        if self.verification_status not in {"verified", "unverified"}:
            raise ValueError("verification_status must be verified or unverified")

        policies = (
            self.overtime_policy,
            self.abandoned_policy,
            self.postponed_policy,
            self.dead_heat_policy,
            self.push_policy,
            self.retirement_policy,
        )
        if any(not value.strip() for value in policies):
            raise ValueError("all settlement policy fields must be explicit")
        if self.verification_status == "verified":
            if any(value in {"unknown", "operator_specific"} for value in policies):
                raise ValueError("verified profile cannot contain unknown/operator-specific policies")
            parsed = urlparse(self.evidence_url or "")
            if parsed.scheme != "https" or not parsed.netloc:
                raise ValueError("verified profile requires an HTTPS evidence_url")
            try:
                timestamp = datetime.fromisoformat((self.verified_at or "").replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError("verified profile requires a valid verified_at timestamp") from exc
            if timestamp.tzinfo is None or timestamp.utcoffset() is None:
                raise ValueError("verified_at must include a timezone")


class SettlementRuleRegistry:
    """In-memory registry; populate only from verified bookmaker rule evidence."""

    def __init__(self) -> None:
        self._profiles: dict[str, SettlementRuleProfile] = {}

    def register(self, profile: SettlementRuleProfile) -> None:
        if profile.profile_id in self._profiles:
            raise ValueError(f"settlement profile already registered: {profile.profile_id}")
        self._profiles[profile.profile_id] = profile

    def get(self, profile_id: str) -> SettlementRuleProfile:
        try:
            return self._profiles[profile_id]
        except KeyError as exc:
            raise KeyError(f"settlement profile not found: {profile_id}") from exc

    def list_profiles(self) -> list[dict[str, Any]]:
        return [
            asdict(profile)
            for profile in sorted(self._profiles.values(), key=lambda item: item.profile_id)
        ]


def compare_settlement_profiles(
    left: SettlementRuleProfile,
    right: SettlementRuleProfile,
) -> dict[str, Any]:
    """Return true only when both rule profiles are verified and semantically equal."""
    if left.sport.casefold() != right.sport.casefold():
        return {"comparable": False, "reason": "sport_mismatch", "differences": ["sport"]}
    if left.canonical_market_type_id != right.canonical_market_type_id:
        return {
            "comparable": False,
            "reason": "market_type_mismatch",
            "differences": ["canonical_market_type_id"],
        }
    if left.settlement_period != right.settlement_period:
        return {
            "comparable": False,
            "reason": "settlement_period_mismatch",
            "differences": ["settlement_period"],
        }
    if left.verification_status != "verified" or right.verification_status != "verified":
        return {
            "comparable": False,
            "reason": "unverified_settlement_profile",
            "differences": [],
        }

    semantic_fields = (
        "overtime_policy",
        "abandoned_policy",
        "postponed_policy",
        "dead_heat_policy",
        "push_policy",
        "retirement_policy",
    )
    differences = [
        field_name for field_name in semantic_fields
        if getattr(left, field_name) != getattr(right, field_name)
    ]
    return {
        "comparable": not differences,
        "reason": "settlement_rules_match" if not differences else "settlement_rules_differ",
        "differences": differences,
        "left_profile_id": left.profile_id,
        "right_profile_id": right.profile_id,
        "left_rules_version": left.rules_version,
        "right_rules_version": right.rules_version,
    }
