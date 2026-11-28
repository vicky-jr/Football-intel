"""Conservative cross-provider event identity matching."""
from __future__ import annotations
from datetime import datetime, timezone
from difflib import SequenceMatcher
import re
from typing import Any

def normalize_label(value: str | None) -> str:
    text=(value or "").casefold()
    text=re.sub(r"\b(fc|afc|cf|sc|club|team)\b"," ",text)
    return re.sub(r"[^a-z0-9]+"," ",text).strip()

def _similarity(left: str | None,right: str | None)->float:
    a,b=normalize_label(left),normalize_label(right)
    if not a or not b:return 0.0
    if a==b:return 1.0
    return SequenceMatcher(None,a,b).ratio()

def _timestamp(value: str | None)->datetime | None:
    if not value:return None
    try: parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError:return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:return None
    return parsed.astimezone(timezone.utc)

def match_events(left:dict[str,Any],right:dict[str,Any],*,auto_match_threshold:float=.92,
                 review_threshold:float=.72,kickoff_tolerance_minutes:int=180)->dict[str,Any]:
    if not 0<=review_threshold<=auto_match_threshold<=1:raise ValueError("thresholds must satisfy 0 <= review <= auto <= 1")
    if kickoff_tolerance_minutes<0:raise ValueError("kickoff_tolerance_minutes cannot be negative")
    ls,rs=normalize_label(left.get("sport")),normalize_label(right.get("sport"))
    if not ls or ls!=rs:return {"status":"rejected","confidence":0.0,"reason":"sport_mismatch"}
    direct=(_similarity(left.get("home"),right.get("home"))+_similarity(left.get("away"),right.get("away")))/2
    swapped=(_similarity(left.get("home"),right.get("away"))+_similarity(left.get("away"),right.get("home")))/2
    reversed_sides=swapped>direct
    participant=max(direct,swapped)
    competition=_similarity(left.get("competition"),right.get("competition"))
    lt,rt=_timestamp(left.get("start_time")),_timestamp(right.get("start_time"))
    if lt is None or rt is None:kickoff,kickoff_status=0.0,"unknown"
    else:
        delta=abs((lt-rt).total_seconds())/60
        kickoff=max(0.0,1.0-delta/max(1,kickoff_tolerance_minutes))
        kickoff_status="within_tolerance" if delta<=kickoff_tolerance_minutes else "outside_tolerance"
    confidence=participant*.5+competition*.2+kickoff*.3
    if participant<.70:status,reason="rejected","participant_mismatch"
    elif kickoff_status=="outside_tolerance":status,reason="rejected","kickoff_time_mismatch"
    elif confidence>=auto_match_threshold and competition>=.8:status,reason="matched","high_confidence_identity"
    elif confidence>=review_threshold:status,reason="review_required","ambiguous_identity"
    else:status,reason="unmatched","insufficient_identity_evidence"
    return {"status":status,"confidence":round(confidence,4),"reason":reason,
      "reversed_home_away":reversed_sides,"components":{"participant_similarity":round(participant,4),
      "competition_similarity":round(competition,4),"kickoff_similarity":round(kickoff,4),
      "kickoff_status":kickoff_status},
      "left_source":{"provider":left.get("provider"),"event_id":left.get("source_event_id")},
      "right_source":{"provider":right.get("provider"),"event_id":right.get("source_event_id")},
      "automatic_link_permitted":status=="matched"}
