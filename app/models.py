"""Validated request and response models."""
from pydantic import BaseModel, Field


class TeamStats(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    avg_goals_scored: float = Field(ge=0, le=10)
    avg_goals_conceded: float = Field(ge=0, le=10)
    form_points_per_game: float = Field(ge=0, le=3, description="Points per game over the selected recent-form window")


class AnalysisRequest(BaseModel):
    home: TeamStats
    away: TeamStats
    home_advantage: float = Field(default=1.12, ge=0.5, le=2.0)


class MarketEstimate(BaseModel):
    market: str
    selection: str
    probability: float = Field(ge=0, le=1)
    note: str


class AnalysisResponse(BaseModel):
    home_team: str
    away_team: str
    expected_home_goals: float
    expected_away_goals: float
    most_likely_score: str
    markets: list[MarketEstimate]
    limitations: list[str]
