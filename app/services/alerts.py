"""Transparent market-movement alert evaluation."""
from __future__ import annotations
from typing import Any

def evaluate_price_alert(history:list[dict[str,Any]],*,threshold_percent:float=5.0,
                         minimum_observations:int=2,rule_id:str="default")->dict[str,Any]:
    if threshold_percent<=0:raise ValueError("threshold_percent must be positive")
    if minimum_observations<2:raise ValueError("minimum_observations must be at least 2")
    rows=sorted(history,key=lambda x:x["captured_at"])
    if len(rows)<minimum_observations:return {"triggered":False,"status":"insufficient_observations","observation_count":len(rows)}
    first,last=rows[0],rows[-1];start,end=float(first["odds_decimal"]),float(last["odds_decimal"])
    if start<=1 or end<=1:raise ValueError("decimal odds must be greater than 1")
    change=(end-start)/start*100;triggered=abs(change)>=threshold_percent
    return {"triggered":triggered,"status":"triggered" if triggered else "below_threshold",
      "rule_id":rule_id,"observation_count":len(rows),"first_observed_at":first["captured_at"],
      "latest_observed_at":last["captured_at"],"first_odds":start,"latest_odds":end,
      "change_percent":round(change,4),"direction":"drifted" if change>0 else "shortened" if change<0 else "unchanged",
      "threshold_percent":threshold_percent,
      "note":"An alert describes an observed price change; it does not explain its cause or predict an outcome."}
