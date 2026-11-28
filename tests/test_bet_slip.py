import pytest
from app.services.bet_slip import reconstruct_bet_slip

def test_reconstructs_explicit_selection_lines_and_retains_unparsed_text():
 r=reconstruct_bet_slip("Arsenal win @ 1.80\nOver 2.5 odds: 1.95\nSome unclear text",stake=100)
 assert r["selection_count"]==2 and r["combined_decimal_odds"]==3.51
 assert r["potential_return"]==351.0 and len(r["unparsed_lines"])==1 and r["verification_required"]

def test_empty_text_and_bad_hash_rejected():
 with pytest.raises(ValueError):reconstruct_bet_slip(" ")
 with pytest.raises(ValueError):reconstruct_bet_slip("A @ 2.0",image_sha256="bad")
