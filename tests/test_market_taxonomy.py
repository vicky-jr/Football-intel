import pytest

from app.providers.base import ProviderMarket, ProviderSelection
from app.services.market_taxonomy import (
    MarketTaxonomyRegistry,
    ProviderMarketMapping,
    normalize_line,
)


def market(
    *,
    provider="book-a",
    source_market_id="market-10",
    name="Total Goals",
    period="Full Time",
    line=2.50,
):
    return ProviderMarket(
        provider=provider,
        source_event_id="event-1",
        source_market_id=source_market_id,
        name=name,
        period=period,
        line=line,
        status="active",
        selections=[ProviderSelection("over", "Over", 1.9)],
        classified=False,
    )


def test_exact_provider_market_id_mapping_classifies_and_keeps_line_identity():
    taxonomy = MarketTaxonomyRegistry()
    taxonomy.register_mapping(ProviderMarketMapping(
        provider_id="Book-A",
        source_market_id="market-10",
        canonical_type_id="football.total_goals",
        source_period="full time",
    ))

    result = taxonomy.classify(market(line=2.50))

    assert result["classified"] is True
    assert result["canonical_type_id"] == "football.total_goals"
    assert "|line=2.5|" in result["canonical_market_id"]
    assert result["mapping_method"] == "provider_market_id"


def test_explicit_name_alias_is_normalized_but_not_fuzzy():
    taxonomy = MarketTaxonomyRegistry()
    taxonomy.register_mapping(ProviderMarketMapping(
        provider_id="book-a",
        source_market_name="Both Teams To Score",
        canonical_type_id="football.both_teams_to_score",
        source_period="full time",
    ))

    exact_alias = market(source_market_id=None, name="Both Teams To Score")
    near_match = market(source_market_id=None, name="Both Teams Score")

    assert taxonomy.classify(exact_alias)["classified"] is True
    assert taxonomy.classify(near_match)["reason"] == "no_verified_provider_mapping"


def test_unknown_market_stays_unclassified():
    result = MarketTaxonomyRegistry().classify(market())
    assert result == {
        "classified": False,
        "canonical_market_id": None,
        "reason": "no_verified_provider_mapping",
    }


def test_required_line_missing_does_not_create_false_market_identity():
    taxonomy = MarketTaxonomyRegistry()
    taxonomy.register_mapping(ProviderMarketMapping(
        provider_id="book-a",
        source_market_id="market-10",
        canonical_type_id="football.total_goals",
    ))
    result = taxonomy.classify(market(line=None))
    assert result["classified"] is False
    assert result["reason"] == "required_line_missing"


def test_period_mismatch_does_not_classify():
    taxonomy = MarketTaxonomyRegistry()
    taxonomy.register_mapping(ProviderMarketMapping(
        provider_id="book-a",
        source_market_id="market-10",
        canonical_type_id="football.total_goals",
        source_period="first half",
    ))
    result = taxonomy.classify(market(period="full time"))
    assert result["reason"] == "source_period_mismatch"


def test_conflicting_source_mapping_is_rejected():
    taxonomy = MarketTaxonomyRegistry()
    taxonomy.register_mapping(ProviderMarketMapping(
        provider_id="book-a",
        source_market_id="market-10",
        canonical_type_id="football.total_goals",
    ))
    with pytest.raises(ValueError, match="conflicting"):
        taxonomy.register_mapping(ProviderMarketMapping(
            provider_id="book-a",
            source_market_id="market-10",
            canonical_type_id="football.both_teams_to_score",
        ))


def test_line_normalization():
    assert normalize_line("2.50") == "2.5"
    assert normalize_line(0.0) == "0"
    assert normalize_line(None) is None
