import pytest
from app.services.bet_slip_portability import plan_bookmaker_portability

def leg(**changes):
 value={"canonical_event_id":"event-1","sport":"football","canonical_market_id":"match_result",
 "selection_key":"home","market_period":"full_time","line":None,"selection_name":"Home win"}
 value.update(changes);return value

def offer(**changes):
 value={**leg(),"bookmaker_id":"book-b","destination_market_id":"market-44",
 "destination_selection_id":"home","odds_decimal":1.9,"market_status":"open",
 "event_identity_status":"verified","market_mapping_status":"verified",
 "settlement_status":"comparable","freshness_status":"fresh",
 "captured_at":"2026-11-28T12:00:00Z","settlement_profile_id":"book-b-rules-v1"}
 value.update(changes);return value

def test_maps_exact_legs_and_calculates_full_destination_price():
 r=plan_bookmaker_portability(source_bookmaker_id="book-a",destination_bookmaker_id="book-b",
 source_legs=[leg(),leg(canonical_event_id="event-2",selection_key="away")],
 destination_offers=[offer(),offer(canonical_event_id="event-2",selection_key="away",
 destination_market_id="market-2",odds_decimal=2.1),offer(bookmaker_id="other")],stake=100)
 assert r["status"]=="mapped_pending_booking" and r["mapped_leg_count"]==2
 assert r["destination_combined_decimal_odds"]==pytest.approx(3.99)
 assert r["potential_return"]==pytest.approx(399)
 assert r["booking_code_generation"]["status"]=="not_available"

def test_blocks_candidate_events_unverified_markets_settlement_and_stale_quotes():
 offers=[offer(event_identity_status="candidate"),
 offer(canonical_event_id="event-2",market_mapping_status="unmapped"),
 offer(canonical_event_id="event-3",settlement_status="mismatch"),
 offer(canonical_event_id="event-4",freshness_status="stale"),
 offer(canonical_event_id="event-5",market_status="suspended")]
 legs=[leg(canonical_event_id=f"event-{i}") for i in range(1,6)]
 r=plan_bookmaker_portability(source_bookmaker_id="book-a",destination_bookmaker_id="book-b",
 source_legs=legs,destination_offers=offers)
 assert r["status"]=="no_verified_mapping"
 assert all(x["status"]=="requires_review" for x in r["legs"])
 assert "event_identity_status" in r["legs"][0]["blockers"]
 assert "market_mapping_status" in r["legs"][1]["blockers"]
 assert "settlement_status" in r["legs"][2]["blockers"]
 assert "freshness_status" in r["legs"][3]["blockers"]
 assert "market_not_open" in r["legs"][4]["blockers"]

def test_partial_slip_never_gets_a_combined_quote():
 r=plan_bookmaker_portability(source_bookmaker_id="book-a",destination_bookmaker_id="book-b",
 source_legs=[leg(),leg(canonical_event_id="missing")],destination_offers=[offer()])
 assert r["status"]=="partially_mapped" and r["destination_combined_decimal_odds"] is None

def test_best_eligible_price_is_selected():
 r=plan_bookmaker_portability(source_bookmaker_id="book-a",destination_bookmaker_id="book-b",
 source_legs=[leg()],destination_offers=[offer(odds_decimal=1.8),
 offer(odds_decimal=1.95,destination_market_id="best")])
 assert r["legs"][0]["destination_offer"]["odds_decimal"]==1.95
 assert r["legs"][0]["eligible_destination_offer_count"]==2

@pytest.mark.parametrize("kwargs",[
 {"source_bookmaker_id":"a","destination_bookmaker_id":"a","source_legs":[leg()],"destination_offers":[]},
 {"source_bookmaker_id":"a","destination_bookmaker_id":"b","source_legs":[],"destination_offers":[]},
 {"source_bookmaker_id":"a","destination_bookmaker_id":"b","source_legs":[leg(line="bad")],"destination_offers":[]},
 {"source_bookmaker_id":"a","destination_bookmaker_id":"b","source_legs":[leg()],"destination_offers":[],"stake":0},
])
def test_rejects_invalid_conversion_inputs(kwargs):
 with pytest.raises(ValueError):plan_bookmaker_portability(**kwargs)
