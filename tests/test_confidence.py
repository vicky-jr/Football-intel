from app.services.confidence import assess_evidence_confidence

def test_missing_verification_causes_abstention():
 r=assess_evidence_confidence(source_freshness="unknown",verified_market_mapping=False,
 verified_settlement_rules=False,sample_size=100,required_sample_size=50,calibrated_model=True)
 assert r["status"]=="abstain" and "market_mapping_not_verified" in r["blocking_reasons"]

def test_fully_supported_evidence_is_eligible_for_review():
 r=assess_evidence_confidence(source_freshness="fresh",verified_market_mapping=True,
 verified_settlement_rules=True,sample_size=100,required_sample_size=50,calibrated_model=True)
 assert r["status"]=="eligible_for_review"
