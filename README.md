# Football Intel

Football Intel is an experimental, bookmaker-agnostic, multi-sport market-analysis and intelligence application.

## Product mission

Football Intel aims to study both real-sport betting markets and bookmaker-hosted proprietary games—including virtual sports, instant virtuals, crash games, wheels, dice and other game families—across providers and formats that can lawfully and reliably be researched. It will turn timestamped observations into explainable research, comparisons and carefully evaluated model outputs.

The system does not claim access to bookmakers' private source code or internal trading algorithms. It studies observable odds, market states, price movements and historical outcomes, then tests behavioural hypotheses against evidence.

## Product scope

The target is to discover and analyse the complete market inventory actually offered for each event by every successfully connected and verified bookmaker—not just Football.com, not just football, and not a hard-coded shortlist of familiar bets.

The system is being designed for a catalogue of 100,000+ distinct market/selection definitions across sports, bookmakers, competitions and event types. That does not mean every option exists on every event. The app must enumerate the exact live inventory returned by each provider and preserve all selections, lines, periods and settlement details.

Operators explicitly in scope include 1xBet and PariPesa/Paripesa, plus popular regional and international bookmakers. The provider registry will be extensible. Actual integrations depend on authorised data access and verification.

## Intelligence capabilities (target architecture)

- Global multi-sport and multi-bookmaker market discovery.\n- Proprietary bookmaker-game catalogue and game-specific statistical research.\n- Virtual sports, instant games, crash/wheel mechanics and published fairness-rule analysis.
- Timestamped odds and market-state history.
- Cross-book price comparison and movement timelines.
- Observable bookmaker behaviour profiles.
- Sports/event/market pattern research.
- Evidence-grounded conversational intelligence with explicit uncertainty.
- Market-specific models with backtesting and calibration.
- Coverage, freshness, model-performance and data-quality reporting.

See [the global bookmaker and market coverage strategy](docs/bookmaker-coverage.md), [the intelligence architecture](docs/intelligence-architecture.md), and [the development roadmap](docs/development-roadmap.md).

## Current implementation status

- FastAPI application with interactive API documentation.
- Health endpoint and experimental match-analysis endpoint.
- Provider-neutral event/market/selection contracts.
- Provider registry and loss-aware in-memory market inventory.
- Global multi-sport/provider discovery requirements documented.
- Intelligence architecture and phased development roadmap documented.
- No bookmaker feeds or live market ingestion connected yet.
- No persistent historical odds/game-results database, validated bookmaker behaviour profiles, proprietary-game research engine or evidence-grounded assistant yet.

## Important limitations

The current prediction endpoint is an experimental baseline, not a validated betting model. It uses supplied averages and does not yet collect fixtures, team news, injuries, lineups, historical results, bookmaker prices or live market inventories. No bookmaker is currently marked as integrated. The application does not identify guaranteed bets.

Bookmaker and proprietary-game insights will be based on observable, timestamped data and published rules—not claims to have reverse-engineered private algorithms or RNGs. Historical random outcomes cannot reliably predict the next independent random outcome. Coverage and conclusions will be limited to providers, markets, periods and data quality we can verify.

## Tests

Run pytest after installing requirements in a Python 3.10+ environment.
