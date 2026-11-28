"""User-controlled exposure checks and safer-gambling guardrails."""
from __future__ import annotations
from dataclasses import dataclass,asdict
from typing import Any

@dataclass(frozen=True)
class RiskLimits:
    max_single_stake:float
    max_daily_stakes:float
    max_open_exposure:float
    max_daily_net_loss:float
    currency:str="NGN"
    def __post_init__(self):
        for name,value in asdict(self).items():
            if name!="currency" and value<=0:raise ValueError(f"{name} must be positive")

def evaluate_risk(*,proposed_stake:float,limits:RiskLimits,stakes_today:float=0.0,
                  open_exposure:float=0.0,net_loss_today:float=0.0,
                  self_excluded:bool=False,cooling_off_active:bool=False)->dict[str,Any]:
    if any(x<0 for x in (proposed_stake,stakes_today,open_exposure,net_loss_today)):
        raise ValueError("stake, exposure and loss values cannot be negative")
    violations=[];projected=stakes_today+proposed_stake;exposure=open_exposure+proposed_stake
    if self_excluded:violations.append("self_exclusion_active")
    if cooling_off_active:violations.append("cooling_off_period_active")
    if proposed_stake>limits.max_single_stake:violations.append("single_stake_limit_exceeded")
    if projected>limits.max_daily_stakes:violations.append("daily_stake_limit_exceeded")
    if exposure>limits.max_open_exposure:violations.append("open_exposure_limit_exceeded")
    if net_loss_today>=limits.max_daily_net_loss:violations.append("daily_loss_limit_reached")
    return {"permitted_by_configured_limits":not violations,"decision":"blocked" if violations else "within_configured_limits",
      "violations":violations,"currency":limits.currency,"projected_daily_stakes":round(projected,2),
      "projected_open_exposure":round(exposure,2),"daily_net_loss":round(net_loss_today,2),
      "limits":asdict(limits),
      "note":"This is a limit check, not a recommendation to gamble or a guarantee of affordability."}
