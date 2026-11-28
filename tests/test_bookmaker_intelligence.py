from app.services.bookmaker_intelligence import summarize_bookmaker_behaviour

def test_behaviour_report_is_descriptive_and_sample_gated():
 rows=[]
 for i in range(5):
  key=f"match-{i}"
  rows += [
   {"provider":"a","comparable_market_key":key,"captured_at":"2026-01-01T10:00:00+00:00","odds_decimal":2.0},
   {"provider":"b","comparable_market_key":key,"captured_at":"2026-01-01T10:00:00+00:00","odds_decimal":2.1},
   {"provider":"a","comparable_market_key":key,"captured_at":"2026-01-01T10:01:00+00:00","odds_decimal":1.9},
   {"provider":"b","comparable_market_key":key,"captured_at":"2026-01-01T10:02:00+00:00","odds_decimal":2.0}]
 r=summarize_bookmaker_behaviour(rows,minimum_market_series=5)
 assert r["profiles"]["a"]["sample_sufficient"]
 assert r["profiles"]["a"]["price_changes"]==5 and r["profiles"]["a"]["first_mover_share"]==1.0
