import pytest

from app.services.settlement_rules import (
    SettlementRuleProfile,
    SettlementRuleRegistry,
    compare_settlement_profiles,
)


def profile(
    profile_id,
    provider,
    *,
    verification_status="verified",
    overtime_policy="exclude",
    abandoned_policy="void",
    postponed_policy="reoffer",
    dead_heat_policy="not_applicable",
    push_policy="stake_returned",
    retirement_policy="void",
    market_type="football.total_goals",
    period="regulation_90",
):
    return SettlementRuleProfile(
        profile_id=profile_id,
        provider_id=provider,
        sport="football",
        canonical_market_type_id=market_type,
        settlement_period=period,
        overtime_policy=overtime_policy,
        abandoned_policy=abandoned_policy,
        postponed_policy=postponed_policy,
        dead_heat_policy=dead_heat_policy,
        push_policy=push_policy,
        retirement_policy=retirement_policy,
        rules_version="2026-01",
        verification_status=verification_status,
        evidence_url="https://bookmaker.example/rules" if verification_status == "verified" else None,
        verified_at="2026-11-28T10:00:00+00:00" if verification_status == "verified" else None,
    )


def test_identical_verified_profiles_are_comparable():
    result = compare_settlement_profiles(
        profile("a-v1", "book-a"),
        profile("b-v1", "book-b"),
    )
    assert result["comparable"] is True
    assert result["reason"] == "settlement_rules_match"


def test_different_overtime_or_abandonment_rules_prevent_comparison():
    left = profile("a-v1", "book-a")
    right = profile("b-v1", "book-b", overtime_policy="include")
    result = compare_settlement_profiles(left, right)
    assert result["comparable"] is False
    assert result["differences"] == ["overtime_policy"]


def test_unverified_rules_never_authorize_comparison():
    result = compare_settlement_profiles(
        profile("a-v1", "book-a"),
        profile("b-v1", "book-b", verification_status="unverified"),
    )
    assert result["comparable"] is False
    assert result["reason"] == "unverified_settlement_profile"


def test_different_period_or_market_type_prevents_comparison():
    period_result = compare_settlement_profiles(
        profile("a-v1", "book-a"),
        profile("b-v1", "book-b", period="full_event"),
    )
    market_result = compare_settlement_profiles(
        profile("a-v1", "book-a"),
        profile("b-v1", "book-b", market_type="football.both_teams_to_score"),
    )
    assert period_result["reason"] == "settlement_period_mismatch"
    assert market_result["reason"] == "market_type_mismatch"


def test_verified_profile_requires_evidence_and_complete_policy_fields():
    with pytest.raises(ValueError, match="HTTPS evidence_url"):
        SettlementRuleProfile(
            profile_id="bad",
            provider_id="book-a",
            sport="football",
            canonical_market_type_id="football.total_goals",
            settlement_period="regulation_90",
            overtime_policy="exclude",
            abandoned_policy="void",
            postponed_policy="reoffer",
            dead_heat_policy="not_applicable",
            push_policy="stake_returned",
            retirement_policy="void",
            rules_version="1",
            verification_status="verified",
        )

    with pytest.raises(ValueError, match="unknown/operator-specific"):
        profile("bad", "book-a", overtime_policy="unknown")


def test_registry_rejects_duplicate_profile_ids_and_lists_records():
    registry = SettlementRuleRegistry()
    item = profile("book-a-football-total-v1", "book-a")
    registry.register(item)
    assert registry.get(item.profile_id) == item
    assert registry.list_profiles()[0]["provider_id"] == "book-a"

    with pytest.raises(ValueError, match="already registered"):
        registry.register(item)
