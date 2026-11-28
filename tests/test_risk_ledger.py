from app.services.risk_ledger import RiskLedger

def test_user_entered_risk_ledger_summary_persists(tmp_path):
 p=tmp_path/"risk.sqlite3";s=RiskLedger(p)
 s.record("u1","2026-01-01T10:00:00+00:00",100,"settled",-30)
 s.record("u1","2026-01-01T11:00:00+00:00",50,"open")
 r=RiskLedger(p).summary("u1","2026-01-01T00:00:00+00:00")
 assert r["entries"]==2 and r["stakes"]==150 and r["net_losses"]==30 and r["open_exposure"]==50
