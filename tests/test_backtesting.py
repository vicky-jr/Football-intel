import pytest
from app.services.backtesting import chronological_split,evaluate_forecasts

def rows():
 return [
 {"event_id":"1","predicted_at":"2026-01-01T10:00:00+00:00","event_start":"2026-01-01T12:00:00+00:00","probabilities":{"H":.6,"D":.2,"A":.2},"outcome":"H"},
 {"event_id":"2","predicted_at":"2026-02-01T10:00:00+00:00","event_start":"2026-02-01T12:00:00+00:00","probabilities":{"H":.2,"D":.3,"A":.5},"outcome":"A"}]

def test_chronological_split_and_metrics():
 s=chronological_split(rows(),"2026-02-01T00:00:00+00:00")
 assert len(s["train"])==1 and len(s["test"])==1
 r=evaluate_forecasts(rows(),class_order=["H","D","A"])
 assert r["status"]=="evaluated" and r["sample_size"]==2 and r["mean_log_loss"]>0

def test_prediction_after_event_start_is_rejected():
 row=rows()[0];row["predicted_at"]="2026-01-01T13:00:00+00:00"
 with pytest.raises(ValueError,match="leakage"):evaluate_forecasts([row],class_order=["H","D","A"])

def test_probabilities_must_sum_to_one():
 row=rows()[0];row["probabilities"]={"H":.6,"D":.1,"A":.1}
 with pytest.raises(ValueError,match="sum to 1"):evaluate_forecasts([row],class_order=["H","D","A"])
