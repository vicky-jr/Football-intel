# Football Intel

Football Intel is an experimental, bookmaker-agnostic, multi-sport market-analysis application.

## Product scope

The target is to discover and analyse the complete market inventory actually offered for each event by every successfully connected and verified bookmaker—not just Football.com, not just football, and not a hard-coded shortlist of familiar bets.

The system is being designed for a catalogue of 100,000+ distinct market/selection definitions across sports, bookmakers, competitions and event types. That does **not** mean every option exists on every event. The app must enumerate the exact live inventory returned by each provider and preserve all selections, lines, periods and settlement details.

Operators explicitly in scope include 1xBet and PariPesa/Paripesa, plus popular regional and international bookmakers. The provider registry will be extensible. Actual integrations depend on authorised data access and verification.

See [the global bookmaker and market coverage strategy](docs/bookmaker-coverage.md) for the discovery architecture, provider registry, coverage measurements and delivery phases.

## Current implementation status

- FastAPI application with interactive API documentation
- Health endpoint
- Match-analysis endpoint using user-supplied team averages
- Experimental Poisson score-grid estimates for 1X2, Over 2.5 goals and Both Teams to Score
- Basic API tests (not yet verified in a live environment)
- Global multi-sport, multi-bookmaker market-discovery requirements documented
- No bookmaker feeds or live market ingestion connected yet

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

The current prediction endpoint is an experimental baseline, not a validated betting model. It uses supplied averages and does not yet collect fixtures, team news, injuries, lineups, historical results, bookmaker prices or live market inventories. No bookmaker is currently marked as integrated. The application does not identify guaranteed bets.

The next engineering milestone is a provider-neutral multi-sport event/market/selection schema and discovery adapter system, followed by authorised provider integrations, coverage measurement, price comparison, market-specific models, historical backtesting and a mobile-friendly interface.

## Tests

```bash
pytest
```
