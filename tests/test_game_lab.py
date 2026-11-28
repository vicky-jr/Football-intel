import hashlib
from app.services.game_lab import analyse_game_rounds,verify_seed_commitment

def test_game_analysis_is_descriptive_and_never_predicts_next_round():
 r=analyse_game_rounds({"game_id":"demo-wheel","rules_version":"v1","published_rtp":.96},
 [{"stake":10,"payout":20,"outcome":"red"},{"stake":10,"payout":0,"outcome":"black"}])
 assert r["sample_size"]==2 and r["observed_rtp"]==1.0 and r["next_round_prediction"] is None

def test_sha256_seed_commitment_check():
 seed="revealed-seed";commit=hashlib.sha256(seed.encode()).hexdigest()
 assert verify_seed_commitment(seed,commit)["commitment_valid"]
 assert not verify_seed_commitment(seed,"0"*64)["commitment_valid"]
