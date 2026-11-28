"""Chronological, leakage-aware probabilistic forecast evaluation."""
from __future__ import annotations
from datetime import datetime,timezone
from math import log
from typing import Any

def _parse_time(value:str)->datetime:
    if not value:raise ValueError("timestamp is required")
    parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:raise ValueError("timestamps must include a timezone")
    return parsed.astimezone(timezone.utc)

def chronological_split(records:list[dict[str,Any]],cutoff:str)->dict[str,list[dict[str,Any]]]:
    boundary=_parse_time(cutoff);train=[];test=[]
    for row in records:
        predicted=_parse_time(row["predicted_at"]);start=_parse_time(row["event_start"])
        if predicted>start:raise ValueError("forecast timestamp occurs after event start (temporal leakage)")
        (train if predicted<boundary else test).append(row)
    key=lambda x:_parse_time(x["predicted_at"])
    return {"train":sorted(train,key=key),"test":sorted(test,key=key)}

def evaluate_forecasts(forecasts:list[dict[str,Any]],*,class_order:list[str],calibration_bins:int=10)->dict[str,Any]:
    if len(class_order)<2 or len(set(class_order))!=len(class_order):raise ValueError("class_order must contain at least two unique classes")
    if not 1<=calibration_bins<=50:raise ValueError("calibration_bins must be between 1 and 50")
    if not forecasts:return {"status":"insufficient_data","sample_size":0}
    briers=[];losses=[]
    bins=[{"lower":i/calibration_bins,"upper":(i+1)/calibration_bins,"count":0,
           "mean_confidence":0.0,"accuracy":0.0} for i in range(calibration_bins)]
    for row in forecasts:
        if _parse_time(row["predicted_at"])>_parse_time(row["event_start"]):
            raise ValueError("forecast timestamp occurs after event start (temporal leakage)")
        probs=row.get("probabilities") or {}
        if set(probs)!=set(class_order):raise ValueError("every forecast must provide exactly the declared classes")
        vals=[float(probs[c]) for c in class_order]
        if any(p<0 or p>1 for p in vals):raise ValueError("probabilities must be between 0 and 1")
        if abs(sum(vals)-1)>1e-6:raise ValueError("class probabilities must sum to 1")
        outcome=row.get("outcome")
        if outcome not in class_order:raise ValueError("outcome is outside class_order")
        target=[1.0 if c==outcome else 0.0 for c in class_order]
        briers.append(sum((p-y)**2 for p,y in zip(vals,target))/len(class_order))
        losses.append(-log(max(1e-15,float(probs[outcome]))))
        idx=max(range(len(vals)),key=lambda i:vals[i]);conf=vals[idx]
        correct=1.0 if class_order[idx]==outcome else 0.0
        bucket=bins[min(calibration_bins-1,int(conf*calibration_bins))]
        bucket["count"]+=1;n=bucket["count"]
        bucket["mean_confidence"]+=(conf-bucket["mean_confidence"])/n
        bucket["accuracy"]+=(correct-bucket["accuracy"])/n
    n=len(forecasts)
    ece=sum(x["count"]/n*abs(x["mean_confidence"]-x["accuracy"]) for x in bins if x["count"])
    return {"status":"evaluated","sample_size":n,"class_order":class_order,
      "multiclass_brier_score":sum(briers)/n,"mean_log_loss":sum(losses)/n,
      "expected_calibration_error":ece,"calibration_bins":bins,
      "evaluation_policy":"chronological predictions only; no prediction timestamp may exceed event start"}
