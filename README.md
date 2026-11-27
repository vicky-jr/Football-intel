# Football Intel

Football Intel is an experimental football match-analysis application. The first milestone provides a small FastAPI backend and an explainable statistical baseline.

## Current status

- FastAPI application with interactive API documentation
- Health endpoint
- Match-analysis endpoint using user-supplied team averages
- Poisson score-grid estimates for 1X2, Over 2.5 goals, and Both Teams to Score
- Basic API tests

## Run locally

Python 3.10 or newer is recommended.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python Main.py
```

Open http://localhost:8000/docs for the interactive API.

## Analyze a match

Send a POST request to `/api/v1/analyze`:

```json
{
  "home": {
    "name": "Home FC",
    "avg_goals_scored": 1.6,
    "avg_goals_conceded": 0.9,
    "form_points_per_game": 2.0
  },
  "away": {
    "name": "Away FC",
    "avg_goals_scored": 1.1,
    "avg_goals_conceded": 1.3,
    "form_points_per_game": 1.2
  }
}
```

## Important limitations

This initial model is a development baseline, not a validated prediction system. It uses only supplied averages. It does not yet collect fixtures, team news, injuries, lineups, historical results, bookmaker prices, or Football.com markets. It does not identify guaranteed bets. The next milestones are data-source integration, historical backtesting and calibration, a complete market catalogue, and a mobile-friendly user interface.

## Tests

```bash
pytest
```
