from app.services.historical_results import HistoricalResultsStore

def test_results_keep_provenance_and_correction_lineage(tmp_path):
 s=HistoricalResultsStore(tmp_path/"results.sqlite3")
 first=s.record_result(canonical_event_id="evt-1",sport="football",outcome="home",
 result_payload={"score":"2-1"},source_name="official",observed_at="2026-01-01T15:00:00+00:00",
 source_url="https://example.com/result",verified=True)
 s.record_result(canonical_event_id="evt-1",sport="football",outcome="draw",
 result_payload={"score":"1-1"},source_name="corrected official",observed_at="2026-01-01T16:00:00+00:00",
 verified=True,supersedes_result_id=first["result_id"])
 rows=s.get_event_results("evt-1")
 assert len(rows)==2 and rows[0]["supersedes_result_id"]==first["result_id"]
 assert rows[1]["result_id"]==first["result_id"]
