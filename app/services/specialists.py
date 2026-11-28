"""Evidence-gated specialist assessment aggregation interface."""
from __future__ import annotations
from typing import Any

def aggregate_specialist_assessments(assessments:list[dict[str,Any]],*,minimum_independent_specialists:int=2)->dict[str,Any]:
    if minimum_independent_specialists<2:raise ValueError("at least two independent specialists are required")
    if not assessments:return {"status":"abstain","reason":"no_specialist_assessments","agreement":None}
    ids=[x.get("specialist_id") for x in assessments]
    if any(not x for x in ids):raise ValueError("every assessment requires specialist_id")
    if len(set(ids))!=len(ids):raise ValueError("specialist assessments must be independent and uniquely identified")
    usable=[x for x in assessments if x.get("conclusion") and x.get("evidence_ids") and x.get("validation_status")=="validated"]
    if len(usable)<minimum_independent_specialists:
        return {"status":"abstain","reason":"insufficient_independent_validated_evidence",
          "usable_specialists":len(usable),"required_specialists":minimum_independent_specialists,"assessments":assessments}
    counts={};evidence={}
    for item in usable:
        conclusion=str(item["conclusion"]);counts[conclusion]=counts.get(conclusion,0)+1
        evidence.setdefault(conclusion,set()).update(item["evidence_ids"])
    leading=max(counts,key=counts.get);agreement=counts[leading]/len(usable);conflict=len(counts)>1
    return {"status":"conflicting_evidence" if conflict and agreement<.8 else "supported",
      "leading_conclusion":leading,"agreement":round(agreement,4),"independent_specialists":len(usable),
      "evidence_ids":sorted(evidence[leading]),"conclusions":counts,"assessments":assessments,
      "note":"Agreement is not a calibrated probability. Each specialist must be separately evaluated and independently sourced."}
