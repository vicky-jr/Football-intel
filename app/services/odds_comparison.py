"""Comparable bookmaker price calculations with explicit no-vig handling."""
from __future__ import annotations
from collections import defaultdict
from typing import Any

def _validate_odds(value:Any)->float:
    if isinstance(value,bool):raise ValueError("decimal odds must be a positive number")
    try:odds=float(value)
    except (TypeError,ValueError) as exc:raise ValueError("decimal odds must be a positive number") from exc
    if odds<=1:raise ValueError("decimal odds must be greater than 1.0")
    return odds

def compare_bookmaker_odds(entries:list[dict[str,Any]])->dict[str,Any]:
    if not entries:return {"status":"no_quotes","quotes":[],"best_prices":[],"overrounds":[]}
    market_ids={x.get("canonical_market_id") for x in entries}
    if len(market_ids)!=1 or None in market_ids or "" in market_ids:
        return {"status":"not_comparable","reason":"canonical_market_identity_mismatch"}
    if any(x.get("settlement_comparable") is not True for x in entries):
        return {"status":"not_comparable","reason":"settlement_rules_not_verified"}
    if any(x.get("freshness") not in {"fresh","unknown"} for x in entries):
        return {"status":"not_comparable","reason":"stale_or_invalid_quote"}
    if any(not x.get("selection_key") or not x.get("bookmaker") for x in entries):
        raise ValueError("each quote requires bookmaker and selection_key")
    grouped:dict[str,list[dict[str,Any]]]=defaultdict(list); quotes=[]
    for entry in entries:
        odds=_validate_odds(entry.get("odds_decimal")); implied=1/odds
        quote={"bookmaker":entry["bookmaker"],"selection_key":entry["selection_key"],
          "odds_decimal":odds,"raw_implied_probability":round(implied,8),
          "source_market_id":entry.get("source_market_id"),
          "source_selection_id":entry.get("source_selection_id"),"captured_at":entry.get("captured_at")}
        quotes.append(quote);grouped[entry["bookmaker"]].append(quote)
    overrounds=[]
    for bookmaker,book_quotes in sorted(grouped.items()):
        complete=all(x.get("outcome_set_complete") is True for x in entries if x.get("bookmaker")==bookmaker)
        total=sum(x["raw_implied_probability"] for x in book_quotes)
        overrounds.append({"bookmaker":bookmaker,"outcome_set_complete":complete,
          "overround":round(total-1,8) if complete else None,
          "normalised_no_vig_probabilities":({x["selection_key"]:round(x["raw_implied_probability"]/total,8)
             for x in book_quotes} if complete and total>0 else None),"quote_count":len(book_quotes)})
    best={}
    for quote in quotes:
        if quote["selection_key"] not in best or quote["odds_decimal"]>best[quote["selection_key"]]["odds_decimal"]:
            best[quote["selection_key"]]=quote
    return {"status":"comparable","canonical_market_id":next(iter(market_ids)),
      "quotes":sorted(quotes,key=lambda x:(x["selection_key"],x["bookmaker"])),
      "best_prices":sorted(best.values(),key=lambda x:x["selection_key"]),"overrounds":overrounds,
      "method":"reciprocal decimal odds; proportional no-vig normalisation",
      "limitations":["No-vig probabilities are a de-vigging method, not guaranteed true probabilities.",
       "Overround is reported only when the complete mutually exclusive outcome set is attested."]}
