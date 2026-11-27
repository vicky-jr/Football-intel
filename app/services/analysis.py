"""Simple, explainable Poisson baseline for supplied team statistics."""
from math import exp, factorial
from app.models import AnalysisRequest, AnalysisResponse, MarketEstimate


def _poisson(mean: float, goals: int) -> float:
    return exp(-mean) * mean ** goals / factorial(goals)


def analyze_fixture(request: AnalysisRequest) -> AnalysisResponse:
    home, away = request.home, request.away

    # Blend each team's scoring rate with the opponent's concession rate.
    home_xg = ((home.avg_goals_scored + away.avg_goals_conceded) / 2) * request.home_advantage
    away_xg = (away.avg_goals_scored + home.avg_goals_conceded) / 2
    home_xg = max(0.05, min(home_xg, 5.0))
    away_xg = max(0.05, min(away_xg, 5.0))

    # An 0-8 goal grid is a practical approximation for this baseline.
    grid = [
        (h, a, _poisson(home_xg, h) * _poisson(away_xg, a))
        for h in range(9) for a in range(9)
    ]
    home_win = sum(p for h, a, p in grid if h > a)
    draw = sum(p for h, a, p in grid if h == a)
    away_win = sum(p for h, a, p in grid if h < a)
    over_25 = sum(p for h, a, p in grid if h + a >= 3)
    btts = sum(p for h, a, p in grid if h > 0 and a > 0)
    score = max(grid, key=lambda item: item[2])

    markets = [
        MarketEstimate(market="1X2", selection=f"{home.name} win", probability=home_win, note="Poisson baseline from supplied averages"),
        MarketEstimate(market="1X2", selection="Draw", probability=draw, note="Poisson baseline from supplied averages"),
        MarketEstimate(market="1X2", selection=f"{away.name} win", probability=away_win, note="Poisson baseline from supplied averages"),
        MarketEstimate(market="Goals", selection="Over 2.5", probability=over_25, note="Total-goals probability from the score grid"),
        MarketEstimate(market="Both teams to score", selection="Yes", probability=btts, note="Probability both teams score at least once"),
    ]

    return AnalysisResponse(
        home_team=home.name,
        away_team=away.name,
        expected_home_goals=round(home_xg, 2),
        expected_away_goals=round(away_xg, 2),
        most_likely_score=f"{score[0]}-{score[1]}",
        markets=markets,
        limitations=[
            "This is an experimental statistical baseline, not a calibrated betting model.",
            "It uses only the statistics supplied in the request; no live fixtures, injuries, lineups, odds, or external data are fetched.",
            "Probabilities are estimates and must not be treated as guaranteed outcomes or betting advice.",
        ],
    )
