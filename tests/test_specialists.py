from app.services.specialists import aggregate_specialist_assessments

def test_validated_specialists_support_conclusion():
 r=aggregate_specialist_assessments([
 {"specialist_id":"form","conclusion":"home_edge","evidence_ids":["e1"],"validation_status":"validated"},
 {"specialist_id":"lineups","conclusion":"home_edge","evidence_ids":["e2"],"validation_status":"validated"}])
 assert r["status"]=="supported" and r["agreement"]==1.0

def test_insufficient_and_conflicting_evidence_are_visible():
 r=aggregate_specialist_assessments([{"specialist_id":"form","conclusion":"home_edge","evidence_ids":[],"validation_status":"validated"}])
 assert r["status"]=="abstain"
 r=aggregate_specialist_assessments([
 {"specialist_id":"form","conclusion":"home_edge","evidence_ids":["e1"],"validation_status":"validated"},
 {"specialist_id":"lineups","conclusion":"away_edge","evidence_ids":["e2"],"validation_status":"validated"},
 {"specialist_id":"odds","conclusion":"away_edge","evidence_ids":["e3"],"validation_status":"validated"}])
 assert r["status"]=="conflicting_evidence" and r["leading_conclusion"]=="away_edge"
