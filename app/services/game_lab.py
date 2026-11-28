"""Descriptive proprietary-game research; never predicts independent RNG outcomes."""
from __future__ import annotations
import hashlib,hmac
from typing import Any

def analyse_game_rounds(game_spec:dict[str,Any],rounds:list[dict[str,Any]])->dict[str,Any]:
    game_id=game_spec.get("game_id");version=game_spec.get("rules_version")
    if not game_id or not version:raise ValueError("game_id and rules_version are required")
    if len(rounds)>1_000_000:raise ValueError("round batch is too large")
    stake_total=payout_total=0.0;freq={}
    for row in rounds:
        stake=float(row.get("stake",0));payout=float(row.get("payout",0))
        if stake<0 or payout<0:raise ValueError("stake and payout cannot be negative")
        stake_total+=stake;payout_total+=payout
        outcome=str(row.get("outcome","unknown"));freq[outcome]=freq.get(outcome,0)+1
    n=len(rounds);rtp=game_spec.get("published_rtp")
    return {"game_id":game_id,"rules_version":version,"sample_size":n,
      "outcome_frequencies":{k:{"count":v,"frequency":v/n if n else None} for k,v in sorted(freq.items())},
      "total_stake":round(stake_total,6),"total_payout":round(payout_total,6),
      "observed_rtp":round(payout_total/stake_total,8) if stake_total else None,
      "published_rtp":rtp,"published_house_edge":1-float(rtp) if rtp is not None else None,
      "rules_evidence_url":game_spec.get("rules_evidence_url"),"interpretation":"descriptive_only",
      "next_round_prediction":None,
      "limitations":["Observed frequencies/RTP describe only this sample and rules version.",
       "Sampling variation does not prove a game is biased or manipulated.",
       "Past independent random outcomes do not reliably predict the next outcome.",
       "Published RTP may be theoretical, provider-specific or mode-specific; verify its scope."]}

def verify_seed_commitment(server_seed:str,published_commitment:str)->dict[str,Any]:
    if not server_seed or not published_commitment:raise ValueError("server_seed and published_commitment are required")
    calculated=hashlib.sha256(server_seed.encode()).hexdigest()
    valid=hmac.compare_digest(calculated.casefold(),published_commitment.strip().casefold())
    return {"commitment_valid":valid,"calculated_commitment":calculated,"method":"SHA-256(server_seed)",
      "limitations":["This verifies only that the revealed seed matches the supplied commitment.",
       "Outcome verification also requires the exact published algorithm, client seed, nonce and game version."]}
