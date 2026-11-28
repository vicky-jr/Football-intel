"""Conservative canonical market taxonomy and explicit provider mappings.

A provider market is classified only when a verified mapping has been registered.
Unknown or ambiguous markets remain unclassified; names are never guessed into
a canonical market type by fuzzy matching.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from app.providers.base import ProviderMarket


@dataclass(frozen=True)
class CanonicalMarketDefinition:
    type_id: str
    sport: str
    label: str
    description: str
    period: str
    settlement_basis: str
    outcome_schema: str
    line_required: bool = False
    taxonomy_version: str = "1.0"


@dataclass(frozen=True)
class ProviderMarketMapping:
    provider_id: str
    canonical_type_id: str
    source_market_id: str | None = None
    source_market_name: str | None = None
    source_period: str | None = None
    mapping_version: str = "1"
    verification: str = "reviewed"


def normalize_market_name(value: str) -> str:
    """Normalize punctuation/spacing for explicit alias lookup, not fuzzy search."""
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def normalize_line(value: str | float | None) -> str | None:
    """Normalize numeric line notation so 2.50 and 2.5 share an identity."""
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        number = Decimal(raw)
        if not number.is_finite():
            return raw.casefold()
        normalized = number.normalize()
        if normalized == 0:
            return "0"
        return format(normalized, "f")
    except (InvalidOperation, ValueError):
        return re.sub(r"\s+", " ", raw.casefold())


def default_market_definitions() -> tuple[CanonicalMarketDefinition, ...]:
    """Small initial catalogue; expand only as settlement semantics are verified."""
    return (
        CanonicalMarketDefinition(
            "football.match_result_3way", "football", "Match result (three-way)",
            "Home win, draw or away win at the defined settlement time.",
            "regulation_90", "regulation_time", "home_draw_away",
        ),
        CanonicalMarketDefinition(
            "football.double_chance", "football", "Double chance",
            "One of the supported two-outcome combinations.",
            "regulation_90", "regulation_time", "double_chance",
        ),
        CanonicalMarketDefinition(
            "football.total_goals", "football", "Total goals",
            "Over/under total goals at a specific line.",
            "regulation_90", "regulation_time", "over_under", line_required=True,
        ),
        CanonicalMarketDefinition(
            "football.both_teams_to_score", "football", "Both teams to score",
            "Whether both teams score within the defined settlement period.",
            "regulation_90", "regulation_time", "yes_no",
        ),
        CanonicalMarketDefinition(
            "football.asian_handicap", "football", "Asian handicap",
            "Handicap result with the exact handicap line retained.",
            "regulation_90", "regulation_time", "handicap_home_away",
            line_required=True,
        ),
        CanonicalMarketDefinition(
            "basketball.moneyline", "basketball", "Moneyline",
            "Winner of the basketball event under the source rules.",
            "full_event", "including_overtime", "winner_two_way",
        ),
        CanonicalMarketDefinition(
            "basketball.spread", "basketball", "Point spread",
            "Winner against a specified point spread.",
            "full_event", "including_overtime", "spread_home_away",
            line_required=True,
        ),
        CanonicalMarketDefinition(
            "basketball.total_points", "basketball", "Total points",
            "Over/under combined points at a specified line.",
            "full_event", "including_overtime", "over_under",
            line_required=True,
        ),
        CanonicalMarketDefinition(
            "tennis.match_winner", "tennis", "Match winner",
            "Winner of the tennis match under the competition rules.",
            "match", "completed_match", "winner_two_way",
        ),
        CanonicalMarketDefinition(
            "tennis.total_games", "tennis", "Total games",
            "Over/under total games at a specified line.",
            "match", "completed_match", "over_under",
            line_required=True,
        ),
        CanonicalMarketDefinition(
            "tennis.set_handicap", "tennis", "Set handicap",
            "Set handicap with the exact handicap line retained.",
            "match", "completed_match", "handicap_home_away",
            line_required=True,
        ),
    )


class MarketTaxonomyRegistry:
    """Register reviewed source-to-canonical mappings and classify conservatively."""

    def __init__(
        self,
        definitions: tuple[CanonicalMarketDefinition, ...] | None = None,
    ) -> None:
        self._definitions = {
            item.type_id: item for item in (definitions or default_market_definitions())
        }
        self._by_source_id: dict[tuple[str, str], ProviderMarketMapping] = {}
        self._by_source_name: dict[tuple[str, str], ProviderMarketMapping] = {}

    def definitions(self) -> list[dict[str, Any]]:
        return [asdict(item) for item in sorted(
            self._definitions.values(), key=lambda item: item.type_id
        )]

    def register_mapping(self, mapping: ProviderMarketMapping) -> None:
        provider = mapping.provider_id.strip().casefold()
        if not provider:
            raise ValueError("mapping provider_id is required")
        if mapping.canonical_type_id not in self._definitions:
            raise KeyError(f"unknown canonical market type: {mapping.canonical_type_id}")
        if not mapping.source_market_id and not mapping.source_market_name:
            raise ValueError("mapping requires a source market id or source market name")
        if mapping.verification not in {"reviewed", "provisional"}:
            raise ValueError("verification must be 'reviewed' or 'provisional'")

        normalized = ProviderMarketMapping(
            provider_id=provider,
            canonical_type_id=mapping.canonical_type_id,
            source_market_id=mapping.source_market_id.strip() if mapping.source_market_id else None,
            source_market_name=mapping.source_market_name.strip() if mapping.source_market_name else None,
            source_period=mapping.source_period.strip().casefold() if mapping.source_period else None,
            mapping_version=mapping.mapping_version,
            verification=mapping.verification,
        )

        if normalized.source_market_id:
            key = (provider, normalized.source_market_id)
            existing = self._by_source_id.get(key)
            if existing and existing != normalized:
                raise ValueError(f"conflicting source market id mapping: {key}")
            self._by_source_id[key] = normalized

        if normalized.source_market_name:
            name_key = (provider, normalize_market_name(normalized.source_market_name))
            existing = self._by_source_name.get(name_key)
            if existing and existing != normalized:
                raise ValueError(f"conflicting source market name mapping: {name_key}")
            self._by_source_name[name_key] = normalized

    def classify(self, market: ProviderMarket, sport: str | None = None) -> dict[str, Any]:
        provider = market.provider.strip().casefold()
        mapping_method = None
        mapping = None

        if market.source_market_id:
            mapping = self._by_source_id.get((provider, market.source_market_id))
            if mapping:
                mapping_method = "provider_market_id"

        if mapping is None:
            name_key = (provider, normalize_market_name(market.name))
            mapping = self._by_source_name.get(name_key)
            if mapping:
                mapping_method = "explicit_name_alias"

        if mapping is None:
            return {
                "classified": False,
                "canonical_market_id": None,
                "reason": "no_verified_provider_mapping",
            }

        definition = self._definitions[mapping.canonical_type_id]
        if sport and normalize_market_name(sport) != normalize_market_name(definition.sport):
            return {
                "classified": False,
                "canonical_market_id": None,
                "reason": "sport_mismatch",
                "mapping_method": mapping_method,
            }

        if mapping.source_period and (
            (market.period or "").strip().casefold() != mapping.source_period
        ):
            return {
                "classified": False,
                "canonical_market_id": None,
                "reason": "source_period_mismatch",
                "mapping_method": mapping_method,
            }

        line = normalize_line(market.line)
        if definition.line_required and line is None:
            return {
                "classified": False,
                "canonical_market_id": None,
                "reason": "required_line_missing",
                "mapping_method": mapping_method,
            }

        # Include settlement/ruleset semantics and line in the instance key.
        canonical_id = (
            f"{definition.type_id}|period={definition.period}"
            f"|settlement={definition.settlement_basis}"
            f"|line={line if line is not None else 'none'}"
            f"|rules={definition.taxonomy_version}"
        )
        return {
            "classified": True,
            "canonical_type_id": definition.type_id,
            "canonical_market_id": canonical_id,
            "canonical_label": definition.label,
            "sport": definition.sport,
            "period": definition.period,
            "settlement_basis": definition.settlement_basis,
            "outcome_schema": definition.outcome_schema,
            "line": line,
            "taxonomy_version": definition.taxonomy_version,
            "mapping_version": mapping.mapping_version,
            "mapping_verification": mapping.verification,
            "mapping_method": mapping_method,
        }
