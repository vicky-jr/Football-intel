import pytest
from app.services.responsible_gambling import RiskLimits,evaluate_risk

def limits():return RiskLimits(1000,3000,2000,1500)

def test_risk_check_blocks_limits_and_self_exclusion():
 r=evaluate_risk(proposed_stake=500,limits=limits(),stakes_today=2800,self_excluded=True)
 assert r["decision"]=="blocked" and "self_exclusion_active" in r["violations"] and "daily_stake_limit_exceeded" in r["violations"]

def test_risk_check_allows_inside_limits():
 assert evaluate_risk(proposed_stake=100,limits=limits(),stakes_today=200)["decision"]=="within_configured_limits"

def test_loss_limit_blocks_new_stake():
 assert "daily_loss_limit_reached" in evaluate_risk(proposed_stake=1,limits=limits(),net_loss_today=1500)["violations"]
