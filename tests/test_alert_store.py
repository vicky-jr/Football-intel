from app.services.alert_store import AlertStore

def test_rules_and_alerts_persist_with_cooldown(tmp_path):
 path=tmp_path/"alerts.sqlite3";store=AlertStore(path)
 rule=store.create_rule("owner-1","book-a","match:evt:market",5,900)
 fired=store.record_trigger(rule["rule_id"],"match:evt:market","2026-11-28T10:00:00+00:00",{"change":-6})
 assert fired["recorded"]
 repeated=store.record_trigger(rule["rule_id"],"match:evt:market","2026-11-28T10:05:00+00:00",{"change":-7})
 assert repeated["reason"]=="cooldown_active"
 reopened=AlertStore(path)
 assert reopened.list_rules("owner-1")[0]["rule_id"]==rule["rule_id"]
 assert len(reopened.list_events("owner-1"))==1

def test_disabled_alert_rule_cannot_record_event(tmp_path):
 store=AlertStore(tmp_path/"alerts.sqlite3")
 rule=store.create_rule("owner","book","key")
 store.set_enabled(rule["rule_id"],False)
 result=store.record_trigger(rule["rule_id"],"key","2026-11-28T10:00:00+00:00",{})
 assert result["recorded"] is False and result["reason"]=="rule_disabled"
