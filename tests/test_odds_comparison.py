from app.services.odds_comparison import compare_bookmaker_odds

def quote(book,sel,odds):
 return {"bookmaker":book,"selection_key":sel,"odds_decimal":odds,
 "canonical_market_id":"football.match_result_3way|regulation","settlement_comparable":True,
 "freshness":"fresh","outcome_set_complete":True}

def test_comparison_removes_overround_and_finds_best_prices():
 rows=[quote("a","home",2.0),quote("a","draw",3.5),quote("a","away",4.0),
       quote("b","home",2.1),quote("b","draw",3.4),quote("b","away",3.8)]
 r=compare_bookmaker_odds(rows)
 assert r["status"]=="comparable"
 assert next(x for x in r["best_prices"] if x["selection_key"]=="home")["bookmaker"]=="b"
 assert len(r["overrounds"])==2 and r["overrounds"][0]["normalised_no_vig_probabilities"]

def test_market_and_settlement_mismatches_block_comparison():
 rows=[quote("a","home",2),quote("b","home",2.1)];rows[1]["canonical_market_id"]="different"
 assert compare_bookmaker_odds(rows)["status"]=="not_comparable"
 rows[1]["canonical_market_id"]=rows[0]["canonical_market_id"];rows[1]["settlement_comparable"]=False
 assert compare_bookmaker_odds(rows)["reason"]=="settlement_rules_not_verified"

def test_incomplete_outcome_set_does_not_claim_overround():
 row=quote("a","home",2);row["outcome_set_complete"]=False
 assert compare_bookmaker_odds([row])["overrounds"][0]["overround"] is None
