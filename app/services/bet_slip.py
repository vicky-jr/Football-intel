"""Bet-slip reconstruction from text produced by an authorised OCR extractor."""
from __future__ import annotations
import re
from typing import Any
_LINE=re.compile(r"^(?P<selection>.+?)\s+(?:@|odds\s*[:=])\s*(?P<odds>[1-9]\d*(?:\.\d+)?)\s*$",re.IGNORECASE)

def reconstruct_bet_slip(extracted_text:str,*,image_sha256:str|None=None,stake:float|None=None)->dict[str,Any]:
    if not extracted_text.strip():raise ValueError("extracted_text is required")
    if image_sha256 is not None and not re.fullmatch(r"[a-fA-F0-9]{64}",image_sha256):raise ValueError("image_sha256 must be a 64-character SHA-256 hex digest")
    if stake is not None and stake<=0:raise ValueError("stake must be positive")
    parsed=[];unparsed=[]
    for number,raw in enumerate(extracted_text.splitlines(),1):
        line=raw.strip()
        if not line:continue
        match=_LINE.match(line)
        if not match:unparsed.append({"line_number":number,"text":line});continue
        odds=float(match.group("odds"))
        if odds<=1:unparsed.append({"line_number":number,"text":line,"reason":"invalid_decimal_odds"});continue
        parsed.append({"selection":match.group("selection").strip(),"odds_decimal":odds,
                       "source_line_number":number,"needs_event_and_market_verification":True})
    combined=1.0
    for item in parsed:combined*=item["odds_decimal"]
    return {"status":"reconstructed" if parsed else "no_selections_parsed",
      "extraction_method":"caller_supplied_ocr_text","image_sha256":image_sha256,
      "selections":parsed,"unparsed_lines":unparsed,"selection_count":len(parsed),
      "combined_decimal_odds":round(combined,6) if parsed else None,"stake":stake,
      "potential_return":round(stake*combined,2) if stake is not None and parsed else None,
      "verification_required":True,
      "limitations":["This parses supplied OCR text; it does not inspect or OCR image bytes.",
       "Selections must be matched to a real event, market, selection and settlement rule before use.",
       "No bet is placed and no bookmaker account is accessed."]}
