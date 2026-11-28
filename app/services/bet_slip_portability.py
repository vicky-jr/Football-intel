"""Conservative bookmaker-to-bookmaker bet-slip portability checks.

Maps already-decoded canonical selections against destination offers. It does not
decode proprietary booking codes, access accounts, place bets or generate codes.
"""
from __future__ import annotations
from decimal import Decimal, InvalidOperation
from typing import Any

_REQUIRED = ("canonical_event_id","sport","canonical_market_id","selection_key","market_period")
_STATUSES = {
 "event_identity_status":{"verified","candidate","mismatch","unknown"},
 "market_mapping_status":{"verified","candidate","unmapped","mismatch"},
 "settlement_status":{"comparable","unknown","mismatch"},
 "freshness_status":{"fresh","stale","unknown"},
}

def _text(obj:dict[str,Any],key:str)->str:
 value=obj.get(key)
 if not isinstance(value,str) or not value.strip(): raise ValueError(f"{key} is required and must be text")
 value=value.strip()
 if len(value)>300: raise ValueError(f"{key} must not exceed 300 characters")
 return value

def _line(value:Any)->str|None:
 if value is None:return None
 if isinstance(value,bool):raise ValueError("line must be a finite numeric value or null")
 try:n=Decimal(str(value))
 except (InvalidOperation,TypeError,ValueError) as exc:raise ValueError("line must be a finite numeric value or null") from exc
 if not n.is_finite():raise ValueError("line must be a finite numeric value or null")
 return "0" if n==0 else format(n.normalize(),"f")

def _leg(item:Any,label:str)->dict[str,Any]:
 if not isinstance(item,dict):raise ValueError(f"{label} must be an object")
 result={field:_text(item,field) for field in _REQUIRED}
 result["line"]=_line(item.get("line"))
 result["selection_name"]=str(item["selection_name"]).strip() if item.get("selection_name") is not None else None
 return result

def _odds(value:Any)->Decimal|None:
 if value is None or isinstance(value,bool):return None
 try:n=Decimal(str(value))
 except (InvalidOperation,TypeError,ValueError):return None
 return n if n.is_finite() and n>1 else None

def _key(leg:dict[str,Any])->tuple:
 return tuple(leg[field] for field in _REQUIRED)+(leg["line"],)

def _blockers(offer:dict[str,Any])->list[str]:
 blocked=[]
 for field,allowed in _STATUSES.items():
  value=offer.get(field,"unknown")
  if value not in allowed:blocked.append(f"invalid_{field}")
  elif value != ({"event_identity_status":"verified","market_mapping_status":"verified","settlement_status":"comparable","freshness_status":"fresh"}[field]):
   blocked.append(field)
 if str(offer.get("market_status") or "unknown").casefold() not in {"active","open"}:
  blocked.append("market_not_open")
 if _odds(offer.get("odds_decimal")) is None:blocked.append("invalid_or_missing_destination_odds")
 return sorted(set(blocked))

def plan_bookmaker_portability(*,source_bookmaker_id:str,destination_bookmaker_id:str,
 source_legs:list[dict[str,Any]],destination_offers:list[dict[str,Any]],
 stake:float|int|str|None=None)->dict[str,Any]:
 """Plan cross-bookmaker mapping from canonical legs and destination offer evidence."""
 if not isinstance(source_bookmaker_id,str) or not source_bookmaker_id.strip():raise ValueError("source_bookmaker_id is required")
 if not isinstance(destination_bookmaker_id,str) or not destination_bookmaker_id.strip():raise ValueError("destination_bookmaker_id is required")
 source=source_bookmaker_id.strip().casefold();destination=destination_bookmaker_id.strip().casefold()
 if source==destination:raise ValueError("source and destination bookmakers must be different")
 if not isinstance(source_legs,list) or not 1<=len(source_legs)<=100:raise ValueError("source_legs must contain between 1 and 100 legs")
 if not isinstance(destination_offers,list) or len(destination_offers)>5000:raise ValueError("destination_offers must be a list of at most 5000 items")
 stake_n=None
 if stake is not None:
  if isinstance(stake,bool):raise ValueError("stake must be a positive finite number")
  try:stake_n=Decimal(str(stake))
  except (InvalidOperation,TypeError,ValueError) as exc:raise ValueError("stake must be a positive finite number") from exc
  if not stake_n.is_finite() or stake_n<=0:raise ValueError("stake must be a positive finite number")
 legs=[_leg(x,f"source_legs[{i}]") for i,x in enumerate(source_legs)]
 index:dict[tuple,list[dict[str,Any]]]={};ignored=0
 for i,raw in enumerate(destination_offers):
  if not isinstance(raw,dict):raise ValueError(f"destination_offers[{i}] must be an object")
  book=_text(raw,"bookmaker_id").casefold()
  if book!=destination:ignored+=1;continue
  item=_leg(raw,f"destination_offers[{i}]")
  item.update({
   "bookmaker_id":book,"destination_market_id":raw.get("destination_market_id"),
   "destination_selection_id":raw.get("destination_selection_id"),
   "odds_decimal":float(_odds(raw.get("odds_decimal"))) if _odds(raw.get("odds_decimal")) else None,
   "market_status":str(raw.get("market_status") or "unknown").casefold(),
   **{field:raw.get(field,"unknown") for field in _STATUSES},
   "captured_at":raw.get("captured_at"),
   "settlement_profile_id":raw.get("settlement_profile_id"),
  })
  index.setdefault(_key(item),[]).append(item)
 result_legs=[];combined=Decimal("1");all_mapped=True;mapped=0
 for number,source_leg in enumerate(legs,1):
  candidates=index.get(_key(source_leg),[])
  if not candidates:
   all_mapped=False
   result_legs.append({"leg_number":number,"source_leg":source_leg,"status":"unavailable",
    "blockers":["no_exact_destination_event_market_selection"],"destination_offer":None})
   continue
  scored=[(offer,_blockers(offer)) for offer in candidates]
  eligible=[offer for offer,blockers in scored if not blockers]
  if not eligible:
   all_mapped=False
   offer,blockers=min(scored,key=lambda pair:(len(pair[1]),str(pair[0].get("destination_market_id") or "")))
   result_legs.append({"leg_number":number,"source_leg":source_leg,"status":"requires_review",
    "blockers":blockers,"destination_offer":{
     "bookmaker_id":destination,"destination_market_id":offer["destination_market_id"],
     "destination_selection_id":offer["destination_selection_id"],
     "odds_decimal":offer["odds_decimal"],"captured_at":offer["captured_at"],
     "verification":{"event_identity":offer["event_identity_status"],
      "market_mapping":offer["market_mapping_status"],"settlement":offer["settlement_status"],
      "freshness":offer["freshness_status"],"market_status":offer["market_status"]}}})
   continue
  offer=max(eligible,key=lambda item:Decimal(str(item["odds_decimal"])))
  price=Decimal(str(offer["odds_decimal"]));combined*=price;mapped+=1
  result_legs.append({"leg_number":number,"source_leg":source_leg,"status":"mapped","blockers":[],
   "eligible_destination_offer_count":len(eligible),"destination_offer":{
    "bookmaker_id":destination,"destination_market_id":offer["destination_market_id"],
    "destination_selection_id":offer["destination_selection_id"],"odds_decimal":float(price),
    "captured_at":offer["captured_at"],"settlement_profile_id":offer["settlement_profile_id"]}})
 all_mapped=all_mapped and mapped==len(legs)
 combined_float=float(combined) if all_mapped else None
 return {
  "source_bookmaker_id":source,"destination_bookmaker_id":destination,
  "status":"mapped_pending_booking" if all_mapped else "partially_mapped" if mapped else "no_verified_mapping",
  "source_leg_count":len(legs),"mapped_leg_count":mapped,
  "unmapped_or_blocked_leg_count":len(legs)-mapped,"ignored_other_bookmaker_offers":ignored,
  "legs":result_legs,"destination_combined_decimal_odds":combined_float,
  "stake":float(stake_n) if stake_n is not None else None,
  "potential_return":float((stake_n*combined).quantize(Decimal("0.01"))) if stake_n is not None and all_mapped else None,
  "booking_code_generation":{"status":"not_available","destination_booking_code":None,
   "reason":"A bookmaker-specific authorised code encoder and live destination validation are not connected yet."},
  "verification_note":(
   "This is a portability plan for already-decoded canonical legs. Event, market, "
   "settlement and freshness statuses are supplied assertions in this request; "
   "this endpoint does not independently verify them, decode proprietary source "
   "codes, access bookmaker accounts or place bets."
  )
 }
