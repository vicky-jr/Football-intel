from app.services.settlement_rules import SettlementRuleProfile
from app.services.settlement_store import PersistentSettlementRuleRegistry

def profile():
 return SettlementRuleProfile(
  profile_id="book-a-football-total-v1",provider_id="book-a",sport="football",
  canonical_market_type_id="football.total_goals",settlement_period="regulation_90",
  overtime_policy="exclude",abandoned_policy="void",postponed_policy="reoffer",
  dead_heat_policy="not_applicable",push_policy="stake_returned",retirement_policy="void",
  rules_version="2026-01",verification_status="unverified")

def test_settlement_profiles_persist_and_remain_unverified(tmp_path):
 path=tmp_path/"rules.sqlite3";store=PersistentSettlementRuleRegistry(path);item=profile()
 store.register(item)
 loaded=PersistentSettlementRuleRegistry(path).get(item.profile_id)
 assert loaded==item
 assert PersistentSettlementRuleRegistry(path).list_profiles()[0]["verification_status"]=="unverified"
