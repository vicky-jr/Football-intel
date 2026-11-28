"""Transparent evidence-quality and uncertainty gate."""
from __future__ import annotations
from typing import Any

def assess_evidence_confidence(*,source_freshness:str,verified_market_mapping:bool,
    verified_settlement_rules:bool,sample_size:int,required_sample_size:int,calibrated_model:bool,
    material_disagreement:bool=False,minimum_score:float=.70)->dict[str,Any]:
    if sample_size<0 or required_sample_size<1:raise ValueError("invalid sample sizes")
    if not 0<=minimum_score<=1:raise ValueError("minimum_score must be between 0 and 1")
    parts={"source_freshness":1.0 if source_freshness=="fresh" else 0.0,
      "verified_market_mapping":1.0 if verified_market_mapping else 0.0,
      "verified_settlement_rules":1.0 if verified_settlement_rules else 0.0,
      "sample_size":min(1.0,sample_size/required_sample_size),
      "model_calibration":1.0 if calibrated_model else 0.0,
      "agreement":0.0 if material_disagreement else 1.0}
    weights={"source_freshness":.15,"verified_market_mapping":.20,"verified_settlement_rules":.20,
      "sample_size":.15,"model_calibration":.20,"agreement":.10}
    score=sum(parts[k]*weights[k] for k in weights);blocking=[]
    if source_freshness!="fresh":blocking.append("source_not_confirmed_fresh")
    if not verified_market_mapping:blocking.append("market_mapping_not_verified")
    if not verified_settlement_rules:blocking.append("settlement_rules_not_verified")
    if sample_size<required_sample_size:blocking.append("sample_below_required_minimum")
    if not calibrated_model:blocking.append("model_not_calibrated")
    if material_disagreement:blocking.append("material_evidence_disagreement")
    abstain=bool(blocking) or score<minimum_score
    return {"status":"abstain" if abstain else "eligible_for_review","score":round(score,4),
      "components":parts,"weights":weights,"blocking_reasons":blocking,"minimum_score":minimum_score,
      "note":"This is an evidence-readiness score, not a probability of winning or a guarantee of accuracy."}
