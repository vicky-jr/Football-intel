from app.services.alerts import evaluate_price_alert

def test_price_alert_fires_after_threshold_crossed():
 r=evaluate_price_alert([{"captured_at":"2026-01-01T10:00:00+00:00","odds_decimal":2.0},
 {"captured_at":"2026-01-01T10:05:00+00:00","odds_decimal":1.8}],threshold_percent=5)
 assert r["triggered"] and r["direction"]=="shortened"

def test_alert_does_not_fire_without_enough_observations():
 assert not evaluate_price_alert([{"captured_at":"t","odds_decimal":2.0}])["triggered"]
