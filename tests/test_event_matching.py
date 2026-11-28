from app.services.event_matching import match_events

def event(p,i,h,a,start="2026-12-01T18:00:00+00:00"):
 return {"provider":p,"source_event_id":i,"sport":"football","competition":"Premier League","home":h,"away":a,"start_time":start}

def test_cross_provider_high_confidence_event_match():
 r=match_events(event("a","1","Arsenal FC","Chelsea FC"),event("b","9","Arsenal","Chelsea"))
 assert r["status"]=="matched" and r["automatic_link_permitted"]

def test_reversed_participant_order_is_flagged():
 assert match_events(event("a","1","Arsenal","Chelsea"),event("b","9","Chelsea","Arsenal"))["reversed_home_away"]

def test_wrong_kickoff_and_sport_are_rejected():
 assert match_events(event("a","1","Arsenal","Chelsea"),event("b","9","Arsenal","Chelsea","2026-12-03T18:00:00+00:00"))["reason"]=="kickoff_time_mismatch"
 other=event("b","9","Arsenal","Chelsea");other["sport"]="basketball"
 assert match_events(event("a","1","Arsenal","Chelsea"),other)["reason"]=="sport_mismatch"
