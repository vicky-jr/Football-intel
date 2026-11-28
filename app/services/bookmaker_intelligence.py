"""Observable bookmaker pricing behaviour summaries."""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime
from typing import Any

def summarize_bookmaker_behaviour(observations:list[dict[str,Any]],*,minimum_market_series:int=5,
                                  follow_on_window_minutes:int=30)->dict[str,Any]:
    if minimum_market_series<1 or follow_on_window_minutes<0:raise ValueError("invalid minimum sample or follow-on window")
    groups=defaultdict(list)
    for item in observations:
        if any(item.get(k) is None for k in ("provider","comparable_market_key","captured_at","odds_decimal")):continue
        price=float(item["odds_decimal"])
        if price>1:groups[str(item["comparable_market_key"])].append({**item,"odds_decimal":price})
    stats_by={};first_movers=defaultdict(int);follow_on=defaultdict(int);series_count=0
    for key,rows in groups.items():
        rows.sort(key=lambda x:x["captured_at"]);previous={};changes=[]
        for row in rows:
            provider=str(row["provider"]);price=row["odds_decimal"]
            if provider in previous and price!=previous[provider]:
                changes.append({"provider":provider,"captured_at":row["captured_at"],
                    "change_percent":(price-previous[provider])/previous[provider]*100})
            previous[provider]=price
            st=stats_by.setdefault(provider,{"observations":0,"price_changes":0,"absolute_change_sum":0.0,
              "suspensions":0,"market_series":set()})
            st["observations"]+=1;st["market_series"].add(key)
            if row.get("status") in {"suspended","closed","halted"}:st["suspensions"]+=1
        if len({x["provider"] for x in rows})<2 or not changes:continue
        series_count+=1;changes.sort(key=lambda x:x["captured_at"]);first=changes[0]
        first_movers[first["provider"]]+=1
        ft=datetime.fromisoformat(first["captured_at"].replace("Z","+00:00"))
        if ft.tzinfo is not None:
            for later in changes[1:]:
                lt=datetime.fromisoformat(later["captured_at"].replace("Z","+00:00"))
                if lt.tzinfo is not None and 0<=(lt-ft).total_seconds()/60<=follow_on_window_minutes:
                    follow_on[first["provider"]]+=1;break
        for change in changes:
            st=stats_by[change["provider"]];st["price_changes"]+=1
            st["absolute_change_sum"]+=abs(change["change_percent"])
    profiles={}
    for provider,st in stats_by.items():
        n=st["observations"];series=len(st["market_series"])
        profiles[provider]={"observations":n,"market_series":series,"price_changes":st["price_changes"],
          "change_rate":st["price_changes"]/n if n else None,
          "mean_absolute_price_change_percent":st["absolute_change_sum"]/st["price_changes"] if st["price_changes"] else None,
          "suspension_observations":st["suspensions"],
          "first_mover_share":first_movers[provider]/series_count if series_count else None,
          "follow_on_within_window_count":follow_on[provider],"sample_sufficient":series>=minimum_market_series,
          "interpretation":"descriptive" if series>=minimum_market_series else "insufficient_sample"}
    return {"profiles":profiles,"comparable_market_series":series_count,
      "minimum_market_series":minimum_market_series,"follow_on_window_minutes":follow_on_window_minutes,
      "limitations":["Only caller-supplied comparable_market_key values are compared.",
       "First mover means first observed price change in this dataset, not first mover at the bookmaker.",
       "Sparse polling and provider cadence differences can distort apparent lead/lag behaviour.",
       "These describe observable behaviour, not private algorithms."]}
