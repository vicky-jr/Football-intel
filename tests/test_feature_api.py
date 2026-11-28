from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)

def test_feature_catalogue_exposes_the_requested_foundations():
 r=client.get("/api/v1/features")
 assert r.status_code==200
 assert "cross-provider event candidate matching" in r.json()["implemented_foundations"]
 assert "native image OCR service and secure image upload" in r.json()["integration_gaps"]

def test_event_matching_and_odds_comparison_api():
 left={"provider":"a","source_event_id":"1","sport":"football","competition":"league",
       "home":"Arsenal","away":"Chelsea","start_time":"2026-12-01T18:00:00+00:00"}
 right={**left,"provider":"b","source_event_id":"2"}
 assert client.post("/api/v1/events/match",json={"left":left,"right":right}).json()["status"]=="matched"
 quotes=[{"bookmaker":"a","selection_key":"home","odds_decimal":2.0,
          "canonical_market_id":"market-v1","settlement_comparable":True,"freshness":"fresh"}]
 result=client.post("/api/v1/odds/compare",json={"quotes":quotes})
 assert result.status_code==200 and result.json()["status"]=="comparable"

def test_risk_and_game_lab_api():
 limits={"max_single_stake":100,"max_daily_stakes":300,"max_open_exposure":200,"max_daily_net_loss":150}
 risk=client.post("/api/v1/risk/check",json={"proposed_stake":50,"limits":limits})
 assert risk.status_code==200 and risk.json()["decision"]=="within_configured_limits"
 game=client.post("/api/v1/games/analyse",json={"game_spec":{"game_id":"demo","rules_version":"v1"},
     "rounds":[{"stake":10,"payout":20,"outcome":"win"}]})
 assert game.status_code==200 and game.json()["next_round_prediction"] is None

def test_persisted_alert_rule_and_workspace_api():
 owner="api-test-"+str(uuid4())
 rule=client.post("/api/v1/alerts/rules",json={"owner_id":owner,"provider_id":"book-a",
     "comparable_market_key":"event-1:market-1","threshold_percent":4,"cooldown_seconds":60})
 assert rule.status_code==200
 assert client.get("/api/v1/alerts/rules",params={"owner_id":owner}).json()["rules"]
 project=client.post("/api/v1/workspaces/projects",json={"owner_id":owner,"name":"API test"})
 assert project.status_code==200
 note=client.post(f"/api/v1/workspaces/projects/{project.json()['project_id']}/notes",
     json={"title":"Evidence","body":"Review source","evidence_ids":["source-1"]})
 assert note.status_code==200
